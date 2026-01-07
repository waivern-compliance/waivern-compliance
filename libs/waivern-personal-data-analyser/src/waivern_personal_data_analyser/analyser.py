"""Personal data analysis analyser."""

import importlib
import logging
from pprint import pformat
from types import ModuleType
from typing import cast, override

from waivern_core import Analyser, InputRequirement, update_analyses_chain
from waivern_core.message import Message
from waivern_core.schemas import (
    AnalysisChainEntry,
    BaseAnalysisOutputMetadata,
    BaseMetadata,
    ChainEntryValidationStats,
    Schema,
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_llm import BaseLLMService

from .llm_validation_strategy import personal_data_validation_strategy
from .pattern_matcher import PersonalDataPatternMatcher
from .schemas.types import (
    PersonalDataIndicatorModel,
    PersonalDataIndicatorOutput,
    PersonalDataIndicatorSummary,
    PersonalDataValidationSummary,
)
from .types import PersonalDataAnalyserConfig

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
        llm_service: BaseLLMService | None = None,
    ) -> None:
        """Initialise the analyser with dependency injection.

        Args:
            config: Validated configuration object
            llm_service: Optional LLM service for validation (injected by factory)

        """
        self._config = config
        self._pattern_matcher = PersonalDataPatternMatcher(config.pattern_matching)
        self._llm_service = llm_service

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

    def _load_reader(self, schema: Schema) -> ModuleType:
        """Dynamically import reader module.

        Python's import system automatically caches modules in sys.modules,
        so repeated imports are fast and don't require manual caching.

        Args:
            schema: Input schema to load reader for

        Returns:
            Reader module with read() function

        Raises:
            ModuleNotFoundError: If reader module doesn't exist for this version

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(
            f"waivern_personal_data_analyser.schema_readers.{module_name}"
        )

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
        # Merge all input data items (same-schema fan-in)
        all_data_items: list[StandardInputDataItemModel[BaseMetadata]] = []
        for message in inputs:
            reader = self._load_reader(message.schema)
            typed_data = cast(
                StandardInputDataModel[BaseMetadata], reader.read(message.content)
            )
            all_data_items.extend(typed_data.data)

        # Process each data item using the pattern matcher
        findings: list[PersonalDataIndicatorModel] = []
        for data_item in all_data_items:
            content = data_item.content
            item_metadata = data_item.metadata

            item_findings = self._pattern_matcher.find_patterns(content, item_metadata)
            findings.extend(item_findings)

        # Run LLM validation if enabled
        validated_findings = self._validate_findings_with_llm(findings)

        # Build chain entry validation stats if validation actually ran
        validation_applied = (
            self._config.llm_validation.enable_llm_validation and len(findings) > 0
        )
        chain_validation_stats = ChainEntryValidationStats.from_counts(
            validation_applied=validation_applied,
            original_count=len(findings),
            validated_count=len(validated_findings),
            validation_mode=self._config.llm_validation.llm_validation_mode,
        )

        # Update analysis chain using first input message
        updated_chain_dicts = update_analyses_chain(
            inputs[0], "personal_data_analyser", validation_stats=chain_validation_stats
        )
        # Convert to strongly-typed models for WCT
        updated_chain = [AnalysisChainEntry(**entry) for entry in updated_chain_dicts]

        # Create and validate output message
        return self._create_output_message(
            findings, validated_findings, output_schema, updated_chain
        )

    def _create_output_message(
        self,
        original_findings: list[PersonalDataIndicatorModel],
        validated_findings: list[PersonalDataIndicatorModel],
        output_schema: Schema,
        analyses_chain: list[AnalysisChainEntry],
    ) -> Message:
        """Create and validate output message using output model.

        Args:
            original_findings: Original findings before LLM validation
            validated_findings: Findings after LLM validation
            output_schema: Schema for output validation
            analyses_chain: Updated analysis chain with proper ordering

        Returns:
            Validated output message

        """
        # Build summary
        summary = self._build_findings_summary(validated_findings)

        # Build validation summary if applicable
        validation_summary = None
        if (
            self._config.llm_validation.enable_llm_validation
            and len(original_findings) > 0
        ):
            validation_summary = self._build_validation_summary(
                original_findings, validated_findings
            )

        # Build analysis metadata for chaining support
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used=self._config.pattern_matching.ruleset,
            llm_validation_enabled=self._config.llm_validation.enable_llm_validation,
            evidence_context_size=self._config.pattern_matching.evidence_context_size,
            analyses_chain=analyses_chain,
        )

        # Create output model (Pydantic validates at construction)
        output_model = PersonalDataIndicatorOutput(
            findings=validated_findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
            validation_summary=validation_summary,
        )

        # Convert to wire format
        result_data = output_model.model_dump(mode="json", exclude_none=True)

        output_message = Message(
            id="Personal_data_analysis",
            content=result_data,
            schema=output_schema,
        )

        output_message.validate()

        logger.info(
            f"PersonalDataAnalyser processed with {len(result_data['findings'])} findings"
        )

        logger.debug(
            f"PersonalDataAnalyser processed with findings:\n{pformat(result_data)}"
        )

        return output_message

    def _validate_findings_with_llm(
        self, findings: list[PersonalDataIndicatorModel]
    ) -> list[PersonalDataIndicatorModel]:
        """Validate findings using LLM if enabled and available.

        Args:
            findings: List of findings to validate

        Returns:
            List of validated findings (filtered/modified by LLM validation)

        """
        if not self._config.llm_validation.enable_llm_validation:
            return findings

        if not findings:
            return findings

        if self._llm_service is None:
            logger.warning("LLM service not available, skipping validation")
            return findings

        try:
            logger.info(f"Starting LLM validation of {len(findings)} findings")

            validated_findings, validation_succeeded = (
                personal_data_validation_strategy(
                    findings, self._config.llm_validation, self._llm_service
                )
            )

            if validation_succeeded:
                logger.info(
                    f"LLM validation completed: {len(findings)} → {len(validated_findings)} findings"
                )
            else:
                logger.warning("LLM validation failed, using original findings")

            return validated_findings

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            logger.warning("Returning unvalidated findings due to LLM validation error")
            return findings

    def _build_findings_summary(
        self, findings: list[PersonalDataIndicatorModel]
    ) -> PersonalDataIndicatorSummary:
        """Build summary statistics for indicators.

        Args:
            findings: List of validated indicators

        Returns:
            Summary statistics model

        """
        return PersonalDataIndicatorSummary(
            total_findings=len(findings),
        )

    def _build_validation_summary(
        self,
        original_findings: list[PersonalDataIndicatorModel],
        validated_findings: list[PersonalDataIndicatorModel],
    ) -> PersonalDataValidationSummary:
        """Build LLM validation summary statistics.

        Args:
            original_findings: Original findings before validation
            validated_findings: Findings after validation

        Returns:
            Validation summary model

        """
        original_count = len(original_findings)
        validated_count = len(validated_findings)
        false_positives_removed = original_count - validated_count

        logger.info(
            f"LLM validation completed: {original_count} → {validated_count} findings "
            f"({false_positives_removed} false positives removed)"
        )

        return PersonalDataValidationSummary(
            llm_validation_enabled=True,
            original_findings_count=original_count,
            validated_findings_count=validated_count,
            false_positives_removed=false_positives_removed,
            validation_mode=self._config.llm_validation.llm_validation_mode,
        )
