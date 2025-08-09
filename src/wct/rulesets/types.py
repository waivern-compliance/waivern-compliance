"""Simple types for structured rulesets."""

from dataclasses import dataclass, field
from typing import Any, TypedDict


class RuleData(TypedDict):
    """Type definition for rule pattern data in PATTERNS dictionaries."""

    description: str
    patterns: tuple[str, ...]
    risk_level: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class Rule:
    """Immutable structured rule for pattern matching.

    A rule represents a category of patterns to match, with associated metadata.
    All rules have a risk_level as this is universal across rulesets.
    The metadata property can hold any additional ruleset-specific information.

    This provides a lightweight immutable structure while maintaining flexibility.
    """

    name: str
    description: str
    patterns: tuple[str, ...]
    risk_level: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate that patterns contains at least one pattern."""
        if not self.patterns:
            raise ValueError("Rule must contain at least one pattern")
