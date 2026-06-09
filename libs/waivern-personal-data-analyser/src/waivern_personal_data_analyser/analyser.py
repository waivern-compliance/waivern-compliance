"""Personal data analysis analyser."""

import importlib
import logging
from collections.abc import Sequence
from typing import Any, override

from waivern_analysers_shared import SchemaReader
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
from waivern_rulesets.personal_data_indicator import PersonalDataIndicatorRule
from waivern_schemas.connector_types import BaseMetadata
from waivern_schemas.personal_data_indicator import PersonalDataIndicatorModel
from waivern_schemas.standard_input import (
    StandardInputDataItemModel,
    StandardInputDataModel,
)

from .pattern_matcher import PersonalDataPatternMatcher
from .result_builder import PersonalDataResultBuilder
from .types import PersonalDataAnalyserConfig, PersonalDataPrepareState
from .validation import create_validation_orchestrator

logger = logging.getLogger(__name__)


class PersonalDataAnalyser(Analyser):
    """Analyser for analysing personal data patterns in content.

    This analyser uses predefined rulesets to identify personal data patterns
    in structured data content. It supports LLM-based validation to filter
    false positives via the DistributedProcessor protocol: ``prepare()``
    builds the request for the executor to dispatch, and ``finalise()``
    consumes the dispatch results.
    """

    def __init__(self, config: PersonalDataAnalyserConfig) -> None:
        """Initialise the analyser.

        Args:
            config: Validated configuration object.

        """
        self._config = config
        rules = RulesetManager.get_rules(
            config.pattern_matching.ruleset, PersonalDataIndicatorRule
        )
        self._pattern_matcher = PersonalDataPatternMatcher(
            rules, config.pattern_matching
        )
        self._result_builder = PersonalDataResultBuilder(config)
        self._orchestrator: ValidationOrchestrator[PersonalDataIndicatorModel] = (
            create_validation_orchestrator(config.llm_validation)
        )

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "personal_data_analyser"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations.

        PersonalDataAnalyser accepts either standard_input OR source_code schema.
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
        """Declare output schemas this analyser can produce."""
        return [Schema("personal_data_indicator", "1.0.0")]

    # ── DistributedProcessor ─────────────────────────────────────────────

    def prepare(
        self, inputs: list[Message], output_schema: Schema
    ) -> PrepareResult[PersonalDataPrepareState]:
        """Analyse inputs and declare LLM dispatch needs.

        1. Validate inputs and extract run_id
        2. Merge input data items (fan-in) and run pattern matching
        3. If LLM enabled and findings exist, run orchestrator.prepare() to
           build the LLMRequest. Otherwise, return empty requests.

        """
        if not inputs:
            raise ValueError("No input messages provided")
        run_id = inputs[0].run_id
        if not run_id:
            raise ValueError("run_id is required but not set on input messages")

        data_items = self._merge_input_data_items(inputs)
        findings = self._find_patterns_in_data_items(data_items)
        llm_enabled = self._config.llm_validation.enable_llm_validation

        if not llm_enabled or not findings:
            return PrepareResult(
                state=PersonalDataPrepareState(
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
            state=PersonalDataPrepareState(
                all_findings=findings,
                run_id=run_id,
                llm_enabled=llm_enabled,
                orchestrator_state=orchestrator_state,
            ),
            requests=requests,
        )

    def finalise(
        self,
        state: PersonalDataPrepareState,
        results: Sequence[DispatchResult],
        output_schema: Schema,
    ) -> tuple[Message, list[Message]] | PrepareResult[PersonalDataPrepareState]:
        """Produce output message from state and dispatch results.

        Paths:
        - LLM disabled or no orchestrator state → build output from raw
          findings, no validation metadata.
        - LLM enabled → invoke ``orchestrator.finalise()`` with the LLM
          dispatch result and marker callback, then build output from the
          resulting ``ValidationResult``.

        PersonalDataAnalyser does not configure a fallback strategy, so the
        orchestrator never returns ``FallbackNeeded`` here. The branch is
        retained defensively to satisfy the typed return union.
        """
        if not state.llm_enabled or state.orchestrator_state is None:
            primary = self._result_builder.build_output_message(
                state.all_findings,
                output_schema,
                validation_result=None,
            )
            return primary, []

        llm_result = self._extract_llm_result(results)
        outcome = self._orchestrator.finalise(
            state.orchestrator_state,
            llm_result,
            marker=self._mark_finding_validated,
        )

        if isinstance(outcome, FallbackNeeded):
            # PersonalDataAnalyser has no fallback strategy; reaching here
            # would indicate a configuration error in the orchestrator.
            raise RuntimeError(
                "PersonalDataAnalyser does not support fallback dispatch rounds"
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
        return primary, []

    def deserialise_prepare_result(
        self, raw: dict[str, Any]
    ) -> PrepareResult[PersonalDataPrepareState]:
        """Reconstruct a typed PrepareResult from a raw dict.

        Called on the resume path where a persisted PrepareResult must be
        restored. Handles LLMRequest reconstruction with correct field types.
        ``prompt_builder`` and ``response_model`` remain ``None`` on resume —
        they are not needed since ``built_cache_keys`` drives cache lookup.

        """
        state = PersonalDataPrepareState.model_validate(raw["state"])
        requests: list[DispatchRequest] = [
            LLMRequest[PersonalDataIndicatorModel].model_validate(r)
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

    def _load_reader(
        self, schema: Schema
    ) -> SchemaReader[StandardInputDataModel[BaseMetadata]]:
        """Dynamically import reader module.

        Python's import system automatically caches modules in sys.modules,
        so repeated imports are fast and don't require manual caching.

        Args:
            schema: Input schema to load reader for.

        Returns:
            Reader module with typed read() function.

        Raises:
            ModuleNotFoundError: If reader module doesn't exist for this version.

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(  # type: ignore[return-value]
            f"waivern_personal_data_analyser.schema_readers.{module_name}"
        )

    def _merge_input_data_items(
        self, inputs: list[Message]
    ) -> list[StandardInputDataItemModel[BaseMetadata]]:
        """Merge data items from multiple input messages (fan-in).

        Args:
            inputs: List of input messages with same schema.

        Returns:
            Flattened list of all data items from all inputs.

        """
        # Python's importlib caches modules, so repeated calls are cheap
        all_data_items: list[StandardInputDataItemModel[BaseMetadata]] = []
        for message in inputs:
            reader = self._load_reader(message.schema)
            input_data = reader.read(message.content)
            all_data_items.extend(input_data.data)
        return all_data_items

    def _find_patterns_in_data_items(
        self, data_items: list[StandardInputDataItemModel[BaseMetadata]]
    ) -> list[PersonalDataIndicatorModel]:
        """Run pattern matching on all data items.

        Args:
            data_items: List of data items to scan for patterns.

        Returns:
            List of findings from all data items.

        """
        findings: list[PersonalDataIndicatorModel] = []
        for item in data_items:
            item_findings = self._pattern_matcher.find_patterns(
                item.content, item.metadata
            )
            findings.extend(item_findings)
        return findings

    def _mark_finding_validated(
        self, finding: PersonalDataIndicatorModel
    ) -> PersonalDataIndicatorModel:
        """Mark a finding as LLM validated.

        Args:
            finding: Finding to mark.

        Returns:
            New finding with validation marker in metadata context.

        """
        if finding.metadata:
            updated_context = dict(finding.metadata.context)
            updated_context["personal_data_llm_validated"] = True

            updated_metadata = finding.metadata.model_copy(
                update={"context": updated_context}
            )
            return finding.model_copy(update={"metadata": updated_metadata})

        return finding
