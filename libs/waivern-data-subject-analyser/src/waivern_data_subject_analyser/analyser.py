"""Data subject analysis analyser for GDPR Article 30(1)(c) compliance."""

import importlib
import logging
from collections.abc import Sequence
from types import ModuleType
from typing import Any, override

from waivern_analysers_shared import SchemaInputHandler
from waivern_analysers_shared.llm_validation import ValidationOrchestrator
from waivern_analysers_shared.llm_validation.validation_orchestrator import (
    FallbackNeeded,
)
from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import Analyser, InputRequirement
from waivern_core.dispatch import DispatchRequest, DispatchResult, PrepareResult
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm.types import LLMDispatchResult, LLMRequest
from waivern_rulesets.data_subject_indicator import DataSubjectIndicatorRule
from waivern_schemas.data_subject_indicator import DataSubjectIndicatorModel

from .result_builder import DataSubjectResultBuilder
from .types import DataSubjectAnalyserConfig, DataSubjectPrepareState
from .validation import create_validation_orchestrator

logger = logging.getLogger(__name__)


class DataSubjectAnalyser(Analyser):
    """Analyser for identifying data subjects for GDPR Article 30(1)(c) compliance.

    This analyser identifies and categorises data subjects from various data sources
    to help organisations maintain systematic records of data processing activities.

    Implements the ``DistributedProcessor`` protocol: ``prepare()`` builds
    the request for the executor to dispatch, and ``finalise()`` consumes
    the dispatch results.
    """

    def __init__(self, config: DataSubjectAnalyserConfig) -> None:
        """Initialise the data subject analyser.

        Args:
            config: Analyser configuration.

        """
        self._config = config
        self._rules = RulesetManager.get_rules(
            config.pattern_matching.ruleset, DataSubjectIndicatorRule
        )
        self._result_builder = DataSubjectResultBuilder(config)
        self._orchestrator: ValidationOrchestrator[DataSubjectIndicatorModel] = (
            create_validation_orchestrator(config.llm_validation)
        )

    @classmethod
    @override
    def get_name(cls) -> str:
        """Get the name of the analyser."""
        return "data_subject_analyser"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations.

        DataSubjectAnalyser accepts either standard_input OR source_code schema.
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
        return [Schema("data_subject_indicator", "1.0.0")]

    # ── DistributedProcessor ─────────────────────────────────────────────

    def prepare(
        self, inputs: list[Message], output_schema: Schema
    ) -> PrepareResult[DataSubjectPrepareState]:
        """Analyse inputs and declare LLM dispatch needs.

        1. Validate inputs and extract run_id
        2. Load schema reader + handler once per input schema and aggregate
           indicators across messages (fan-in)
        3. If LLM enabled and findings exist, run orchestrator.prepare() to
           build the LLMRequest. Otherwise, return empty requests.

        """
        if not inputs:
            raise ValueError("No input messages provided")
        run_id = inputs[0].run_id
        if not run_id:
            raise ValueError("run_id is required but not set on input messages")

        findings = self._merge_input_findings(inputs)
        llm_enabled = self._config.llm_validation.enable_llm_validation

        if not llm_enabled or not findings:
            return PrepareResult(
                state=DataSubjectPrepareState(
                    all_findings=findings,
                    run_id=run_id,
                    llm_enabled=llm_enabled,
                ),
                requests=[],
            )

        orchestrator_state, llm_request = self._orchestrator.prepare(
            findings, self._config.llm_validation, run_id
        )

        requests: list[DispatchRequest] = []
        if llm_request is not None:
            requests.append(llm_request)

        return PrepareResult(
            state=DataSubjectPrepareState(
                all_findings=findings,
                run_id=run_id,
                llm_enabled=llm_enabled,
                orchestrator_state=orchestrator_state,
            ),
            requests=requests,
        )

    def finalise(
        self,
        state: DataSubjectPrepareState,
        results: Sequence[DispatchResult],
        output_schema: Schema,
    ) -> tuple[Message, list[Message]] | PrepareResult[DataSubjectPrepareState]:
        """Produce output message from state and dispatch results.

        Paths:
        - LLM disabled or no orchestrator state → build output from raw
          findings, no validation metadata.
        - LLM enabled → invoke ``orchestrator.finalise()`` with the LLM
          dispatch result and marker callback, then build output from the
          resulting ``ValidationResult``.

        DataSubjectAnalyser does not configure a fallback strategy, so the
        orchestrator never returns ``FallbackNeeded`` here. The branch is
        retained defensively to satisfy the typed return union.
        """
        if not state.llm_enabled or state.orchestrator_state is None:
            primary = self._result_builder.build_output_message(
                state.all_findings,
                output_schema,
                validation_result=None,
            )
            return primary, self._result_builder.build_sidecars(None, state.run_id)

        llm_result = self._extract_llm_result(results)
        outcome = self._orchestrator.finalise(
            state.orchestrator_state,
            llm_result,
            marker=self._mark_finding_validated,
        )

        if isinstance(outcome, FallbackNeeded):
            # DataSubjectAnalyser has no fallback strategy; reaching here
            # would indicate a configuration error in the orchestrator.
            raise RuntimeError(
                "DataSubjectAnalyser does not support fallback dispatch rounds"
            )

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
        return primary, self._result_builder.build_sidecars(outcome, state.run_id)

    def deserialise_prepare_result(
        self, raw: dict[str, Any]
    ) -> PrepareResult[DataSubjectPrepareState]:
        """Reconstruct a typed PrepareResult from a raw dict.

        Called on the resume path where a persisted PrepareResult must be
        restored. Handles LLMRequest reconstruction with correct field types.
        ``prompt_builder`` and ``response_model`` remain ``None`` on resume —
        they are not needed since ``built_cache_keys`` drives cache lookup.

        """
        state = DataSubjectPrepareState.model_validate(raw["state"])
        requests: list[DispatchRequest] = [
            LLMRequest[DataSubjectIndicatorModel].model_validate(r)
            for r in raw.get("requests", [])
        ]
        return PrepareResult(state=state, requests=requests)

    # ── Private helpers ──────────────────────────────────────────────────

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

        The reader module provides both read() and create_handler() functions,
        co-locating schema reading and handler creation.

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
                f"waivern_data_subject_analyser.schema_readers.{module_name}"
            )
        except (ModuleNotFoundError, AttributeError) as e:
            raise ValueError(f"Unsupported input schema: {schema.name}") from e

    def _merge_input_findings(
        self, inputs: list[Message]
    ) -> list[DataSubjectIndicatorModel]:
        """Aggregate indicators across input messages (fan-in).

        Loads the reader and handler once per input schema and reuses them
        for all messages with the same schema. Supports mixed-schema fan-in
        (standard_input and source_code messages in the same call).

        Args:
            inputs: List of input messages (same or mixed schemas).

        Returns:
            Flattened list of all indicators from all inputs.

        """
        # Cache (reader_module, handler) per schema to avoid redundant
        # imports and object creation when multiple messages share a schema.
        cache_by_schema: dict[
            tuple[str, str],
            tuple[ModuleType, SchemaInputHandler[DataSubjectIndicatorModel]],
        ] = {}
        findings: list[DataSubjectIndicatorModel] = []
        for message in inputs:
            schema_key = (message.schema.name, message.schema.version)
            if schema_key not in cache_by_schema:
                reader = self._load_reader(message.schema)
                handler = reader.create_handler(self._config, self._rules)
                cache_by_schema[schema_key] = (reader, handler)
            reader, handler = cache_by_schema[schema_key]
            input_data = reader.read(message.content)
            findings.extend(handler.analyse(input_data))
        return findings

    def _mark_finding_validated(
        self, finding: DataSubjectIndicatorModel
    ) -> DataSubjectIndicatorModel:
        """Mark a finding as LLM validated.

        Args:
            finding: Finding to mark.

        Returns:
            New finding with validation marker in metadata context.

        """
        if finding.metadata:
            updated_context = dict(finding.metadata.context)
            updated_context["data_subject_llm_validated"] = True

            updated_metadata = finding.metadata.model_copy(
                update={"context": updated_context}
            )
            return finding.model_copy(update={"metadata": updated_metadata})

        return finding
