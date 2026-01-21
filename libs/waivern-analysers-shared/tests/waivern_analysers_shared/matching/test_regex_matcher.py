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

        assert result.first_match is not None
        assert result.pattern == r"[a-z]+@[a-z]+\.[a-z]+"

    def test_matching_is_case_insensitive(self) -> None:
        """Matching is case insensitive."""
        matcher = RegexMatcher()

        assert (
            matcher.find_match(
                "EMAIL@EXAMPLE.COM", r"[a-z]+@[a-z]+\.[a-z]+"
            ).first_match
            is not None
        )
        assert (
            matcher.find_match(
                "Email@Example.Com", r"[a-z]+@[a-z]+\.[a-z]+"
            ).first_match
            is not None
        )


class TestRegexMatcherEdgeCases:
    """Test edge case handling."""

    def test_returns_no_match_for_empty_content(self) -> None:
        """Empty content returns no match."""
        matcher = RegexMatcher()

        result = matcher.find_match("", r"\d+")

        assert result.first_match is None
        assert result.match_count == 0

    def test_returns_no_match_for_empty_pattern(self) -> None:
        """Empty pattern returns no match."""
        matcher = RegexMatcher()

        result = matcher.find_match("some content", "")

        assert result.first_match is None
        assert result.match_count == 0


class TestRegexMatcherReturnType:
    """Test correct PatternMatchResult return values."""

    def test_returns_correct_positions(self) -> None:
        """Returned positions correctly identify match locations."""
        matcher = RegexMatcher()
        content = "call 555-1234 today"

        result = matcher.find_match(content, r"\d{3}-\d{4}")

        assert result.first_match is not None
        assert result.first_match.start == 5
        assert result.first_match.end == 13
        assert content[result.first_match.start : result.first_match.end] == "555-1234"

    def test_returns_pattern_match_with_regex_type(self) -> None:
        """PatternMatch has pattern_type=REGEX."""
        matcher = RegexMatcher()

        result = matcher.find_match("test 123", r"\d+")

        assert result.first_match is not None
        assert result.first_match.pattern_type == PatternType.REGEX


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
        assert result.first_match is not None
        assert result.first_match.start == 0

    def test_match_count_zero_when_no_match(self) -> None:
        """No matches returns match_count=0."""
        matcher = RegexMatcher()

        result = matcher.find_match("no numbers here", r"\d+")

        assert result.match_count == 0
        assert result.first_match is None
