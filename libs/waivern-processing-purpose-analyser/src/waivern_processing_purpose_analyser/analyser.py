"""Processing purpose analysis analyser for compliance frameworks."""

import importlib
import logging
from collections.abc import Sequence
from types import ModuleType
from typing import Any, override

from waivern_analysers_shared.llm_validation import ValidationOrchestrator
from waivern_analysers_shared.llm_validation.validation_orchestrator import (
    FallbackNeeded,
)
from waivern_core import Analyser, InputRequirement
from waivern_core.dispatch import DispatchRequest, DispatchResult, PrepareResult
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm.types import LLMDispatchResult, LLMRequest
from waivern_schemas.processing_purpose_indicator import ProcessingPurposeIndicatorModel
from waivern_schemas.source_code import SourceCodeDataModel

from .result_builder import ProcessingPurposeResultBuilder
from .types import ProcessingPurposeAnalyserConfig, ProcessingPurposePrepareState
from .validation import create_validation_orchestrator

logger = logging.getLogger(__name__)


class ProcessingPurposeAnalyser(Analyser):
    """Analyser for identifying data processing purposes.

    This analyser identifies and categorises data processing purposes from textual
    content to help organisations understand what they're using personal data for.

    Implements the ``DistributedProcessor`` protocol: ``prepare()`` builds
    the request for the executor to dispatch, and ``finalise()`` consumes
    the dispatch results.

    Multi-round behaviour: when the input schema is ``source_code`` and primary
    (extended-context) validation leaves fallback-eligible skipped findings
    (``OVERSIZED`` / ``MISSING_CONTENT`` / ``MISSING_SOURCE``), ``finalise()``
    returns a new ``PrepareResult`` carrying a fallback ``LLMRequest``. The
    executor runs another Phase 2 → 3 cycle; a second ``finalise()`` call then
    merges primary and fallback outcomes into the final output ``Message``.
    """

    def __init__(self, config: ProcessingPurposeAnalyserConfig) -> None:
        """Initialise the processing purpose analyser.

        Args:
            config: Configuration object with analysis settings.

        """
        self._config = config
        self._result_builder = ProcessingPurposeResultBuilder(config)

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "processing_purpose_analyser"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations.

        ProcessingPurposeAnalyser accepts either standard_input OR source_code schema.
        Each is a valid alternative input. Multiple messages of the same schema are
        supported (fan-in).
        """
        return [
            [InputRequirement("standard_input", "1.0.0")],
            [InputRequirement("source_code", "1.0.0")],
        ]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this analyser."""
        return [Schema("processing_purpose_indicator", "1.0.0")]

    # ── DistributedProcessor ─────────────────────────────────────────────

    def prepare(
        self, inputs: list[Message], output_schema: Schema
    ) -> PrepareResult[ProcessingPurposePrepareState]:
        """Analyse inputs and declare LLM dispatch needs.

        1. Validate inputs and extract run_id.
        2. Merge input messages (fan-in) and run pattern matching.
        3. If source_code schema, collect source contents from all messages.
        4. If LLM enabled and findings exist, construct the orchestrator and
           delegate to ``orchestrator.prepare()`` to build the LLMRequest.

        """
        if not inputs:
            raise ValueError("No input messages provided")
        run_id = inputs[0].run_id
        if not run_id:
            raise ValueError("run_id is required but not set on input messages")

        input_schema = inputs[0].schema
        findings = self._merge_input_findings(inputs)
        source_contents = self._extract_source_contents(inputs)
        llm_enabled = self._config.llm_validation.enable_llm_validation

        if not llm_enabled or not findings:
            return PrepareResult(
                state=ProcessingPurposePrepareState(
                    all_findings=findings,
                    run_id=run_id,
                    llm_enabled=llm_enabled,
                    input_schema_name=input_schema.name,
                ),
                requests=[],
            )

        orchestrator = create_validation_orchestrator(
            config=self._config.llm_validation,
            input_schema_name=input_schema.name,
            source_contents=source_contents,
        )
        orchestrator_state, llm_request = orchestrator.prepare(
            findings, self._config.llm_validation, run_id
        )

        requests: list[DispatchRequest] = []
        if llm_request is not None:
            requests.append(llm_request)

        return PrepareResult(
            state=ProcessingPurposePrepareState(
                all_findings=findings,
                run_id=run_id,
                llm_enabled=llm_enabled,
                input_schema_name=input_schema.name,
                orchestrator_state=orchestrator_state,
            ),
            requests=requests,
        )

    def finalise(
        self,
        state: ProcessingPurposePrepareState,
        results: Sequence[DispatchResult],
        output_schema: Schema,
    ) -> tuple[Message, list[Message]] | PrepareResult[ProcessingPurposePrepareState]:
        """Produce output from state and dispatch results.

        Paths:
        - LLM disabled / no orchestrator state → build output from raw findings.
        - LLM enabled, single round → orchestrator returns ValidationResult;
          build output Message.
        - LLM enabled, fallback round needed → orchestrator returns
          ``FallbackNeeded``; wrap it into a new ``PrepareResult`` so the
          executor runs another Phase 2 → 3 cycle. The fallback round's
          ``finalise()`` merges primary + fallback outcomes into a Message.
        """
        if not state.llm_enabled or state.orchestrator_state is None:
            primary = self._result_builder.build_output_message(
                state.all_findings,
                output_schema,
                validation_result=None,
            )
            return primary, []

        orchestrator = self._rebuild_orchestrator(state)
        llm_result = self._extract_llm_result(results)
        outcome = orchestrator.finalise(
            state.orchestrator_state,
            llm_result,
            marker=self._mark_finding_validated,
        )

        if isinstance(outcome, FallbackNeeded):
            # Multi-round: executor will dispatch the fallback request and
            # call finalise() again with is_fallback_round=True state.
            next_state = state.model_copy(update={"orchestrator_state": outcome.state})
            return PrepareResult(state=next_state, requests=[outcome.request])

        logger.info(
            f"Validation complete: {len(state.all_findings)} → "
            f"{len(outcome.kept_findings)} findings "
            f"({len(outcome.removed_groups)} groups removed)"
        )

        primary = self._result_builder.build_output_message(
            outcome.kept_findings,
            output_schema,
            validation_result=outcome,
        )
        return primary, []

    def deserialise_prepare_result(
        self, raw: dict[str, Any]
    ) -> PrepareResult[ProcessingPurposePrepareState]:
        """Reconstruct a typed PrepareResult from a raw dict.

        Called on the resume path where a persisted PrepareResult must be
        restored. Handles LLMRequest reconstruction with correct field types.
        ``prompt_builder`` and ``response_model`` remain ``None`` on resume —
        they are not needed since ``built_cache_keys`` drives cache lookup.

        """
        state = ProcessingPurposePrepareState.model_validate(raw["state"])
        requests: list[DispatchRequest] = [
            LLMRequest[ProcessingPurposeIndicatorModel].model_validate(r)
            for r in raw.get("requests", [])
        ]
        return PrepareResult(state=state, requests=requests)

    # ── Private helpers ──────────────────────────────────────────────────

    def _rebuild_orchestrator(
        self, state: ProcessingPurposePrepareState
    ) -> ValidationOrchestrator[ProcessingPurposeIndicatorModel]:
        """Rebuild the orchestrator for finalise() using persisted state.

        Passes the primary strategy's persistence state through to the factory.
        The factory extracts source contents from it when reconstructing a
        source_code strategy configuration.

        Precondition: ``state.orchestrator_state`` is not None (caller checks).
        """
        strategy_state = (
            state.orchestrator_state.strategy_state
            if state.orchestrator_state is not None
            else None
        )
        return create_validation_orchestrator(
            config=self._config.llm_validation,
            input_schema_name=state.input_schema_name,
            strategy_state=strategy_state,
        )

    def _extract_llm_result(
        self,
        results: Sequence[DispatchResult],
    ) -> LLMDispatchResult | None:
        """Extract the first LLMDispatchResult from dispatch results."""
        for result in results:
            match result:
                case LLMDispatchResult() as llm_result:
                    return llm_result
                case _:
                    continue
        return None

    def _load_reader(self, schema: Schema) -> ModuleType:
        """Dynamically import reader module.

        The reader module provides both ``read()`` and ``create_handler()``
        functions, co-locating schema reading and handler creation.

        Args:
            schema: Input schema to load reader for.

        Returns:
            Reader module with read() and create_handler() functions.

        Raises:
            ValueError: If reader module doesn't exist for this schema version.

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        try:
            return importlib.import_module(
                f"waivern_processing_purpose_analyser.schema_readers.{module_name}"
            )
        except (ModuleNotFoundError, AttributeError) as e:
            raise ValueError(f"Unsupported input schema: {schema.name}") from e

    def _merge_input_findings(
        self, inputs: list[Message]
    ) -> list[ProcessingPurposeIndicatorModel]:
        """Aggregate indicators across input messages (fan-in).

        Loads the reader/handler once per input schema and applies it to each
        message with that schema. Supports mixed-schema fan-in.

        Args:
            inputs: List of input messages (same or mixed schemas).

        Returns:
            Flattened list of all indicators from all inputs.

        """
        readers_by_schema: dict[tuple[str, str], ModuleType] = {}
        findings: list[ProcessingPurposeIndicatorModel] = []
        for message in inputs:
            schema_key = (message.schema.name, message.schema.version)
            reader = readers_by_schema.get(schema_key)
            if reader is None:
                reader = self._load_reader(message.schema)
                readers_by_schema[schema_key] = reader
            handler = reader.create_handler(self._config)
            input_data = reader.read(message.content)
            findings.extend(handler.analyse(input_data))
        return findings

    def _extract_source_contents(self, inputs: list[Message]) -> dict[str, str] | None:
        """Collect source file contents from source_code inputs (if applicable).

        Returns ``None`` when the first input is not source_code; this signals
        the factory to use the standard evidence-only strategy path.
        """
        if inputs[0].schema.name != "source_code":
            return None

        source_contents: dict[str, str] = {}
        for message in inputs:
            source_data = SourceCodeDataModel.model_validate(message.content)
            for file_data in source_data.data:
                source_contents[file_data.file_path] = file_data.raw_content
        return source_contents

    def _mark_finding_validated(
        self, finding: ProcessingPurposeIndicatorModel
    ) -> ProcessingPurposeIndicatorModel:
        """Mark a finding as LLM validated.

        Args:
            finding: Finding to mark.

        Returns:
            New finding with validation marker in metadata context.

        """
        if finding.metadata:
            updated_context = dict(finding.metadata.context)
            updated_context["processing_purpose_llm_validated"] = True

            updated_metadata = finding.metadata.model_copy(
                update={"context": updated_context}
            )
            return finding.model_copy(update={"metadata": updated_metadata})

        return finding
