"""Processing purpose analysis analyser for GDPR compliance."""

import logging
from typing import Any

from typing_extensions import Self, override

from wct.analysers.base import Analyser
from wct.analysers.runners import (
    PatternMatchingAnalysisRunner,
)
from wct.message import Message
from wct.schemas import (
    ProcessingPurposeFindingSchema,
    Schema,
    SourceCodeDataModel,
    SourceCodeSchema,
    StandardInputDataModel,
    StandardInputSchema,
    parse_data_model,
)

from .pattern_matcher import ProcessingPurposePatternMatcher
from .source_code_schema_input_handler import SourceCodeSchemaInputHandler
from .types import ProcessingPurposeAnalyserConfig, ProcessingPurposeFindingModel

logger = logging.getLogger(__name__)

# Private constants
_ANALYSER_NAME = "processing_purpose_analyser"
_ANALYSIS_MESSAGE_ID = "Processing purpose analysis"
_STANDARD_INPUT_SCHEMA_NAME = "standard_input"
_SOURCE_CODE_SCHEMA_NAME = "source_code"

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
        config: ProcessingPurposeAnalyserConfig,
        pattern_runner: PatternMatchingAnalysisRunner[ProcessingPurposeFindingModel],
    ) -> None:
        """Initialise the processing purpose analyser with specified configuration and runners.

        Args:
            config: Configuration object with analysis settings
            pattern_runner: Pattern matching runner for processing purpose detection

        """
        # Store strongly-typed configuration
        self.config: ProcessingPurposeAnalyserConfig = config
        self.pattern_runner = pattern_runner

        # Initialise source code handler for SourceCodeSchema processing
        self.source_code_handler = SourceCodeSchemaInputHandler()

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return _ANALYSER_NAME

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create analyser instance from properties."""
        # Create and validate config using ProcessingPurposeAnalyserConfig
        config = ProcessingPurposeAnalyserConfig.from_properties(properties)

        # Create pattern matcher with configuration
        pattern_matcher = ProcessingPurposePatternMatcher(config.pattern_matching)

        # Create pattern runner with processing purpose specific strategy
        pattern_runner = PatternMatchingAnalysisRunner[ProcessingPurposeFindingModel](
            pattern_matcher=pattern_matcher
        )

        return cls(config=config, pattern_runner=pattern_runner)

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

        # Process data based on schema type
        findings = self._process_data_by_schema(data, input_schema)

        # Create and validate output message
        return self._create_output_message(findings, output_schema)

    def _process_data_by_schema(
        self, data: dict[str, Any], input_schema: Schema
    ) -> list[ProcessingPurposeFindingModel]:
        """Process data based on input schema type.

        Args:
            data: Input data to process
            input_schema: Schema that determines processing method

        Returns:
            List of processing purpose findings

        """
        if input_schema.name == _STANDARD_INPUT_SCHEMA_NAME:
            return self._process_standard_input_with_runners(data)
        elif input_schema.name == _SOURCE_CODE_SCHEMA_NAME:
            return self._process_source_code_with_handler(data)
        else:
            raise ValueError(f"Unsupported input schema: {input_schema.name}")

    def _process_standard_input_with_runners(
        self, data: dict[str, Any]
    ) -> list[ProcessingPurposeFindingModel]:
        """Process standard_input schema data using runners.

        Args:
            data: Input data in standard_input schema format

        Returns:
            List of findings from pattern matching

        """
        # Validate and parse StandardInputData using Pydantic
        standard_input_data = StandardInputDataModel.model_validate(data)

        findings: list[ProcessingPurposeFindingModel] = []

        # Process each data item in the array using the pattern runner
        for data_item in standard_input_data.data:
            # Get content and metadata
            content = data_item.content
            item_metadata = data_item.metadata

            # Use pattern runner for analysis
            item_findings = self.pattern_runner.run_analysis(
                content, item_metadata, self.config.pattern_matching
            )
            findings.extend(item_findings)

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

    def _create_output_message(
        self, findings: list[ProcessingPurposeFindingModel], output_schema: Schema
    ) -> Message:
        """Create and validate output message.

        Args:
            findings: Processing purpose findings
            output_schema: Schema for output validation

        Returns:
            Validated output message

        """
        # Convert models to dicts for JSON output
        findings_dicts = [finding.model_dump() for finding in findings]

        # Create result data with findings
        result_data: dict[str, Any] = {
            "findings": findings_dicts,
            "summary": {
                "total_findings": len(findings),
                "purposes_identified": len(set(f.purpose for f in findings)),
            },
        }

        # Add analysis metadata
        result_data["analysis_metadata"] = {
            "ruleset_used": self.config.pattern_matching.ruleset,
            "llm_validation_enabled": self.config.llm_validation.enable_llm_validation,
            "evidence_context_size": self.config.pattern_matching.evidence_context_size,
        }

        output_message = Message(
            id=_ANALYSIS_MESSAGE_ID,
            content=result_data,
            schema=output_schema,
        )

        # Validate the output message against the output schema
        output_message.validate()

        logger.debug(f"Processing purpose analysis completed with data: {result_data}")

        return output_message
