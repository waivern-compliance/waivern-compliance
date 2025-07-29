"""Personal data analysis plugin for GDPR compliance."""

from dataclasses import dataclass
from typing import Any, Literal
from pprint import pformat

from typing_extensions import Self, override

from wct.plugins.base import Plugin
from wct.rulesets import get_ruleset
from wct.schema import WctSchema
from wct.message import Message

SUPPORTED_INPUT_SCHEMAS = [
    WctSchema(name="text", type=dict[str, Any]),
]

SUPPORTED_OUTPUT_SCHEMAS = [
    WctSchema(name="personal_data_analysis_findings", type=dict[str, Any]),
]

DEFAULT_INPUT_SCHEMA = SUPPORTED_INPUT_SCHEMAS[0]
DEFAULT_OUTPUT_SCHEMA = SUPPORTED_OUTPUT_SCHEMAS[0]


@dataclass(frozen=True, slots=True)
class PersonalDataPattern:
    """A pattern for a personal data type."""

    name: str
    patterns: list[str]
    risk_level: Literal["low", "medium", "high"]
    is_special_category: bool | None = None
    """Indicates if this pattern is a special category under GDPR."""


@dataclass(frozen=True, slots=True)
class PersonalDataFinding:
    """A finding of a personal data."""

    type: str
    risk_level: str
    special_category: str | None
    """Indicates if this finding is a special category under GDPR."""
    matched_pattern: str
    source: str | None
    evidence: list[str] | None = None
    """Evidence found in the content that matches this finding."""


