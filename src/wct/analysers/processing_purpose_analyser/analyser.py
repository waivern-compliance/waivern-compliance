"""Processing purpose analysis analyser for GDPR compliance."""

import logging
from dataclasses import dataclass
from typing import Any, cast

from typing_extensions import Self, override

from wct.analysers.base import Analyser
from wct.analysers.runners import (
    PatternMatchingAnalysisRunner,
    PatternMatchingRunnerConfig,
)
from wct.message import Message
from wct.schemas import (
    ProcessingPurposeFindingSchema,
    Schema,
    StandardInputData,
    StandardInputSchema,
)

from .pattern_matcher import processing_purpose_pattern_matcher

logger = logging.getLogger(__name__)

SUPPORTED_INPUT_SCHEMAS: list[Schema] = [
    StandardInputSchema(),
]

SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [
    ProcessingPurposeFindingSchema(),
]

DEFAULT_INPUT_SCHEMA = SUPPORTED_INPUT_SCHEMAS[0]
DEFAULT_OUTPUT_SCHEMA = SUPPORTED_OUTPUT_SCHEMAS[0]

# Default configuration values
DEFAULT_RULESET_NAME = "processing_purposes"
DEFAULT_EVIDENCE_CONTEXT_SIZE = "medium"
DEFAULT_ENABLE_LLM_VALIDATION = True
DEFAULT_LLM_BATCH_SIZE = 30
DEFAULT_CONFIDENCE_THRESHOLD = 0.8

# Default confidence for all findings
DEFAULT_FINDING_CONFIDENCE = 0.5


@dataclass
class ProcessingPurposeAnalyserConfig:
    """Configuration for ProcessingPurposeAnalyser.

    Groups related configuration parameters to reduce constructor complexity.
    """

    ruleset_name: str = DEFAULT_RULESET_NAME
    evidence_context_size: str = DEFAULT_EVIDENCE_CONTEXT_SIZE
    enable_llm_validation: bool = DEFAULT_ENABLE_LLM_VALIDATION
    llm_batch_size: int = DEFAULT_LLM_BATCH_SIZE
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD


class ProcessingPurposeAnalyser(Analyser):
    """Analyser for identifying data processing purposes.

    This analyser identifies and categorises data processing purposes from textual
    content to help organisations understand what they're using personal data for.
    """

    def __init__(
        self,
        config: ProcessingPurposeAnalyserConfig | None = None,
        pattern_runner: PatternMatchingAnalysisRunner[dict[str, Any]] | None = None,
    ) -> None:
        """Initialise the processing purpose analyser with specified configuration and runners.

        Args:
            config: Configuration object with analysis settings (uses defaults if None)
            pattern_runner: Pattern matching runner (optional, will create default if None)

        """
        super().__init__()  # Call Analyser.__init__ directly

        # Store configuration
        analysis_config = config or ProcessingPurposeAnalyserConfig()
        self.config = {
            "ruleset_name": analysis_config.ruleset_name,
            "evidence_context_size": analysis_config.evidence_context_size,
            "enable_llm_validation": analysis_config.enable_llm_validation,
            "llm_batch_size": analysis_config.llm_batch_size,
            "confidence_threshold": analysis_config.confidence_threshold,
            "confidence": DEFAULT_FINDING_CONFIDENCE,  # Default confidence for all findings
            "max_evidence": 3,  # Default max evidence count
        }

        # Initialise pattern runner with processing purpose specific strategy
        # Note: ProcessingPurpose doesn't use LLM validation in current implementation
        self.pattern_runner = pattern_runner or PatternMatchingAnalysisRunner[
            dict[str, Any]
        ](pattern_matcher=processing_purpose_pattern_matcher)

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "processing_purpose_analyser"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create analyser instance from properties."""
        ruleset_name = properties.get("ruleset", DEFAULT_RULESET_NAME)
        evidence_context_size = properties.get(
            "evidence_context_size", DEFAULT_EVIDENCE_CONTEXT_SIZE
        )
        enable_llm_validation = properties.get(
            "enable_llm_validation", DEFAULT_ENABLE_LLM_VALIDATION
        )
        llm_batch_size = properties.get("llm_batch_size", DEFAULT_LLM_BATCH_SIZE)
        confidence_threshold = properties.get(
            "confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD
        )

        config = ProcessingPurposeAnalyserConfig(
            ruleset_name=ruleset_name,
            evidence_context_size=evidence_context_size,
            enable_llm_validation=enable_llm_validation,
            llm_batch_size=llm_batch_size,
            confidence_threshold=confidence_threshold,
        )

        return cls(config=config)

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[Schema]:
        """Return the input schemas supported by this analyser."""
        return SUPPORTED_INPUT_SCHEMAS

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this analyser."""
        return SUPPORTED_OUTPUT_SCHEMAS

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

        # Process standard_input schema using pattern runner
        findings = self._process_standard_input_with_runners(data)

        # Create result data with findings (findings are already in correct format from pattern matcher)
        result_data: dict[str, Any] = {
            "findings": findings,
            "summary": {
                "total_findings": len(findings),
                "high_confidence_count": len(
                    [
                        f
                        for f in findings
                        if f.get("confidence", 0) >= self.config["confidence_threshold"]
                    ]
                ),
                "purposes_identified": len(set(f.get("purpose") for f in findings)),
            },
        }

        # Add analysis metadata
        result_data["analysis_metadata"] = {
            "ruleset_used": self.config["ruleset_name"],
            "llm_validation_enabled": self.config["enable_llm_validation"],
            "confidence_threshold": self.config["confidence_threshold"],
            "evidence_context_size": self.config["evidence_context_size"],
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
    ) -> list[dict[str, Any]]:
        """Process standard_input schema data using runners.

        Args:
            data: Input data in standard_input schema format

        Returns:
            List of findings from pattern matching

        """
        findings: list[dict[str, Any]] = []

        if "data" in data and isinstance(data["data"], list):
            # Type narrowing: we know this is StandardInputData structure
            standard_input_data = cast(StandardInputData, data)

            # Process each data item in the array using the pattern runner
            for data_item in standard_input_data["data"]:
                # Get content and metadata (types guaranteed by StandardInputDataItem)
                content = data_item["content"]
                item_metadata = cast(dict[str, Any], data_item["metadata"])

                # Use pattern runner for analysis
                item_findings = self.pattern_runner.run_analysis(
                    content, item_metadata, self._get_pattern_matching_config()
                )
                findings.extend(item_findings)
        else:
            # Handle direct content format (fallback)
            content = data.get("content", "")
            metadata = data.get("metadata", {})
            findings = self.pattern_runner.run_analysis(
                content, metadata, self._get_pattern_matching_config()
            )

        return findings

    def _get_pattern_matching_config(self) -> PatternMatchingRunnerConfig:
        """Extract pattern matching configuration from the full config."""
        return PatternMatchingRunnerConfig(
            ruleset_name=str(self.config.get("ruleset_name", "processing_purposes")),
            max_evidence=int(self.config.get("max_evidence", 3)),
            maximum_evidence_count=int(self.config.get("maximum_evidence_count", 3)),
            context_size=str(self.config.get("context_size", "medium")),
            evidence_context_size=str(
                self.config.get("evidence_context_size", "medium")
            ),
        )
