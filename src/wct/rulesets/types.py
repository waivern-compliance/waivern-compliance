"""Simple types for structured rulesets."""

from dataclasses import dataclass, field
from typing import Any, TypedDict


class ComplianceData(TypedDict):
    """Type definition for compliance information."""

    regulation: str
    relevance: str


# Make RuleData dataclass a Pydantic model (check the RuleData usage to see whether the metadata has mandatory fields)
class RuleData(TypedDict):
    """Type definition for rule pattern data in PATTERNS dictionaries."""

    description: str
    patterns: tuple[str, ...]
    risk_level: str
    compliance: list[ComplianceData]
    metadata: dict[str, Any]


# Make Rule dataclass a Pydantic model (check the Rule usage to see whether the metadata has mandatory fields)
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
    compliance: list[ComplianceData] = field(default_factory=list)
    # TODO: Make metadata a Pydantic model (check the metadata usage to see whether the metadata has mandatory fields)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate that patterns contains at least one pattern."""
        if not self.patterns:
            raise ValueError("Rule must contain at least one pattern")
