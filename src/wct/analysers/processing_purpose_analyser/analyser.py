"""Processing purpose analysis analyser for GDPR compliance."""

from typing import Any

from typing_extensions import Self, override

from wct.analysers.base import Analyser
from wct.analysers.runners import PatternMatchingRunner
from wct.message import Message
from wct.schema import WctSchema

from .pattern_matcher import processing_purpose_pattern_matcher

SUPPORTED_INPUT_SCHEMAS = [
    WctSchema(name="standard_input", type=dict[str, Any]),
]

SUPPORTED_OUTPUT_SCHEMAS = [
    WctSchema(name="processing_purpose_finding", type=dict[str, Any]),
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


class ProcessingPurposeAnalyser(Analyser):
    """Analyser for identifying data processing purposes.

    This analyser identifies and categorises data processing purposes from textual
    content to help organisations understand what they're using personal data for.
    """

    def __init__(
        self,
        ruleset_name: str = DEFAULT_RULESET_NAME,
        evidence_context_size: str = DEFAULT_EVIDENCE_CONTEXT_SIZE,
        enable_llm_validation: bool = DEFAULT_ENABLE_LLM_VALIDATION,
        llm_batch_size: int = DEFAULT_LLM_BATCH_SIZE,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        pattern_runner: PatternMatchingRunner | None = None,
    ):
        """Initialize the processing purpose analyser with specified configuration and runners.

        Args:
            ruleset_name: Name of the ruleset to use for analysis (default: "processing_purposes")
            evidence_context_size: Size of context around evidence matches
                                  ('small': 50 chars, 'medium': 100 chars, 'large': 200 chars, 'full': entire content)
            enable_llm_validation: Whether to use LLM for purpose classification (default: True)
            llm_batch_size: Number of findings to process in each LLM batch (default: 10)
            confidence_threshold: Minimum confidence score for accepting findings (default: 0.7)
            pattern_runner: Pattern matching runner (optional, will create default if None)
        """
        super().__init__()  # Call Analyser.__init__ directly

        # Store configuration
        self.config = {
            "ruleset_name": ruleset_name,
            "evidence_context_size": evidence_context_size,
            "enable_llm_validation": enable_llm_validation,
            "llm_batch_size": llm_batch_size,
            "confidence_threshold": confidence_threshold,
            "confidence": DEFAULT_FINDING_CONFIDENCE,  # Default confidence for all findings
            "max_evidence": 3,  # Default max evidence count
        }

        # Initialize pattern runner with processing purpose specific strategy
        # Note: ProcessingPurpose doesn't use LLM validation in current implementation
        self.pattern_runner = pattern_runner or PatternMatchingRunner(
            pattern_matcher=processing_purpose_pattern_matcher
        )

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

        return cls(
            ruleset_name=ruleset_name,
            evidence_context_size=evidence_context_size,
            enable_llm_validation=enable_llm_validation,
            llm_batch_size=llm_batch_size,
            confidence_threshold=confidence_threshold,
        )

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[WctSchema[Any]]:
        """Return the input schemas supported by this analyser."""
        return SUPPORTED_INPUT_SCHEMAS

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[WctSchema[Any]]:
        """Return the output schemas supported by this analyser."""
        return SUPPORTED_OUTPUT_SCHEMAS

    @override
    def process(
        self,
        input_schema: WctSchema[Any],
        output_schema: WctSchema[Any],
        message: Message,
    ) -> Message:
        """Process data to identify processing purposes using runners."""
        self.logger.info("Starting processing purpose analysis")

        # Validate input message
        Analyser.validate_input_message(message, input_schema)

        # Extract content from message
        data = message.content
        self.logger.debug(f"Processing data with schema: {input_schema.name}")

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

        self.logger.debug(
            f"Processing purpose analysis completed with data: {result_data}"
        )

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
        findings = []

        if "data" in data and isinstance(data["data"], list):
            # Process each data item in the array using the pattern runner
            for item in data["data"]:
                content = item.get("content", "")
                item_metadata = item.get("metadata", {})

                # Use pattern runner for analysis
                item_findings = self.pattern_runner.run_analysis(
                    content, item_metadata, self.config
                )
                findings.extend(item_findings)
        else:
            # Handle direct content format (fallback)
            content = data.get("content", "")
            metadata = data.get("metadata", {})
            findings = self.pattern_runner.run_analysis(content, metadata, self.config)

        return findings
