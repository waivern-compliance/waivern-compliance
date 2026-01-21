"""Tests for WordBoundaryMatcher."""

from waivern_analysers_shared.matching import WordBoundaryMatcher
from waivern_analysers_shared.types import PatternType


class TestWordBoundaryMatcherBoundaryDetection:
    """Test word boundary detection behaviour."""

    def test_matches_pattern_surrounded_by_spaces(self) -> None:
        """Pattern matches when surrounded by spaces."""
        matcher = WordBoundaryMatcher()

        match = matcher.find_match("user dna sample", "dna")

        assert match is not None
        assert match.pattern == "dna"
        assert match.pattern_type == PatternType.WORD_BOUNDARY

    def test_matches_pattern_with_underscore_boundaries(self) -> None:
        """Pattern matches when surrounded by underscores."""
        matcher = WordBoundaryMatcher()

        match = matcher.find_match("user_dna_sample", "dna")

        assert match is not None
        assert match.pattern == "dna"

    def test_matches_pattern_with_punctuation_boundaries(self) -> None:
        """Pattern matches when surrounded by punctuation."""
        matcher = WordBoundaryMatcher()

        assert matcher.find_match('"dna": "value"', "dna") is not None
        assert matcher.find_match("field-email-address", "email") is not None
        assert matcher.find_match("data.dna.sequence", "dna") is not None

    def test_matches_pattern_at_start_of_string(self) -> None:
        """Pattern matches at the start of string."""
        matcher = WordBoundaryMatcher()

        match = matcher.find_match("dna sequence here", "dna")

        assert match is not None
        assert match.start == 0

    def test_matches_pattern_at_end_of_string(self) -> None:
        """Pattern matches at the end of string."""
        matcher = WordBoundaryMatcher()

        content = "contains some dna"
        match = matcher.find_match(content, "dna")

        assert match is not None
        assert match.end == len(content)

    def test_no_match_when_embedded_in_alphanumeric(self) -> None:
        """Pattern does NOT match when embedded in alphanumeric sequence."""
        matcher = WordBoundaryMatcher()

        assert matcher.find_match("package", "age") is None
        assert matcher.find_match("relationship", "ip") is None
        assert matcher.find_match("message", "age") is None
        assert matcher.find_match("storage", "age") is None

    def test_no_match_in_base64_encoded_string(self) -> None:
        """Pattern does NOT match inside base64-like encoded strings."""
        matcher = WordBoundaryMatcher()

        base64_content = "EDYvj90wmildna5h31gzvsWw30apC1s"
        assert matcher.find_match(base64_content, "dna") is None

        jwt_content = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.agedna123"
        assert matcher.find_match(jwt_content, "age") is None


class TestWordBoundaryMatcherCaseSensitivity:
    """Test case-insensitive matching."""

    def test_matching_is_case_insensitive(self) -> None:
        """Matching is case insensitive."""
        matcher = WordBoundaryMatcher()

        assert matcher.find_match("user DNA sample", "dna") is not None
        assert matcher.find_match("user dna sample", "DNA") is not None
        assert matcher.find_match("USER EMAIL ADDRESS", "email") is not None


class TestWordBoundaryMatcherEdgeCases:
    """Test edge case handling."""

    def test_returns_none_for_empty_content(self) -> None:
        """Empty content returns None."""
        matcher = WordBoundaryMatcher()

        assert matcher.find_match("", "dna") is None

    def test_returns_none_for_empty_pattern(self) -> None:
        """Empty pattern returns None."""
        matcher = WordBoundaryMatcher()

        assert matcher.find_match("some content", "") is None


class TestWordBoundaryMatcherReturnType:
    """Test correct PatternMatch return values."""

    def test_returns_correct_positions(self) -> None:
        """Returned positions correctly identify match locations."""
        matcher = WordBoundaryMatcher()
        content = "user dna sample"

        match = matcher.find_match(content, "dna")

        assert match is not None
        assert match.start == 5
        assert match.end == 8
        assert content[match.start : match.end] == "dna"

    def test_returns_pattern_match_with_word_boundary_type(self) -> None:
        """PatternMatch has pattern_type=WORD_BOUNDARY."""
        matcher = WordBoundaryMatcher()

        match = matcher.find_match("test email here", "email")

        assert match is not None
        assert match.pattern_type == PatternType.WORD_BOUNDARY
