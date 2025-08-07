"""Processing purpose analysis analyser for GDPR compliance."""

from typing import Any

from typing_extensions import Self, override

from wct.analysers.base import Analyser
from wct.analysers.base_compliance import BaseComplianceAnalyser
from wct.message import Message
from wct.schema import WctSchema

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


class ProcessingPurposeAnalyser(BaseComplianceAnalyser):
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
    ):
        """Initialize the processing purpose analyser.

        Args:
            ruleset_name: Name of the ruleset to use for analysis (default: "processing_purposes")
            evidence_context_size: Size of context around evidence matches
                                  ('small': 50 chars, 'medium': 100 chars, 'large': 200 chars, 'full': entire content)
            enable_llm_validation: Whether to use LLM for purpose classification (default: True)
            llm_batch_size: Number of findings to process in each LLM batch (default: 10)
            confidence_threshold: Minimum confidence score for accepting findings (default: 0.7)
        """
        super().__init__(
            ruleset_name=ruleset_name,
            evidence_context_size=evidence_context_size,
            enable_llm_validation=enable_llm_validation,
            llm_batch_size=llm_batch_size,
        )
        self.confidence_threshold = confidence_threshold

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
        """Process data to identify processing purposes.

        This is a skeleton implementation that will be expanded with actual
        processing purpose detection logic.
        """
        self.logger.info("Starting processing purpose analysis")

        # Validate input message
        Analyser.validate_input_message(message, input_schema)

        # Extract content from message
        data = message.content
        self.logger.debug(f"Processing data with schema: {input_schema.name}")

        # TODO: Implement actual processing purpose detection logic
        # For now, return a skeleton result
        findings = self._analyse_content_for_purposes(data)

        # Create result data with findings
        result_data: dict[str, Any] = {
            "findings": [
                {
                    "purpose": finding.get("purpose", "Unknown Processing Purpose"),
                    "purpose_category": finding.get("purpose_category", "OPERATIONAL"),
                    "risk_level": finding.get("risk_level", "low"),
                    "compliance_relevance": finding.get(
                        "compliance_relevance", ["GDPR"]
                    ),
                    "matched_pattern": finding.get("matched_pattern", ""),
                    # TODO: Implement confidence calculation logic (LLM-based)
                    "confidence": finding.get("confidence", 0.5),
                    "evidence": finding.get("evidence", []),
                    "metadata": finding.get("metadata", {}),
                }
                for finding in findings
            ],
            "summary": {
                "total_findings": len(findings),
                "high_confidence_count": len(
                    [
                        f
                        for f in findings
                        if f.get("confidence", 0) >= self.confidence_threshold
                    ]
                ),
                "purposes_identified": len(set(f.get("purpose") for f in findings)),
            },
        }

        # Add analysis metadata
        result_data["analysis_metadata"] = {
            "ruleset_used": self.ruleset_name,
            "llm_validation_enabled": self.enable_llm_validation,
            "confidence_threshold": self.confidence_threshold,
            "evidence_context_size": self.evidence_context_size,
        }

        output_message = Message(
            id="Processing purpose analysis",
            content=result_data,
            schema=output_schema,
        )

        # Validate the output message against the output schema
        output_message.validate()

        self.logger.info(
            f"Processing purpose analysis completed with {len(findings)} findings"
        )
        return output_message

    def _analyse_content_for_purposes(
        self, data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Analyze content for processing purposes.

        Analyzes textual content to identify processing purposes using pattern matching
        against the processing_purposes ruleset.

        Args:
            data: Input data to analyse (standard_input schema format)

        Returns:
            List of processing purpose findings
        """
        self.logger.debug("Analyzing content for processing purposes")
        findings = self._process_standard_input_data(data)
        self.logger.debug(f"Found {len(findings)} processing purpose indicators")
        return findings

    @override
    def analyse_content_item(
        self, content: str, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Analyze a single content item for processing purposes.

        Args:
            content: Text content to analyse
            metadata: Metadata about the content source

        Returns:
            List of processing purpose findings for this content
        """
        findings = []

        if not content.strip():
            return findings

        content_lower = content.lower()

        # Iterate through all processing purposes in the ruleset
        for purpose_name, purpose_data in self.patterns.items():
            patterns = purpose_data.get("patterns", [])

            # Check if any pattern matches in the content
            for pattern in patterns:
                if pattern.lower() in content_lower:
                    # Extract evidence snippets
                    evidence = self._extract_evidence(content, pattern)

                    if evidence:  # Only create finding if we have evidence
                        # Use default confidence for all findings
                        confidence = DEFAULT_FINDING_CONFIDENCE

                        finding = {
                            "purpose": purpose_name,
                            "purpose_category": purpose_data.get(
                                "purpose_category", "OPERATIONAL"
                            ),
                            "risk_level": purpose_data.get("risk_level", "low"),
                            "compliance_relevance": purpose_data.get(
                                "compliance_relevance", ["GDPR"]
                            ),
                            "matched_pattern": pattern,
                            "confidence": confidence,
                            "evidence": evidence,
                            "metadata": metadata.copy() if metadata else {},
                        }
                        findings.append(finding)

                        self.logger.debug(
                            f"Found purpose '{purpose_name}' with pattern '{pattern}' (confidence: {confidence:.2f})"
                        )

                        # Only match one pattern per purpose to avoid duplicates
                        break

        return findings
