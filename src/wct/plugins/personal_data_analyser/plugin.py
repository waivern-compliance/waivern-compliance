"""Personal data analysis plugin for GDPR compliance."""

from dataclasses import dataclass
from typing import Any, Literal

from typing_extensions import Self, override

from wct.plugins.base import Plugin
from wct.rulesets import get_ruleset
from wct.schema import WctSchema
from wct.message import Message

SUPPORTED_INPUT_SCHEMAS = [
    WctSchema(name="text", type=dict[str, Any]),
    WctSchema(name="file_content", type=dict[str, Any]),
]

SUPPORTED_OUTPUT_SCHEMAS = [
    WctSchema(name="personal_data_findings", type=dict[str, Any]),
]

DEFAULT_INPUT_SCHEMA = SUPPORTED_INPUT_SCHEMAS[0]
DEFAULT_OUTPUT_SCHEMA = SUPPORTED_OUTPUT_SCHEMAS[0]


@dataclass(frozen=True, slots=True)
class PersonalDataPattern:
    """A pattern for a personal data type."""

    name: str
    patterns: list[str]
    risk_level: Literal["low", "medium", "high"]
    is_special_category: bool


@dataclass(frozen=True, slots=True)
class PersonalDataFinding:
    """A finding of a personal data."""

    type: str
    risk_level: str
    special_category: str
    matched_pattern: str
    source: str | None


class PersonalDataAnalyser(Plugin):
    """Plugin for analyzing personal data patterns for GDPR compliance."""

    def __init__(self, ruleset_name: str = "personal_data"):
        """Initialize the analyser with specified ruleset.

        Args:
            ruleset_name: Name of the ruleset to use for analysis
        """
        self.ruleset_name = ruleset_name
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
        return cls(ruleset_name=ruleset_name)

    @property
    def patterns(self) -> dict[str, Any]:
        """Get the loaded patterns, loading them if necessary."""
        if self._patterns is None:
            self._patterns = get_ruleset(self.ruleset_name)
        return self._patterns

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

        # For personal data analysis, we expect text content
        # The content might be a direct string or wrapped in schema structure
        if isinstance(data, dict):
            if "content" in data and isinstance(data["content"], list):
                # Handle text schema format from file connector
                content_array = data["content"]
                content = "\n".join(item.get("text", "") for item in content_array)
                source = data.get("source", "unknown")
            else:
                # Handle direct content
                content = data.get("content", "")
                source = data.get("source", "unknown")
        else:
            # Handle direct string content
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

        # Return new Message with analysis results
        return output_message

    def _analyze_content(self, content: str, source: str) -> list[PersonalDataFinding]:
        """Analyze content for personal data patterns."""
        findings = []

        for category_name, category_data in self.patterns.items():
            for pattern in category_data["patterns"]:
                if pattern.lower() in content.lower():
                    finding = PersonalDataFinding(
                        type=category_name,
                        risk_level=category_data["risk_level"],
                        special_category=category_data["special_category"],
                        matched_pattern=pattern,
                        source=source,
                    )
                    findings.append(finding)

        return findings
