"""Rule pattern dispatcher."""

from waivern_core import DetectionRule

from waivern_analysers_shared.matching.regex import RegexMatcher
from waivern_analysers_shared.matching.word_boundary import WordBoundaryMatcher
from waivern_analysers_shared.types import PatternMatch


class RulePatternDispatcher:
    """Routes DetectionRule patterns to appropriate matchers.

    - rule.patterns → WordBoundaryMatcher
    - rule.value_patterns → RegexMatcher
    """

    def __init__(self) -> None:
        """Initialise dispatcher with word boundary and regex matchers."""
        self._word_boundary = WordBoundaryMatcher()
        self._regex = RegexMatcher()

    def find_matches(self, content: str, rule: DetectionRule) -> list[PatternMatch]:
        """Find all pattern matches for a rule.

        Args:
            content: Text to search
            rule: Detection rule with patterns and/or value_patterns

        Returns:
            List of matches (one per matching pattern), properly typed with PatternType

        """
        if not content.strip():
            return []

        matches: list[PatternMatch] = []

        for pattern in rule.patterns:
            match = self._word_boundary.find_match(content, pattern)
            if match:
                matches.append(match)

        for pattern in rule.value_patterns:
            match = self._regex.find_match(content, pattern)
            if match:
                matches.append(match)

        return matches
