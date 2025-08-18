"""Processing purpose analysis analyser for GDPR compliance."""

import logging
from typing import Any

from typing_extensions import Self, override

from wct.analysers.base import Analyser
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
        pattern_matcher: ProcessingPurposePatternMatcher,
    ) -> None:
        """Initialise the processing purpose analyser with specified configuration and pattern matcher.

        Args:
            config: Configuration object with analysis settings
            pattern_matcher: Pattern matcher for processing purpose detection

        """
        # Store strongly-typed configuration
        self._config: ProcessingPurposeAnalyserConfig = config
        self._pattern_matcher = pattern_matcher

        # Initialise source code handler for SourceCodeSchema processing
        self._source_code_handler = SourceCodeSchemaInputHandler()

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

        # Create pattern matcher with processing purpose specific strategy
        pattern_matcher = ProcessingPurposePatternMatcher(config.pattern_matching)

        return cls(config=config, pattern_matcher=pattern_matcher)

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

        logger.debug(f"Processing data with schema: {input_schema.name}")

        # Validate and parse data based on schema type
        if input_schema.name == "standard_input":
            typed_data = StandardInputDataModel.model_validate(message.content)
            findings = self._process_standard_input_data(typed_data)
        elif input_schema.name == "source_code":
            typed_data = parse_data_model(message.content, SourceCodeDataModel)
            findings = self._process_source_code_data(typed_data)
        else:
            raise ValueError(f"Unsupported input schema: {input_schema.name}")

        # Create and validate output message
        return self._create_output_message(findings, output_schema)

    def _process_standard_input_data(
        self, typed_data: StandardInputDataModel
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
            "ruleset_used": self._config.pattern_matching.ruleset,
            "llm_validation_enabled": self._config.llm_validation.enable_llm_validation,
            "evidence_context_size": self._config.pattern_matching.evidence_context_size,
        }

        output_message = Message(
            id="Processing_purpose_analysis",
            content=result_data,
            schema=output_schema,
        )

        # Validate the output message against the output schema
        output_message.validate()

        logger.debug(f"Processing purpose analysis completed with data: {result_data}")

        return output_message
