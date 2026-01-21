"""Tests for WordBoundaryMatcher."""

from waivern_analysers_shared.matching import WordBoundaryMatcher
from waivern_analysers_shared.types import PatternType


class TestWordBoundaryMatcherBoundaryDetection:
    """Test word boundary detection behaviour."""

    def test_matches_pattern_surrounded_by_spaces(self) -> None:
        """Pattern matches when surrounded by spaces."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("user dna sample", "dna")

        assert result.first_match is not None
        assert result.first_match.pattern == "dna"
        assert result.first_match.pattern_type == PatternType.WORD_BOUNDARY

    def test_matches_pattern_with_underscore_boundaries(self) -> None:
        """Pattern matches when surrounded by underscores."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("user_dna_sample", "dna")

        assert result.first_match is not None
        assert result.first_match.pattern == "dna"

    def test_matches_pattern_with_punctuation_boundaries(self) -> None:
        """Pattern matches when surrounded by punctuation."""
        matcher = WordBoundaryMatcher()

        assert matcher.find_match('"dna": "value"', "dna").first_match is not None
        assert (
            matcher.find_match("field-email-address", "email").first_match is not None
        )
        assert matcher.find_match("data.dna.sequence", "dna").first_match is not None

    def test_matches_pattern_at_start_of_string(self) -> None:
        """Pattern matches at the start of string."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("dna sequence here", "dna")

        assert result.first_match is not None
        assert result.first_match.start == 0

    def test_matches_pattern_at_end_of_string(self) -> None:
        """Pattern matches at the end of string."""
        matcher = WordBoundaryMatcher()

        content = "contains some dna"
        result = matcher.find_match(content, "dna")

        assert result.first_match is not None
        assert result.first_match.end == len(content)

    def test_no_match_when_embedded_in_alphanumeric(self) -> None:
        """Pattern does NOT match when embedded in alphanumeric sequence."""
        matcher = WordBoundaryMatcher()

        assert matcher.find_match("package", "age").first_match is None
        assert matcher.find_match("relationship", "ip").first_match is None
        assert matcher.find_match("message", "age").first_match is None
        assert matcher.find_match("storage", "age").first_match is None

    def test_no_match_in_base64_encoded_string(self) -> None:
        """Pattern does NOT match inside base64-like encoded strings."""
        matcher = WordBoundaryMatcher()

        base64_content = "EDYvj90wmildna5h31gzvsWw30apC1s"
        assert matcher.find_match(base64_content, "dna").first_match is None

        jwt_content = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.agedna123"
        assert matcher.find_match(jwt_content, "age").first_match is None


class TestWordBoundaryMatcherCaseSensitivity:
    """Test case-insensitive matching."""

    def test_matching_is_case_insensitive(self) -> None:
        """Matching is case insensitive."""
        matcher = WordBoundaryMatcher()

        assert matcher.find_match("user DNA sample", "dna").first_match is not None
        assert matcher.find_match("user dna sample", "DNA").first_match is not None
        assert matcher.find_match("USER EMAIL ADDRESS", "email").first_match is not None


class TestWordBoundaryMatcherEdgeCases:
    """Test edge case handling."""

    def test_returns_no_match_for_empty_content(self) -> None:
        """Empty content returns no match."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("", "dna")

        assert result.first_match is None
        assert result.match_count == 0

    def test_returns_no_match_for_empty_pattern(self) -> None:
        """Empty pattern returns no match."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("some content", "")

        assert result.first_match is None
        assert result.match_count == 0


class TestWordBoundaryMatcherReturnType:
    """Test correct PatternMatchResult return values."""

    def test_returns_correct_positions(self) -> None:
        """Returned positions correctly identify match locations."""
        matcher = WordBoundaryMatcher()
        content = "user dna sample"

        result = matcher.find_match(content, "dna")

        assert result.first_match is not None
        assert result.first_match.start == 5
        assert result.first_match.end == 8
        assert content[result.first_match.start : result.first_match.end] == "dna"

    def test_returns_pattern_match_with_word_boundary_type(self) -> None:
        """PatternMatch has pattern_type=WORD_BOUNDARY."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("test email here", "email")

        assert result.first_match is not None
        assert result.first_match.pattern_type == PatternType.WORD_BOUNDARY


class TestWordBoundaryMatcherMatchCount:
    """Test match count calculation."""

    def test_match_count_single_occurrence(self) -> None:
        """Single occurrence returns match_count=1."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("user email address", "email")

        assert result.match_count == 1

    def test_match_count_multiple_occurrences(self) -> None:
        """Multiple occurrences returns correct count."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("dna sample dna test dna", "dna")

        assert result.match_count == 3
        # First match position should still be the first occurrence
        assert result.first_match is not None
        assert result.first_match.start == 0

    def test_match_count_zero_when_no_match(self) -> None:
        """No matches returns match_count=0."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("package storage", "dna")

        assert result.match_count == 0
        assert result.first_match is None
