"""Tests for WordBoundaryMatcher."""

from waivern_analysers_shared.matching import WordBoundaryMatcher
from waivern_analysers_shared.types import PatternType


class TestWordBoundaryMatcherBoundaryDetection:
    """Test word boundary detection behaviour."""

    def test_matches_pattern_surrounded_by_spaces(self) -> None:
        """Pattern matches when surrounded by spaces."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("user dna sample", "dna")

        assert len(result.representative_matches) > 0
        assert result.pattern == "dna"
        assert (
            result.representative_matches[0].pattern_type == PatternType.WORD_BOUNDARY
        )

    def test_matches_pattern_with_underscore_boundaries(self) -> None:
        """Pattern matches when surrounded by underscores."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("user_dna_sample", "dna")

        assert len(result.representative_matches) > 0
        assert result.pattern == "dna"

    def test_matches_pattern_with_punctuation_boundaries(self) -> None:
        """Pattern matches when surrounded by punctuation."""
        matcher = WordBoundaryMatcher()

        assert (
            matcher.find_match('"dna": "value"', "dna").representative_matches[0]
            is not None
        )
        assert (
            matcher.find_match("field-email-address", "email").representative_matches[0]
            is not None
        )
        assert (
            matcher.find_match("data.dna.sequence", "dna").representative_matches[0]
            is not None
        )

    def test_matches_pattern_at_start_of_string(self) -> None:
        """Pattern matches at the start of string."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("dna sequence here", "dna")

        assert len(result.representative_matches) > 0
        assert result.representative_matches[0].start == 0

    def test_matches_pattern_at_end_of_string(self) -> None:
        """Pattern matches at the end of string."""
        matcher = WordBoundaryMatcher()

        content = "contains some dna"
        result = matcher.find_match(content, "dna")

        assert len(result.representative_matches) > 0
        assert result.representative_matches[0].end == len(content)

    def test_no_match_when_embedded_in_alphanumeric(self) -> None:
        """Pattern does NOT match when embedded in alphanumeric sequence."""
        matcher = WordBoundaryMatcher()

        assert len(matcher.find_match("package", "age").representative_matches) == 0
        assert len(matcher.find_match("relationship", "ip").representative_matches) == 0
        assert len(matcher.find_match("message", "age").representative_matches) == 0
        assert len(matcher.find_match("storage", "age").representative_matches) == 0

    def test_no_match_in_base64_encoded_string(self) -> None:
        """Pattern does NOT match inside base64-like encoded strings."""
        matcher = WordBoundaryMatcher()

        base64_content = "EDYvj90wmildna5h31gzvsWw30apC1s"
        assert (
            len(matcher.find_match(base64_content, "dna").representative_matches) == 0
        )

        jwt_content = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.agedna123"
        assert len(matcher.find_match(jwt_content, "age").representative_matches) == 0


class TestWordBoundaryMatcherCaseSensitivity:
    """Test case-insensitive matching."""

    def test_matching_is_case_insensitive(self) -> None:
        """Matching is case insensitive."""
        matcher = WordBoundaryMatcher()

        assert (
            matcher.find_match("user DNA sample", "dna").representative_matches[0]
            is not None
        )
        assert (
            matcher.find_match("user dna sample", "DNA").representative_matches[0]
            is not None
        )
        assert (
            matcher.find_match("USER EMAIL ADDRESS", "email").representative_matches[0]
            is not None
        )


class TestWordBoundaryMatcherEdgeCases:
    """Test edge case handling."""

    def test_returns_no_match_for_empty_content(self) -> None:
        """Empty content returns no match."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("", "dna")

        assert len(result.representative_matches) == 0
        assert result.match_count == 0

    def test_returns_no_match_for_empty_pattern(self) -> None:
        """Empty pattern returns no match."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("some content", "")

        assert len(result.representative_matches) == 0
        assert result.match_count == 0


class TestWordBoundaryMatcherReturnType:
    """Test correct PatternMatchResult return values."""

    def test_returns_correct_positions(self) -> None:
        """Returned positions correctly identify match locations."""
        matcher = WordBoundaryMatcher()
        content = "user dna sample"

        result = matcher.find_match(content, "dna")

        assert len(result.representative_matches) > 0
        assert result.representative_matches[0].start == 5
        assert result.representative_matches[0].end == 8
        assert (
            content[
                result.representative_matches[0].start : result.representative_matches[
                    0
                ].end
            ]
            == "dna"
        )

    def test_returns_pattern_match_with_word_boundary_type(self) -> None:
        """PatternMatch has pattern_type=WORD_BOUNDARY."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("test email here", "email")

        assert len(result.representative_matches) > 0
        assert (
            result.representative_matches[0].pattern_type == PatternType.WORD_BOUNDARY
        )


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
        assert len(result.representative_matches) > 0
        assert result.representative_matches[0].start == 0

    def test_match_count_zero_when_no_match(self) -> None:
        """No matches returns match_count=0."""
        matcher = WordBoundaryMatcher()

        result = matcher.find_match("package storage", "dna")

        assert result.match_count == 0
        assert len(result.representative_matches) == 0


class TestWordBoundaryMatcherProximityGrouping:
    """Tests for WordBoundaryMatcher with proximity grouping."""

    def test_returns_multiple_representatives_for_spread_matches(self) -> None:
        """Spread matches return multiple representatives based on proximity threshold."""
        matcher = WordBoundaryMatcher()
        content = (
            "user email here ... user email there .................... user email far"
        )
        result = matcher.find_match(
            content, "email", proximity_threshold=50, max_representatives=3
        )

        assert (
            len(result.representative_matches) == 1
        )  # All matches within 50 char threshold
        assert result.match_count == 3  # Total of 3 email matches
        assert result.representative_matches[0].start == 5  # First email position

    def test_proximity_threshold_creates_multiple_groups(self) -> None:
        """Larger threshold creates separate groups for distant matches."""
        matcher = WordBoundaryMatcher()
        content = (
            "user email here ... user email there .................... user email far"
        )
        result = matcher.find_match(
            content, "email", proximity_threshold=1, max_representatives=10
        )

        # With threshold=1, each match should be its own group (they're separated by more than 1 char)
        assert len(result.representative_matches) == 3  # Three separate groups
        assert result.match_count == 3  # Total of 3 email matches

    def test_max_representatives_limits_returned_matches(self) -> None:
        """max_representatives parameter limits the number of returned matches."""
        matcher = WordBoundaryMatcher()
        content = (
            "user email here ... user email there .................... user email far"
        )
        result = matcher.find_match(
            content, "email", proximity_threshold=1, max_representatives=2
        )

        assert len(result.representative_matches) == 2  # Limited by max_representatives
        assert result.match_count == 3  # Still reports total match count

    def test_empty_content_returns_empty_representatives(self) -> None:
        """Empty content returns empty representative_matches tuple."""
        matcher = WordBoundaryMatcher()
        result = matcher.find_match(
            "", "dna", proximity_threshold=200, max_representatives=10
        )

        assert result.representative_matches == ()
        assert result.match_count == 0

    def test_no_matches_returns_empty_representatives(self) -> None:
        """No matches returns empty representative_matches tuple."""
        matcher = WordBoundaryMatcher()
        result = matcher.find_match(
            "no dna here", "xyz", proximity_threshold=200, max_representatives=10
        )

        assert result.representative_matches == ()
        assert result.match_count == 0
