"""Processing purpose analysis analyser for GDPR compliance."""

from typing import Any

from typing_extensions import Self, override

from wct.analysers.base import Analyser
from wct.llm_service import LLMServiceError, LLMServiceFactory
from wct.message import Message
from wct.rulesets import RulesetLoader
from wct.schema import WctSchema

SUPPORTED_INPUT_SCHEMAS = [
    WctSchema(name="standard_input", type=dict[str, Any]),
    WctSchema(name="source_code", type=dict[str, Any]),
]

SUPPORTED_OUTPUT_SCHEMAS = [
    WctSchema(name="processing_purpose_finding", type=dict[str, Any]),
]

DEFAULT_INPUT_SCHEMA = SUPPORTED_INPUT_SCHEMAS[0]
DEFAULT_OUTPUT_SCHEMA = SUPPORTED_OUTPUT_SCHEMAS[0]


class ProcessingPurposeAnalyser(Analyser):
    """Analyser for identifying data processing purposes.

    This analyser identifies and categorises data processing purposes from textual
    content and source code to help organisations understand what they're using
    personal data for.
    """

    def __init__(
        self,
        ruleset_name: str = "processing_purposes",
        evidence_context_size: str = "medium",
        enable_llm_validation: bool = True,
        llm_batch_size: int = 10,
        confidence_threshold: float = 0.7,
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
        super().__init__()  # Initialize logger from base class
        self.ruleset_name = ruleset_name
        self.evidence_context_size = evidence_context_size
        self.enable_llm_validation = enable_llm_validation
        self.llm_batch_size = llm_batch_size
        self.confidence_threshold = confidence_threshold
        self._patterns = None
        self._llm_service = None

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "processing_purpose_analyser"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create analyser instance from properties."""
        ruleset_name = properties.get("ruleset", "processing_purposes")
        evidence_context_size = properties.get("evidence_context_size", "medium")
        enable_llm_validation = properties.get("enable_llm_validation", True)
        llm_batch_size = properties.get("llm_batch_size", 10)
        confidence_threshold = properties.get("confidence_threshold", 0.7)

        return cls(
            ruleset_name=ruleset_name,
            evidence_context_size=evidence_context_size,
            enable_llm_validation=enable_llm_validation,
            llm_batch_size=llm_batch_size,
            confidence_threshold=confidence_threshold,
        )

    @property
    def patterns(self) -> dict[str, Any]:
        """Get the loaded patterns, loading them if necessary."""
        if self._patterns is None:
            try:
                self._patterns = RulesetLoader.load_ruleset(self.ruleset_name)
                self.logger.info(f"Loaded ruleset: {self.ruleset_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load ruleset {self.ruleset_name}: {e}")
                # Fallback to empty patterns for skeleton implementation
                self._patterns = {}
        return self._patterns

    @property
    def llm_service(self):
        """Get the LLM service, creating it if necessary."""
        if self._llm_service is None and self.enable_llm_validation:
            try:
                self._llm_service = LLMServiceFactory.create_anthropic_service()
                self.logger.info(
                    "LLM service initialized for processing purpose analysis"
                )
            except LLMServiceError as e:
                self.logger.warning(
                    f"Failed to initialize LLM service: {e}. Continuing without LLM validation."
                )
                self.enable_llm_validation = False
        return self._llm_service

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
        findings = self._analyze_content_for_purposes(data)

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

    def _analyze_content_for_purposes(
        self, data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Analyze content for processing purposes.

        This is a skeleton method that will be implemented with actual
        purpose detection logic.

        Args:
            data: Input data to analyze

        Returns:
            List of processing purpose findings
        """
        self.logger.debug("Analyzing content for processing purposes")

        # TODO: Implement actual purpose detection logic
        # This could include:
        # - Pattern matching for common processing purposes
        # - LLM-based purpose classification
        # - Source code analysis for data usage patterns
        # - Business logic identification

        # Skeleton implementation - return empty findings for now
        findings = []

        # Example skeleton finding structure:
        # findings.append({
        #     "purpose": "Artificial Intelligence Compliance Management",
        #     "purpose_category": "AI_AND_ML",
        #     "risk_level": "low",
        #     "compliance_relevance": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF"],
        #     "matched_pattern": "compliance",
        #     "confidence": 0.8,
        #     "evidence": ["AI compliance framework", "regulatory dashboard"],
        #     "metadata": {"source": "form_field", "line": 42}
        # })

        self.logger.debug(f"Found {len(findings)} processing purpose indicators")
        return findings