class PersonalDataAnalyser(Plugin):
    """Plugin for analyzing personal data patterns for GDPR compliance."""

    def __init__(
        self, ruleset_name: str = "personal_data", evidence_context_size: str = "small"
    ):
        """Initialize the analyser with specified ruleset and evidence context size.

        Args:
            ruleset_name: Name of the ruleset to use for analysis
            evidence_context_size: Size of context around evidence matches
                                  ('small': 50 chars, 'medium': 100 chars, 'large': 200 chars)
        """
        super().__init__()  # Initialize logger from base class
        self.ruleset_name = ruleset_name
        self.evidence_context_size = evidence_context_size
        self._patterns = None

    @classmethod
    @override
    def get_name(cls) -> str:
        """The name of the plugin."""
        return "personal_data_analyser"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create plugin instance from properties."""
        ruleset_name = properties.get("ruleset", "personal_data")
        evidence_context_size = properties.get("evidence_context_size", "small")
        return cls(
            ruleset_name=ruleset_name, evidence_context_size=evidence_context_size
        )

    @property
    def patterns(self) -> dict[str, Any]:
        """Get the loaded patterns, loading them if necessary."""
        if self._patterns is None:
            self._patterns = get_ruleset(self.ruleset_name)
        return self._patterns

    def _get_context_size(self) -> int:
        """Get the context size in characters based on the configured level.

        Returns:
            Number of characters to include before and after each match
        """
        size_mapping = {"small": 50, "medium": 100, "large": 200}
        return size_mapping.get(self.evidence_context_size.lower(), 50)

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[WctSchema[Any]]:
        """Return the input schemas supported by this plugin."""
        return SUPPORTED_INPUT_SCHEMAS

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[WctSchema[Any]]:
        """Return the output schemas supported by this plugin."""
        return SUPPORTED_OUTPUT_SCHEMAS

    @override
    def process(
        self,
        input_schema: WctSchema[Any],
        output_schema: WctSchema[Any],
        message: Message,
    ) -> Message:
        """Process data to find personal data patterns."""

        Plugin.validate_input_message(message, input_schema)

        # Extract content from message
        data = message.content

        # Extract and process content based on input format
        # Personal data analysis requires granular tracking for compliance purposes
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], list):
                # DESIGN DECISION: Analyze each data array item independently
                #
                # For personal data compliance (GDPR, CCPA), we need granular tracking
                # of where specific personal data types are found. This enables:
                # - Precise data mapping for compliance documentation
                # - Granular consent management
                # - Targeted data deletion/modification
                # - Detailed audit trails for regulatory requirements
                #
                # Each item in the data array represents a distinct content piece
                # that should be analyzed and tracked separately for compliance.

                data_array = data["data"]
                source = data.get("source", "unknown")
                all_findings = []

                for item in data_array:
                    content = item.get("content", "")
                    item_metadata = item.get("metadata", {})
                    # Use item-specific source for granular tracking
                    item_source = item_metadata.get("source", source)

                    # Analyze each content piece independently for compliance tracking
                    item_findings = self._analyze_content(content, item_source)
                    all_findings.extend(item_findings)

                findings = all_findings
            else:
                # Handle direct content format (legacy or simplified input)
                content = data.get("content", "")
                source = data.get("source", "unknown")
                findings = self._analyze_content(content, source)
        else:
            # Handle direct string content (fallback case)
            content = str(data)
            source = "unknown"
            findings = self._analyze_content(content, source)

        # Create result data
        result_data = {
            "findings": [
                {
                    "type": finding.type,
                    "risk_level": finding.risk_level,
                    "special_category": finding.special_category,
                    "matched_pattern": finding.matched_pattern,
                    "source": finding.source,
                    "evidence": finding.evidence,
                }
                for finding in findings
            ],
            "summary": {
                "total_findings": len(findings),
                "high_risk_count": len([f for f in findings if f.risk_level == "high"]),
                "special_category_count": len(
                    [f for f in findings if f.special_category == "Y"]
                ),
            },
        }

        output_message = Message(
            id=f"Personal data analysis for {source}",
            content=result_data,
            schema=output_schema,
        )

        # Validate the output message against the output schema
        output_message.validate()

        self.logger.debug(
            f"PersonalDataAnalyser processed {source} with findings:\n{pformat(findings)}"
        )

        # Return new Message with analysis results
        return output_message

    def _analyze_content(self, content: str, source: str) -> list[PersonalDataFinding]:
        """Analyze content for personal data patterns."""
        findings = []

        for category_name, category_data in self.patterns.items():
            for pattern in category_data["patterns"]:
                if pattern.lower() in content.lower():
                    # Extract evidence - find all occurrences of the pattern in the content
                    evidence_matches = self._extract_evidence(content, pattern)

                    finding = PersonalDataFinding(
                        type=category_name,
                        risk_level=category_data["risk_level"],
                        special_category=category_data["special_category"],
                        matched_pattern=pattern,
                        source=source,
                        evidence=evidence_matches,
                    )
                    findings.append(finding)

        return findings

    def _extract_evidence(self, content: str, pattern: str) -> list[str]:
        """Extract evidence snippets where the pattern was found.

        Args:
            content: The full content to search in
            pattern: The pattern that was matched

        Returns:
            List of evidence snippets showing context around matches
        """
        evidence_list = []
        content_lower = content.lower()
        pattern_lower = pattern.lower()

        # Find all occurrences of the pattern
        start_pos = 0
        while True:
            match_pos = content_lower.find(pattern_lower, start_pos)
            if match_pos == -1:
                break

            # Extract context around the match (configurable characters before and after)
            context_size = self._get_context_size()
            context_start = max(0, match_pos - context_size)
            context_end = min(len(content), match_pos + len(pattern) + context_size)

            # Extract the evidence with context
            evidence_snippet = content[context_start:context_end].strip()

            # Add ellipsis if we truncated the context
            if context_start > 0:
                evidence_snippet = "..." + evidence_snippet
            if context_end < len(content):
                evidence_snippet = evidence_snippet + "..."

            evidence_list.append(evidence_snippet)

            # Move past this match for next search
            start_pos = match_pos + 1

            # Limit to maximum 3 evidence snippets to avoid overwhelming output
            if len(evidence_list) >= 3:
                break

        return evidence_list
