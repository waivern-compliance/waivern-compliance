"""Simple types for structured rulesets."""

from typing import Any, TypedDict


class RuleData(TypedDict):
    """Type definition for rule pattern data in PATTERNS dictionaries."""

    description: str
    patterns: list[str]
    risk_level: str
    metadata: dict[str, Any]


class Rule:
    """Simple structured rule for pattern matching.

    A rule represents a category of patterns to match, with associated metadata.
    All rules have a risk_level as this is universal across rulesets.
    The metadata property can hold any additional ruleset-specific information.

    This provides a lightweight structure while maintaining flexibility.
    """

    def __init__(
        self,
        name: str,
        description: str,
        patterns: list[str],
        risk_level: str,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize a rule with patterns, risk level, and metadata.

        Args:
            name: Unique name/identifier for this rule
            description: Human-readable description of what this rule detects
            patterns: List of string patterns to match against
            risk_level: Risk level for this rule (e.g., "low", "medium", "high")
            metadata: Optional dictionary of additional ruleset-specific metadata
        """
        self.name = name
        self.description = description
        self.patterns = patterns
        self.risk_level = risk_level
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"Rule(name='{self.name}', risk_level='{self.risk_level}', patterns={len(self.patterns)}, metadata={self.metadata})"
