"""Processing purpose analysis analyser for GDPR compliance."""

import importlib
import logging
from types import ModuleType
from typing import Any, override

from waivern_core import Analyser
from waivern_core.message import Message
from waivern_core.schemas import (
    AnalysisChainEntry,
    BaseAnalysisOutputMetadata,
    BaseMetadata,
    Schema,
    StandardInputDataModel,
)
from waivern_llm import BaseLLMService
from waivern_source_code.schemas import (
    SourceCodeDataModel,
)

from .llm_validation_strategy import processing_purpose_validation_strategy
from .pattern_matcher import ProcessingPurposePatternMatcher
from .schemas.types import ProcessingPurposeFindingModel
from .source_code_schema_input_handler import SourceCodeSchemaInputHandler
from .types import ProcessingPurposeAnalyserConfig

logger = logging.getLogger(__name__)

_SUPPORTED_INPUT_SCHEMAS: list[Schema] = [
    Schema("standard_input", "1.0.0"),
    Schema("source_code", "1.0.0"),
]

_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [
    Schema("processing_purpose_finding", "1.0.0")
]


class ProcessingPurposeAnalyser(Analyser):
    """Analyser for identifying data processing purposes.

    This analyser identifies and categorises data processing purposes from textual
    content to help organisations understand what they're using personal data for.
    """

    def __init__(
        self,
        config: ProcessingPurposeAnalyserConfig,
        llm_service: BaseLLMService | None = None,
    ) -> None:
        """Initialise the processing purpose analyser with dependency injection.

        Args:
            config: Configuration object with analysis settings
            llm_service: Optional LLM service for validation (injected by factory)

        """
        # Store strongly-typed configuration
        self._config: ProcessingPurposeAnalyserConfig = config
        self._pattern_matcher = ProcessingPurposePatternMatcher(config.pattern_matching)
        self._llm_service = llm_service

        # Initialise source code handler for SourceCodeSchema processing
        self._source_code_handler = SourceCodeSchemaInputHandler()

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "processing_purpose_analyser"

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
            f"waivern_processing_purpose_analyser.schema_readers.{module_name}"
        )

    def _load_producer(self, schema: Schema) -> ModuleType:
        """Dynamically import producer module.

        Python's import system automatically caches modules in sys.modules,
        so repeated imports are fast and don't require manual caching.

        Args:
            schema: Output schema to load producer for

        Returns:
            Producer module with produce() function

        Raises:
            ModuleNotFoundError: If producer module doesn't exist for this version

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(
            f"waivern_processing_purpose_analyser.schema_producers.{module_name}"
        )

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[Schema]:
        """Return the input schemas supported by this analyser."""
        return _SUPPORTED_INPUT_SCHEMAS

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this analyser."""
        return _SUPPORTED_OUTPUT_SCHEMAS

    @override
    def process(
        self,
        input_schema: Schema,
        output_schema: Schema,
        message: Message,
    ) -> Message:
        """Process data to identify processing purposes using dynamic reader/producer."""
        logger.info("Starting processing purpose analysis")

        # Validate input message
        Analyser.validate_input_message(message, input_schema)

        logger.debug(f"Processing data with schema: {input_schema.name}")

        # Load reader and transform to canonical Pydantic model
        try:
            reader = self._load_reader(input_schema)
            typed_data = reader.read(message.content)
        except (ModuleNotFoundError, AttributeError) as e:
            raise ValueError(f"Unsupported input schema: {input_schema.name}") from e

        # Process based on schema type
        if input_schema.name == "standard_input":
            findings = self._process_standard_input_data(typed_data)
        elif input_schema.name == "source_code":
            findings = self._process_source_code_data(typed_data)
        else:
            raise ValueError(f"Unsupported input schema: {input_schema.name}")

        # Apply LLM validation if enabled and findings exist
        validated_findings, validation_applied = self._validate_findings_with_llm(
            findings
        )

        # Update analysis chain with this analyser
        updated_chain_dicts = self.update_analyses_chain(
            message, "processing_purpose_analyser"
        )
        # Convert to strongly-typed models for WCT
        updated_chain = [AnalysisChainEntry(**entry) for entry in updated_chain_dicts]

        # Create and validate output message
        return self._create_output_message(
            findings,
            validated_findings,
            validation_applied,
            output_schema,
            updated_chain,
        )

    def _process_standard_input_data(
        self, typed_data: StandardInputDataModel[BaseMetadata]
    ) -> list[ProcessingPurposeFindingModel]:
        """Process standard_input schema data using runners.

        Args:
            typed_data: Validated standard input data

        Returns:
            List of findings from pattern matching

        """
        findings: list[ProcessingPurposeFindingModel] = []

        # Process each data item in the array using the pattern runner
        for data_item in typed_data.data:
            # Get content and metadata
            content = data_item.content
            item_metadata = data_item.metadata

            # Use pattern matcher for analysis
            item_findings = self._pattern_matcher.find_patterns(content, item_metadata)
            findings.extend(item_findings)

        return findings

    def _process_source_code_data(
        self, typed_data: SourceCodeDataModel
    ) -> list[ProcessingPurposeFindingModel]:
        """Process source_code schema data using the source code handler.

        Args:
            typed_data: Validated source code data

        Returns:
            List of processing purpose findings from source code analysis

        """
        # Use source code handler for analysis - returns strongly typed models
        findings = self._source_code_handler.analyse_source_code_data(typed_data)

        return findings

    def _validate_findings_with_llm(
        self, findings: list[ProcessingPurposeFindingModel]
    ) -> tuple[list[ProcessingPurposeFindingModel], bool]:
        """Validate findings using LLM if enabled and available.

        Args:
            findings: List of findings to validate

        Returns:
            Tuple of (validated findings, validation_was_applied)

        """
        if not self._config.llm_validation.enable_llm_validation:
            return findings, False

        if not findings:
            return findings, False

        if not self._llm_service:
            logger.warning("LLM service unavailable, returning original findings")
            return findings, False

        try:
            validated_findings, validation_succeeded = (
                processing_purpose_validation_strategy(
                    findings, self._config.llm_validation, self._llm_service
                )
            )
            return validated_findings, validation_succeeded
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            logger.warning("Returning original findings due to validation error")
            return findings, False

    def _create_output_message(
        self,
        original_findings: list[ProcessingPurposeFindingModel],
        validated_findings: list[ProcessingPurposeFindingModel],
        validation_applied: bool,
        output_schema: Schema,
        analyses_chain: list[AnalysisChainEntry],
    ) -> Message:
        """Create and validate output message using producer.

        Args:
            original_findings: Original findings before LLM validation
            validated_findings: Findings after LLM validation
            validation_applied: Whether LLM validation was actually applied
            output_schema: Schema for output validation
            analyses_chain: Updated analysis chain with proper ordering

        Returns:
            Validated output message

        """
        # Build summary statistics
        summary = self._build_findings_summary(validated_findings)

        # Build validation summary separately if LLM validation was actually applied
        validation_summary = None
        if validation_applied and len(original_findings) > 0:
            validation_summary = self._build_validation_summary(
                original_findings, validated_findings
            )

        # Add enhanced analysis metadata with additional fields
        extra_fields = {
            "llm_validation_mode": self._config.llm_validation.llm_validation_mode,
            "llm_batch_size": self._config.llm_validation.llm_batch_size,
            "analyser_version": "1.0.0",
            "processing_purpose_categories_detected": len(
                set(
                    f.purpose_category for f in validated_findings if f.purpose_category
                )
            ),
        }

        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used=self._config.pattern_matching.ruleset,
            llm_validation_enabled=self._config.llm_validation.enable_llm_validation,
            evidence_context_size=self._config.pattern_matching.evidence_context_size,
            analyses_chain=analyses_chain,
            **extra_fields,
        )

        # Load producer and transform to wire format
        producer = self._load_producer(output_schema)
        result_data = producer.produce(
            findings=validated_findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
            validation_summary=validation_summary,
        )

        output_message = Message(
            id="Processing_purpose_analysis",
            content=result_data,
            schema=output_schema,
        )

        # Validate the output message against the output schema
        output_message.validate()

        logger.debug(f"Processing purpose analysis completed with data: {result_data}")

        return output_message

    def _build_findings_summary(
        self, findings: list[ProcessingPurposeFindingModel]
    ) -> dict[str, Any]:
        """Build summary statistics for processing purpose findings.

        Args:
            findings: List of validated findings

        Returns:
            Summary statistics dictionary with purpose categories, risk levels, and totals

        """
        if not findings:
            return {
                "total_findings": 0,
                "purposes_identified": 0,
                "high_risk_count": 0,
                "purpose_categories": {},
                "risk_level_distribution": {"low": 0, "medium": 0, "high": 0},
            }

        # Count unique purposes and categories
        unique_purposes = set(f.purpose for f in findings)
        purpose_categories: dict[str, int] = {}
        risk_distribution = {"low": 0, "medium": 0, "high": 0}

        for finding in findings:
            # Count purpose categories
            category = finding.purpose_category or "uncategorised"
            purpose_categories[category] = purpose_categories.get(category, 0) + 1

            # Count risk levels
            risk_distribution[finding.risk_level] = (
                risk_distribution.get(finding.risk_level, 0) + 1
            )

        return {
            "total_findings": len(findings),
            "purposes_identified": len(unique_purposes),
            "high_risk_count": risk_distribution["high"],
            "purpose_categories": purpose_categories,
            "risk_level_distribution": risk_distribution,
        }

    def _build_validation_summary(
        self,
        original_findings: list[ProcessingPurposeFindingModel],
        validated_findings: list[ProcessingPurposeFindingModel],
    ) -> dict[str, Any]:
        """Build LLM validation summary statistics for processing purposes.

        Args:
            original_findings: Original findings before validation
            validated_findings: Findings after validation

        Returns:
            Validation summary dictionary with effectiveness metrics

        """
        original_count = len(original_findings)
        validated_count = len(validated_findings)
        false_positives_removed = original_count - validated_count

        # Calculate effectiveness metrics
        if original_count > 0:
            validation_effectiveness = (false_positives_removed / original_count) * 100
        else:
            validation_effectiveness = 0.0

        # Analyze which purposes were removed (false positives)
        original_purposes = {f.purpose for f in original_findings}
        validated_purposes = {f.purpose for f in validated_findings}
        removed_purposes = original_purposes - validated_purposes

        logger.info(
            f"LLM validation completed: {original_count} → {validated_count} findings "
            f"({false_positives_removed} false positives removed, {validation_effectiveness:.1f}% effectiveness)"
        )

        return {
            "llm_validation_enabled": True,
            "original_findings_count": original_count,
            "validated_findings_count": validated_count,
            "false_positives_removed": false_positives_removed,
            "validation_effectiveness_percentage": round(validation_effectiveness, 1),
            "validation_mode": self._config.llm_validation.llm_validation_mode,
            "removed_purposes": sorted(list(removed_purposes)),
        }
