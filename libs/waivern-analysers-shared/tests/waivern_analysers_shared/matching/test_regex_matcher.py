"""Tests for RegexMatcher."""

from waivern_analysers_shared.matching import RegexMatcher
from waivern_analysers_shared.types import PatternType


class TestRegexMatcherPatternMatching:
    """Test regex pattern matching behaviour."""

    def test_matches_pattern_as_regex(self) -> None:
        """Pattern is used as regex without escaping."""
        matcher = RegexMatcher()

        # Regex with character class and quantifier
        result = matcher.find_match("email@example.com", r"[a-z]+@[a-z]+\.[a-z]+")

        assert len(result.representative_matches) > 0
        assert result.pattern == r"[a-z]+@[a-z]+\.[a-z]+"

    def test_matching_is_case_insensitive(self) -> None:
        """Matching is case insensitive."""
        matcher = RegexMatcher()

        assert (
            matcher.find_match(
                "EMAIL@EXAMPLE.COM", r"[a-z]+@[a-z]+\.[a-z]+"
            ).representative_matches[0]
            is not None
        )
        assert (
            matcher.find_match(
                "Email@Example.Com", r"[a-z]+@[a-z]+\.[a-z]+"
            ).representative_matches[0]
            is not None
        )


class TestRegexMatcherEdgeCases:
    """Test edge case handling."""

    def test_returns_no_match_for_empty_content(self) -> None:
        """Empty content returns no match."""
        matcher = RegexMatcher()

        result = matcher.find_match("", r"\d+")

        assert len(result.representative_matches) == 0
        assert result.match_count == 0

    def test_returns_no_match_for_empty_pattern(self) -> None:
        """Empty pattern returns no match."""
        matcher = RegexMatcher()

        result = matcher.find_match("some content", "")

        assert len(result.representative_matches) == 0
        assert result.match_count == 0


class TestRegexMatcherReturnType:
    """Test correct PatternMatchResult return values."""

    def test_returns_correct_positions(self) -> None:
        """Returned positions correctly identify match locations."""
        matcher = RegexMatcher()
        content = "call 555-1234 today"

        result = matcher.find_match(content, r"\d{3}-\d{4}")

        assert len(result.representative_matches) > 0
        assert result.representative_matches[0].start == 5
        assert result.representative_matches[0].end == 13
        assert (
            content[
                result.representative_matches[0].start : result.representative_matches[
                    0
                ].end
            ]
            == "555-1234"
        )

    def test_returns_pattern_match_with_regex_type(self) -> None:
        """PatternMatch has pattern_type=REGEX."""
        matcher = RegexMatcher()

        result = matcher.find_match("test 123", r"\d+")

        assert len(result.representative_matches) > 0
        assert result.representative_matches[0].pattern_type == PatternType.REGEX


class TestRegexMatcherMatchCount:
    """Test match count calculation."""

    def test_match_count_single_occurrence(self) -> None:
        """Single occurrence returns match_count=1."""
        matcher = RegexMatcher()

        result = matcher.find_match("test@example.com", r"[a-z]+@[a-z]+\.[a-z]+")

        assert result.match_count == 1

    def test_match_count_multiple_occurrences(self) -> None:
        """Multiple occurrences returns correct count."""
        matcher = RegexMatcher()

        result = matcher.find_match("12 and 34 and 56", r"\d+")

        assert result.match_count == 3
        # First match position should still be the first occurrence
        assert len(result.representative_matches) > 0
        assert result.representative_matches[0].start == 0

    def test_match_count_zero_when_no_match(self) -> None:
        """No matches returns match_count=0."""
        matcher = RegexMatcher()

        result = matcher.find_match("no numbers here", r"\d+")

        assert result.match_count == 0
        assert len(result.representative_matches) == 0


class TestRegexMatcherProximityGrouping:
    """Tests for RegexMatcher with proximity grouping."""

    def test_returns_multiple_representatives_for_spread_matches(self) -> None:
        """Spread matches return multiple representatives based on proximity threshold."""
        matcher = RegexMatcher()
        content = (
            "email: a@b.com ... email: c@d.com .................... email: e@f.com"
        )
        result = matcher.find_match(
            content, r"\w+@\w+", proximity_threshold=50, max_representatives=3
        )

        assert (
            len(result.representative_matches) == 1
        )  # All matches within 50 char threshold
        assert result.match_count == 3  # Total of 3 email matches
        assert result.representative_matches[0].start == 7  # First email position

    def test_proximity_threshold_creates_multiple_groups(self) -> None:
        """Larger threshold creates separate groups for distant matches."""
        matcher = RegexMatcher()
        content = (
            "email: a@b.com ... email: c@d.com .................... email: e@f.com"
        )
        result = matcher.find_match(
            content, r"\w+@\w+", proximity_threshold=1, max_representatives=10
        )

        # With threshold=1, each match should be its own group (they're separated by more than 1 char)
        assert len(result.representative_matches) == 3  # Three separate groups
        assert result.match_count == 3  # Total of 3 email matches

    def test_max_representatives_limits_returned_matches(self) -> None:
        """max_representatives parameter limits the number of returned matches."""
        matcher = RegexMatcher()
        content = (
            "email: a@b.com ... email: c@d.com .................... email: e@f.com"
        )
        result = matcher.find_match(
            content, r"\w+@\w+", proximity_threshold=1, max_representatives=2
        )

        assert len(result.representative_matches) == 2  # Limited by max_representatives
        assert result.match_count == 3  # Still reports total match count

    def test_empty_content_returns_empty_representatives(self) -> None:
        """Empty content returns empty representative_matches tuple."""
        matcher = RegexMatcher()
        result = matcher.find_match(
            "", r"\d+", proximity_threshold=200, max_representatives=10
        )

        assert result.representative_matches == ()
        assert result.match_count == 0

    def test_no_matches_returns_empty_representatives(self) -> None:
        """No matches returns empty representative_matches tuple."""
        matcher = RegexMatcher()
        result = matcher.find_match(
            "no numbers here", r"\d+", proximity_threshold=200, max_representatives=10
        )

        assert result.representative_matches == ()
        assert result.match_count == 0
