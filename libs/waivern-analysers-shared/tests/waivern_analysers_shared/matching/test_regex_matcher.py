"""Tests for RegexMatcher."""

from waivern_analysers_shared.matching import RegexMatcher
from waivern_analysers_shared.types import PatternType


class TestRegexMatcherPatternMatching:
    """Test regex pattern matching behaviour."""

    def test_matches_pattern_as_regex(self) -> None:
        """Pattern is used as regex without escaping."""
        matcher = RegexMatcher()

        # Regex with character class and quantifier
        match = matcher.find_match("email@example.com", r"[a-z]+@[a-z]+\.[a-z]+")

        assert match is not None
        assert match.pattern == r"[a-z]+@[a-z]+\.[a-z]+"

    def test_matching_is_case_insensitive(self) -> None:
        """Matching is case insensitive."""
        matcher = RegexMatcher()

        assert (
            matcher.find_match("EMAIL@EXAMPLE.COM", r"[a-z]+@[a-z]+\.[a-z]+")
            is not None
        )
        assert (
            matcher.find_match("Email@Example.Com", r"[a-z]+@[a-z]+\.[a-z]+")
            is not None
        )


class TestRegexMatcherEdgeCases:
    """Test edge case handling."""

    def test_returns_none_for_empty_content(self) -> None:
        """Empty content returns None."""
        matcher = RegexMatcher()

        assert matcher.find_match("", r"\d+") is None

    def test_returns_none_for_empty_pattern(self) -> None:
        """Empty pattern returns None."""
        matcher = RegexMatcher()

        assert matcher.find_match("some content", "") is None


class TestRegexMatcherReturnType:
    """Test correct PatternMatch return values."""

    def test_returns_correct_positions(self) -> None:
        """Returned positions correctly identify match locations."""
        matcher = RegexMatcher()
        content = "call 555-1234 today"

        match = matcher.find_match(content, r"\d{3}-\d{4}")

        assert match is not None
        assert match.start == 5
        assert match.end == 13
        assert content[match.start : match.end] == "555-1234"

    def test_returns_pattern_match_with_regex_type(self) -> None:
        """PatternMatch has pattern_type=REGEX."""
        matcher = RegexMatcher()

        match = matcher.find_match("test 123", r"\d+")

        assert match is not None
        assert match.pattern_type == PatternType.REGEX
