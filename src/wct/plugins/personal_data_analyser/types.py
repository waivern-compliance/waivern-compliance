"""Data types for personal data analysis plugin."""

from dataclasses import dataclass
from typing import Any, Literal


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
    evidence: list[str] | None = None
    """Evidence found in the content that matches this finding."""
    metadata: dict[str, Any] | None = None
    """Additional metadata from the original data source."""
