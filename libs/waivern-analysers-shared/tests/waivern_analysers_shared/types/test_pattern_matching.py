"""Tests for pattern matching types."""

import pytest
from pydantic import ValidationError

from waivern_analysers_shared.types import (
    EvidenceContextSize,
    PatternMatch,
    PatternMatchingConfig,
    PatternMatchResult,
    PatternType,
)


class TestPatternMatchingConfig:
    """Tests for PatternMatchingConfig business rules."""

    def test_default_evidence_proximity_threshold(self) -> None:
        """Default proximity threshold is 200 characters."""
        config = PatternMatchingConfig(
            ruleset="local/test/1.0.0",
            evidence_context_size=EvidenceContextSize.MEDIUM,
            maximum_evidence_count=3,
        )
        assert config.evidence_proximity_threshold == 200

    def test_evidence_proximity_threshold_validation(self) -> None:
        """Proximity threshold must be between 50 and 1000 characters."""
        # Valid values work
        for threshold in [50, 200, 500, 1000]:
            config = PatternMatchingConfig(
                ruleset="local/test/1.0.0",
                evidence_context_size=EvidenceContextSize.MEDIUM,
                evidence_proximity_threshold=threshold,
            )
            assert config.evidence_proximity_threshold == threshold

        # Invalid values rejected
        with pytest.raises(ValidationError, match="evidence_proximity_threshold"):
            PatternMatchingConfig(
                ruleset="local/test/1.0.0",
                evidence_context_size=EvidenceContextSize.MEDIUM,
                evidence_proximity_threshold=49,  # Too low
            )

        with pytest.raises(ValidationError, match="evidence_proximity_threshold"):
            PatternMatchingConfig(
                ruleset="local/test/1.0.0",
                evidence_context_size=EvidenceContextSize.MEDIUM,
                evidence_proximity_threshold=1001,  # Too high
            )


class TestPatternMatchResult:
    """Tests for PatternMatchResult dataclass."""

    def test_with_representative_matches(self) -> None:
        """PatternMatchResult stores representative matches for evidence extraction."""
        match1 = PatternMatch(pattern_type=PatternType.REGEX, start=10, end=20)
        match2 = PatternMatch(pattern_type=PatternType.REGEX, start=100, end=110)
        result = PatternMatchResult(
            pattern="test_pattern",
            representative_matches=(match1, match2),
            match_count=5,
        )

        assert result.pattern == "test_pattern"
        assert len(result.representative_matches) == 2
        assert result.representative_matches[0].start == 10
        assert result.representative_matches[1].start == 100
        assert result.match_count == 5

    def test_empty_representatives(self) -> None:
        """PatternMatchResult with no matches has empty tuple."""
        result = PatternMatchResult(
            pattern="no_match", representative_matches=(), match_count=0
        )

        assert result.pattern == "no_match"
        assert len(result.representative_matches) == 0
        assert result.match_count == 0


class TestPatternMatch:
    """Tests for PatternMatch dataclass."""

    def test_matched_text_length_property(self) -> None:
        """matched_text_length returns end - start."""
        match = PatternMatch(pattern_type=PatternType.WORD_BOUNDARY, start=10, end=25)
        assert match.matched_text_length == 15

    def test_single_character_match(self) -> None:
        """Single character match has length 1."""
        match = PatternMatch(pattern_type=PatternType.REGEX, start=5, end=6)
        assert match.matched_text_length == 1


class TestEvidenceContextSize:
    """Tests for EvidenceContextSize enum."""

    def test_char_count_values(self) -> None:
        """Each context size has expected char_count."""
        assert EvidenceContextSize.SMALL.char_count == 50
        assert EvidenceContextSize.MEDIUM.char_count == 100
        assert EvidenceContextSize.LARGE.char_count == 200
        assert EvidenceContextSize.FULL.char_count is None

    def test_string_coercion_for_yaml_compatibility(self) -> None:
        """EvidenceContextSize can be created from string values (YAML compatibility)."""
        # This works because EvidenceContextSize inherits from str
        assert EvidenceContextSize("small") == EvidenceContextSize.SMALL
        assert EvidenceContextSize("medium") == EvidenceContextSize.MEDIUM
        assert EvidenceContextSize("large") == EvidenceContextSize.LARGE
        assert EvidenceContextSize("full") == EvidenceContextSize.FULL
