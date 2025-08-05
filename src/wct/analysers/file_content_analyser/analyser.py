"""Content analysis analyser for detecting sensitive information."""

import re
from pprint import pformat
from typing import Any

from typing_extensions import Self, override

from wct.analysers.base import Analyser
from wct.message import Message
from wct.schema import WctSchema

SUPPORTED_INPUT_SCHEMAS = [
    WctSchema(name="text", type=dict[str, Any]),
]

SUPPORTED_OUTPUT_SCHEMAS = [
    WctSchema(name="file_content_analysis_result", type=dict[str, Any]),
]

DEFAULT_INPUT_SCHEMA = SUPPORTED_INPUT_SCHEMAS[0]
DEFAULT_OUTPUT_SCHEMA = SUPPORTED_OUTPUT_SCHEMAS[0]


class FileContentAnalyser(Analyser):
    """Analyzes file content for potentially sensitive information.

    This analyser looks for patterns that might indicate sensitive data
    like email addresses, potential passwords, API keys, etc.
    """

    # Number of characters to show at the end of masked sensitive values
    MASK_VISIBLE_CHARS = 3

    # Risk level thresholds
    CRITICAL_RISK_THRESHOLD = 50
    HIGH_RISK_THRESHOLD = 20
    MEDIUM_RISK_THRESHOLD = 5

    def __init__(self, sensitivity_level: str = "medium"):
        super().__init__()  # Initialize logger from base class
        self.sensitivity_level = sensitivity_level

        # Define patterns for different types of sensitive data
        self.patterns = {
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "potential_password": re.compile(
                r'(?i)(password|pwd|pass)\s*[:=]\s*[\'"]?([^\'"\s]+)[\'"]?'
            ),
            "api_key": re.compile(
                r'(?i)(api[\s_]?key|apikey|access[\s_]?key)\s*[:=]\s*[\'"]?([A-Za-z0-9]{20,})[\'"]?'
            ),
        }

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

    @classmethod
    @override
    def get_name(cls) -> str:
        return "file_content_analyser"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        sensitivity_level = properties.get("sensitivity_level", "medium")
        return cls(sensitivity_level=sensitivity_level)

    @override
    def process(
        self,
        input_schema: WctSchema[Any],
        output_schema: WctSchema[Any],
        message: Message,
    ) -> Message:
        """Analyze file content for sensitive information."""
        Analyser.validate_input_message(message, input_schema)

        # Extract content from the message's content structure
        payload_content = message.content

        # Get the actual text content from the text schema structure
        data_array = payload_content.get("data", [])
        if not data_array:
            text_content = ""
        else:
            # DESIGN DECISION: Combine all content pieces for holistic file analysis
            #
            # The file content analyser is designed to provide an overall security assessment
            # of the entire file, looking for patterns and calculating risk scores across
            # the complete document. This differs from analyzers that need granular tracking.
            #
            # Rationale for combining content:
            # - Patterns may span across multiple content pieces
            # - Risk scoring should consider the entire file context
            # - File-level security assessment is the primary goal
            # - Simpler analysis logic for overall file insights
            #
            # For new developers: If you need piece-by-piece analysis, consider creating
            # a separate analyser or see PersonalDataAnalyser for reference implementation.
            text_content = "\n".join(item.get("content", "") for item in data_array)

        # Get metadata from the guaranteed schema structure
        file_path = "unknown"  # fallback, will be overridden by first item's metadata
        encoding = payload_content.get("contentEncoding", "unknown")
        file_metadata = payload_content.get("metadata", {})

        # Extract source from first data item's metadata (guaranteed by schema)
        if data_array:
            first_item_metadata = data_array[0].get("metadata", {})
            file_path = first_item_metadata.get("source", "unknown")

        findings = []

        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(text_content)
            if matches:
                # Handle different regex patterns that may return tuples
                if pattern_name == "email":
                    # Email pattern returns strings directly
                    raw_samples = (
                        matches[:3]
                        if self.sensitivity_level in ["medium", "high"]
                        else []
                    )
                    samples = [
                        self._mask_sensitive_value(sample) for sample in raw_samples
                    ]
                elif pattern_name in ["potential_password", "api_key"]:
                    # These patterns return tuples, extract the actual value (second group)
                    raw_samples = (
                        [match[1] for match in matches[:3]]
                        if self.sensitivity_level in ["medium", "high"]
                        else []
                    )
                    samples = [
                        self._mask_sensitive_value(sample) for sample in raw_samples
                    ]
                else:
                    # Fallback for any other patterns
                    raw_samples = (
                        matches[:3]
                        if self.sensitivity_level in ["medium", "high"]
                        else []
                    )
                    samples = [
                        self._mask_sensitive_value(str(sample))
                        for sample in raw_samples
                    ]

                findings.append(
                    {
                        "type": pattern_name,
                        "count": len(matches),
                        "severity": self._get_severity(pattern_name),
                        "samples": samples,
                    }
                )

        risk_score = self._calculate_risk_score(findings)

        # Create result data
        result_data = {
            "source": file_path,
            "encoding": encoding,
            "file_metadata": file_metadata,
            "content_length": len(text_content),  # Use actual text content length
            "findings": findings,
            "risk_score": risk_score,
            "risk_level": self._get_risk_level(risk_score),
            "analysis_metadata": {
                "sensitivity_level": self.sensitivity_level,
                "patterns_checked": list(self.patterns.keys()),
            },
        }

        output_message = Message(
            id=f"Analysis results for {file_path}",
            content=result_data,
            schema=output_schema,
        )

        # Validate the output message against the output schema
        output_message.validate()

        self.logger.debug(
            f"FileContentAnalyser processed {file_path} with findings:\n{pformat(findings)}"
        )

        # Return new Message with analysis results
        return output_message

    def _get_severity(self, pattern_name: str) -> str:
        """Get severity level for different pattern types."""
        severity_map = {
            "email": "low",
            "potential_password": "high",
            "api_key": "critical",
        }
        return severity_map.get(pattern_name, "medium")

    def _calculate_risk_score(self, findings: list[dict[str, Any]]) -> int:
        """Calculate overall risk score based on findings."""
        score = 0
        severity_scores = {"low": 1, "medium": 3, "high": 7, "critical": 10}

        for finding in findings:
            severity = finding.get("severity", "medium")
            count = finding.get("count", 0)
            score += severity_scores.get(severity, 3) * count

        return min(score, 100)  # Cap at 100

    def _get_risk_level(self, risk_score: int) -> str:
        """Convert risk score to risk level."""
        if risk_score >= self.CRITICAL_RISK_THRESHOLD:
            return "critical"
        elif risk_score >= self.HIGH_RISK_THRESHOLD:
            return "high"
        elif risk_score >= self.MEDIUM_RISK_THRESHOLD:
            return "medium"

        return "low"

    def _mask_sensitive_value(self, value: str) -> str:
        """Mask sensitive values showing only the last 3 characters.

        Args:
            value: The sensitive value to mask

        Returns:
            Masked string with only last 3 characters visible
        """
        if len(value) <= self.MASK_VISIBLE_CHARS:
            # If value is 3 chars or less, mask all but the last char
            return "*" * (len(value) - 1) + value[-1] if value else ""
        else:
            # Mask all but the last 3 characters
            return (
                "*" * (len(value) - self.MASK_VISIBLE_CHARS)
                + value[-self.MASK_VISIBLE_CHARS :]
            )
