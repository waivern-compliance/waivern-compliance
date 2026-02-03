"""Personal data analysis analyser."""

import importlib
import logging
from typing import override

from waivern_analysers_shared import SchemaReader
from waivern_analysers_shared.llm_validation import ValidationResult
from waivern_core import Analyser, InputRequirement
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseMetadata,
    Schema,
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_llm.v2 import LLMService

from .pattern_matcher import PersonalDataPatternMatcher
from .result_builder import PersonalDataResultBuilder
from .schemas.types import PersonalDataIndicatorModel
from .types import PersonalDataAnalyserConfig
from .validation import create_validation_orchestrator

logger = logging.getLogger(__name__)


class PersonalDataAnalyser(Analyser):
    """Analyser for analysing personal data patterns in content.

    This analyser uses predefined rulesets to identify personal data patterns
    in structured data content. It supports LLM-based validation to filter
    false positives.
    """

    def __init__(
        self,
        config: PersonalDataAnalyserConfig,
        llm_service: LLMService | None = None,
    ) -> None:
        """Initialise the analyser with dependency injection.

        Args:
            config: Validated configuration object
            llm_service: LLM service for validation (injected by factory)

        """
        self._config = config
        self._pattern_matcher = PersonalDataPatternMatcher(config.pattern_matching)
        self._llm_service = llm_service
        self._result_builder = PersonalDataResultBuilder(config)

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "personal_data_analyser"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations.

        PersonalDataAnalyser accepts standard_input schema.
        Multiple messages of the same schema are supported (fan-in).
        """
        return [
            [InputRequirement("standard_input", "1.0.0")],
        ]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this analyser can produce."""
        return [Schema("personal_data_indicator", "1.0.0")]

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

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process data to find personal data patterns using dynamic reader/producer.

        Supports same-schema fan-in: multiple standard_input messages are merged
        before processing. Each data item retains its original metadata for tracing.

        Args:
            inputs: List of input messages (same schema, fan-in supported).
            output_schema: Expected output schema.

        Returns:
            Output message with findings from all inputs combined.

        """
        # Merge inputs, find patterns
        data_items = self._merge_input_data_items(inputs)
        findings = self._find_patterns_in_data_items(data_items)

        # Extract run_id from inputs (set by executor, used for cache scoping)
        run_id = inputs[0].run_id

        # Apply LLM validation if enabled
        validation_result: ValidationResult[PersonalDataIndicatorModel] | None = None
        final_findings = findings
        if self._config.llm_validation.enable_llm_validation:
            validated_findings, _, validation_result = self._validate_findings(
                findings, run_id=run_id
            )
            final_findings = validated_findings

        # Build and return output message
        return self._result_builder.build_output_message(
            final_findings,
            output_schema,
            validation_result,
        )

    def _validate_findings(
        self,
        findings: list[PersonalDataIndicatorModel],
        run_id: str | None = None,
    ) -> tuple[
        list[PersonalDataIndicatorModel],
        bool,
        ValidationResult[PersonalDataIndicatorModel] | None,
    ]:
        """Validate findings using ValidationOrchestrator.

        The orchestrator handles:
        - Grouping by category (when sampling is enabled)
        - Sampling and group-level decisions

        Args:
            findings: List of findings to validate.
            run_id: Unique identifier for the current run, used for cache scoping.

        Returns:
            Tuple of (validated findings, validation applied, validation result).

        """
        if not findings:
            return findings, False, None

        if not self._llm_service:
            logger.warning("LLM service unavailable, returning original findings")
            return findings, False, None

        try:
            # Create orchestrator and validate with marker callback
            # Marker is applied at strategy level to only mark actually-validated findings
            orchestrator = create_validation_orchestrator(
                self._config.llm_validation, self._llm_service
            )
            # TODO: Post-migration cleanup (once all processors use LLMService):
            #   Remove the None argument - orchestrator.validate() won't need llm_service param
            result = orchestrator.validate(
                findings,
                self._config.llm_validation,
                None,  # type: ignore[arg-type]  # Strategy uses constructor-injected service
                marker=self._mark_finding_validated,
                run_id=run_id,
            )

            logger.info(
                f"Validation complete: {len(findings)} → {len(result.kept_findings)} findings "
                f"({len(result.removed_groups)} groups removed)"
            )

            return result.kept_findings, result.all_succeeded, result

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            logger.warning("Returning original findings due to validation error")
            return findings, False, None

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
