"""Types for pattern matching analysis."""

from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field


class PatternType(Enum):
    """Type of pattern matching strategy.

    WORD_BOUNDARY: Matches patterns at word boundaries only, avoiding false
        positives in compound words or encoded strings (e.g., base64).

    REGEX: Full regex matching for detecting actual data values like
        email addresses, phone numbers, etc.
    """

    WORD_BOUNDARY = "word_boundary"
    REGEX = "regex"


@dataclass(frozen=True, slots=True)
class PatternMatch:
    """A single pattern match with position information.

    Immutable value object representing where a pattern matched in content.
    Used to track matches from both word-boundary and regex patterns with
    their exact positions for evidence extraction.

    Note: The pattern itself is not stored here - it belongs to the parent
    PatternMatchResult which represents the search operation. This avoids
    redundant data storage.

    Attributes:
        pattern_type: Whether this was word-boundary or regex matching
        start: Start position (inclusive) in the content
        end: End position (exclusive) in the content

    """

    pattern_type: PatternType
    start: int
    end: int

    @property
    def matched_text_length(self) -> int:
        """Length of the actual matched text."""
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class PatternMatchResult:
    """Result of searching for a pattern in content.

    Contains representative matches for evidence extraction (one per
    location cluster) and the total match count for reporting.

    Attributes:
        pattern: The pattern that was searched for
        representative_matches: Representative matches (one per proximity cluster)
        match_count: Total number of times the pattern matched

    """

    pattern: str
    representative_matches: tuple[PatternMatch, ...]
    match_count: int


class EvidenceContextSize(str, Enum):
    """Evidence context size options.

    Each size determines the number of characters to include before and after
    a pattern match when extracting evidence snippets.
    """

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    FULL = "full"

    @property
    def char_count(self) -> int | None:
        """Characters to include on each side of a match (None = full content)."""
        match self:
            case EvidenceContextSize.SMALL:
                return 50
            case EvidenceContextSize.MEDIUM:
                return 100
            case EvidenceContextSize.LARGE:
                return 200
            case EvidenceContextSize.FULL:
                return None


class PatternMatchingConfig(BaseModel):
    """Strongly typed configuration for pattern matching analysis."""

    ruleset: str = Field(
        description="Ruleset URI in format provider/name/version (e.g., 'local/personal_data/1.0.0')"
    )

    evidence_context_size: EvidenceContextSize = Field(
        default=EvidenceContextSize.MEDIUM,
        description="Context size for evidence extraction",
    )

    maximum_evidence_count: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum number of evidence items to collect per finding",
    )

    evidence_proximity_threshold: int = Field(
        default=200,
        ge=50,
        le=1000,
        description="Characters between matches to consider them distinct locations",
    )
