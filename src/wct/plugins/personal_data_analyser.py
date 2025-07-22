"""Personal data analysis plugin for GDPR compliance."""

from dataclasses import dataclass
from typing import Any, Literal

from wct.plugins.base import Plugin
from wct.rulesets import get_ruleset


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
    def get_name(cls) -> str:
        """The name of the plugin."""
        return "personal_data_analyser"

    @classmethod
    def from_properties(cls, properties: dict[str, Any]):
        """Create plugin instance from properties."""
        ruleset_name = properties.get("ruleset", "personal_data")
        return cls(ruleset_name=ruleset_name)

    @property
    def patterns(self) -> dict[str, Any]:
        """Get the loaded patterns, loading them if necessary."""
        if self._patterns is None:
            self._patterns = get_ruleset(self.ruleset_name)
        return self._patterns

    def get_input_schema(self) -> str:
        """Expected input schema."""
        # TODO: Implement a proper schema definition - this should be a JSON schema or similar
        return "file_content"

    def get_output_schema(self) -> str:
        """Output schema produced."""
        # TODO: Implement a proper schema definition - this should be a JSON schema or similar
        return "personal_data_findings"

    def validate_input(self, data: dict[str, Any]) -> bool:
        """Validate input data format."""
        if "content" not in data:
            raise ValueError("Input data must contain 'content' field")
        return True

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process data to find personal data patterns."""
        content = data.get("content", "")
        file_path = data.get("file_path", "unknown")

        findings = self._analyze_content(content, file_path)

        return {
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
