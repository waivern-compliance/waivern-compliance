"""Tests for RulePatternDispatcher."""

from waivern_core import DetectionRule

from waivern_analysers_shared.matching import RulePatternDispatcher
from waivern_analysers_shared.types import PatternType


class TestRulePatternDispatcherFindMatches:
    """Test find_matches method."""

    def test_routes_patterns_to_word_boundary_matcher(self) -> None:
        """rule.patterns are matched using WordBoundaryMatcher."""
        dispatcher = RulePatternDispatcher()
        rule = DetectionRule(
            name="email",
            description="Email detection",
            patterns=("email",),
        )

        matches = dispatcher.find_matches("user email address", rule)

        assert len(matches) == 1
        assert matches[0].pattern == "email"
        assert matches[0].pattern_type == PatternType.WORD_BOUNDARY

    def test_routes_value_patterns_to_regex_matcher(self) -> None:
        """rule.value_patterns are matched using RegexMatcher."""
        dispatcher = RulePatternDispatcher()
        rule = DetectionRule(
            name="email_value",
            description="Email value detection",
            value_patterns=(r"[a-z]+@[a-z]+\.[a-z]+",),
        )

        matches = dispatcher.find_matches("contact john@example.com today", rule)

        assert len(matches) == 1
        assert matches[0].pattern == r"[a-z]+@[a-z]+\.[a-z]+"
        assert matches[0].pattern_type == PatternType.REGEX

    def test_combines_matches_from_both_matchers(self) -> None:
        """Matches from both pattern types are returned together."""
        dispatcher = RulePatternDispatcher()
        rule = DetectionRule(
            name="email",
            description="Email detection",
            patterns=("email",),
            value_patterns=(r"[a-z]+@[a-z]+\.[a-z]+",),
        )

        matches = dispatcher.find_matches('{"email": "john@example.com"}', rule)

        assert len(matches) == 2
        pattern_types = {m.pattern_type for m in matches}
        assert pattern_types == {PatternType.WORD_BOUNDARY, PatternType.REGEX}

    def test_returns_empty_list_for_whitespace_only_content(self) -> None:
        """Whitespace-only content returns empty list."""
        dispatcher = RulePatternDispatcher()
        rule = DetectionRule(
            name="email",
            description="Email detection",
            patterns=("email",),
        )

        assert dispatcher.find_matches("   \n\t  ", rule) == []

    def test_returns_multiple_matches_for_multiple_patterns(self) -> None:
        """Each matching pattern produces one match."""
        dispatcher = RulePatternDispatcher()
        rule = DetectionRule(
            name="email",
            description="Email detection",
            patterns=("email", "address", "mailing"),
        )

        matches = dispatcher.find_matches("user email address here", rule)

        # "email" and "address" match, "mailing" doesn't appear
        assert len(matches) == 2
        matched_patterns = {m.pattern for m in matches}
        assert matched_patterns == {"email", "address"}
