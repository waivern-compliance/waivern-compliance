"""Processing purpose analysis analyser for GDPR compliance."""

import logging
from typing import Any

from typing_extensions import Self, override

from wct.analysers.base import Analyser
from wct.analysers.runners import (
    PatternMatchingAnalysisRunner,
)
from wct.analysers.runners.types import PatternMatchingConfig
from wct.message import Message
from wct.schemas import (
    ProcessingPurposeFindingSchema,
    Schema,
    SourceCodeDataModel,
    SourceCodeSchema,
    StandardInputDataItemMetadataModel,
    StandardInputDataModel,
    StandardInputSchema,
    parse_data_model,
)

from .pattern_matcher import processing_purpose_pattern_matcher
from .source_code_schema_input_handler import SourceCodeSchemaInputHandler
from .types import ProcessingPurposeAnalyserConfig, ProcessingPurposeFindingModel

logger = logging.getLogger(__name__)

_SUPPORTED_INPUT_SCHEMAS: list[Schema] = [
    StandardInputSchema(),
    SourceCodeSchema(),
]

_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [
    ProcessingPurposeFindingSchema(),
]


class ProcessingPurposeAnalyser(Analyser):
    """Analyser for identifying data processing purposes.

    This analyser identifies and categorises data processing purposes from textual
    content to help organisations understand what they're using personal data for.
    """

    def __init__(
        self,
        config: ProcessingPurposeAnalyserConfig | None = None,
        pattern_runner: PatternMatchingAnalysisRunner[ProcessingPurposeFindingModel]
        | None = None,
    ) -> None:
        """Initialise the processing purpose analyser with specified configuration and runners.

        Args:
            config: Configuration object with analysis settings (uses defaults if None)
            pattern_runner: Pattern matching runner (optional, will create default if None)

        """
        # Store strongly-typed configuration (aligned with PersonalDataAnalyser)
        self.config: ProcessingPurposeAnalyserConfig = (
            config or ProcessingPurposeAnalyserConfig()
        )

        # Initialise pattern runner with processing purpose specific strategy
        # Note: ProcessingPurpose doesn't use LLM validation in current implementation
        self.pattern_runner = pattern_runner or PatternMatchingAnalysisRunner[
            ProcessingPurposeFindingModel
        ](pattern_matcher=processing_purpose_pattern_matcher)

        # Initialise source code handler for SourceCodeSchema processing
        self.source_code_handler = SourceCodeSchemaInputHandler()

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "processing_purpose_analyser"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create analyser instance from properties."""
        # Create and validate config using ProcessingPurposeAnalyserConfig
        config = ProcessingPurposeAnalyserConfig.from_properties(properties)

        return cls(config=config)

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
        """Process data to identify processing purposes using runners."""
        logger.info("Starting processing purpose analysis")

        # Validate input message
        Analyser._validate_input_message(message, input_schema)

        # Extract content from message
        data = message.content
        logger.debug(f"Processing data with schema: {input_schema.name}")

        # Process based on input schema type
        if input_schema.name == "standard_input":
            findings = self._process_standard_input_with_runners(data)
        elif input_schema.name == "source_code":
            findings = self._process_source_code_with_handler(data)
        else:
            raise ValueError(f"Unsupported input schema: {input_schema.name}")

        # Convert models to dicts for JSON output
        findings_dicts = [finding.model_dump() for finding in findings]

        # Create result data with findings
        result_data: dict[str, Any] = {
            "findings": findings_dicts,
            "summary": {
                "total_findings": len(findings),
                "high_confidence_count": len(
                    [
                        f
                        for f in findings
                        if f.confidence >= self.config.confidence_threshold
                    ]
                ),
                "purposes_identified": len(set(f.purpose for f in findings)),
            },
        }

        # Add analysis metadata
        result_data["analysis_metadata"] = {
            "ruleset_used": self.config.ruleset_name,
            "llm_validation_enabled": self.config.enable_llm_validation,
            "confidence_threshold": self.config.confidence_threshold,
            "evidence_context_size": self.config.evidence_context_size,
        }

        output_message = Message(
            id="Processing purpose analysis",
            content=result_data,
            schema=output_schema,
        )

        # Validate the output message against the output schema
        output_message.validate()

        logger.debug(f"Processing purpose analysis completed with data: {result_data}")

        return output_message

    def _process_standard_input_with_runners(
        self, data: dict[str, Any]
    ) -> list[ProcessingPurposeFindingModel]:
        """Process standard_input schema data using runners.

        Args:
            data: Input data in standard_input schema format

        Returns:
            List of findings from pattern matching

        """
        findings: list[ProcessingPurposeFindingModel] = []

        if "data" in data and isinstance(data["data"], list):
            # Validate and parse StandardInputData using Pydantic
            standard_input_data = StandardInputDataModel.model_validate(data)

            # Process each data item in the array using the pattern runner
            for data_item in standard_input_data.data:
                # Get content and metadata
                content = data_item.content
                item_metadata = data_item.metadata

                # Use pattern runner for analysis
                item_findings = self.pattern_runner.run_analysis(
                    content, item_metadata, self._get_pattern_matching_config()
                )
                findings.extend(item_findings)
        else:
            # Handle direct content format (fallback)
            content = data.get("content", "")
            metadata_dict = data.get("metadata", {})
            # Convert dict to model for type safety
            metadata = StandardInputDataItemMetadataModel.model_validate(metadata_dict)
            findings = self.pattern_runner.run_analysis(
                content, metadata, self._get_pattern_matching_config()
            )

        return findings

    def _process_source_code_with_handler(
        self, data: dict[str, Any]
    ) -> list[ProcessingPurposeFindingModel]:
        """Process source_code schema data using the source code handler.

        Args:
            data: Input data in source_code schema format

        Returns:
            List of processing purpose findings from source code analysis

        """
        # Parse and validate source code data
        source_code_data = parse_data_model(data, SourceCodeDataModel)

        # Use source code handler for analysis
        findings_dicts = self.source_code_handler.analyse_source_code_data(
            source_code_data
        )

        # Convert dict findings to models for type consistency
        findings = [
            ProcessingPurposeFindingModel.model_validate(finding_dict)
            for finding_dict in findings_dicts
        ]

        return findings

    def _get_pattern_matching_config(self) -> PatternMatchingConfig:
        """Extract pattern matching configuration from the full config."""
        return PatternMatchingConfig(
            ruleset=self.config.ruleset_name,
            maximum_evidence_count=3,  # Default max evidence count
            evidence_context_size=self.config.evidence_context_size,
        )
