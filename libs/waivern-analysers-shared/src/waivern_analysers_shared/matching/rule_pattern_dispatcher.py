"""Rule pattern dispatcher."""

from waivern_core import DetectionRule

from waivern_analysers_shared.matching.regex import RegexMatcher
from waivern_analysers_shared.matching.word_boundary import WordBoundaryMatcher
from waivern_analysers_shared.types import PatternMatchResult


class RulePatternDispatcher:
    """Routes DetectionRule patterns to appropriate matchers.

    - rule.patterns → WordBoundaryMatcher
    - rule.value_patterns → RegexMatcher
    """

    def __init__(self) -> None:
        """Initialise dispatcher with word boundary and regex matchers."""
        self._word_boundary = WordBoundaryMatcher()
        self._regex = RegexMatcher()

    def find_matches(
        self,
        content: str,
        rule: DetectionRule,
        proximity_threshold: int = 200,
        max_representatives: int = 10,
    ) -> list[PatternMatchResult]:
        """Find all pattern matches for a rule.

        Args:
            content: Text to search
            rule: Detection rule with patterns and/or value_patterns
            proximity_threshold: Characters between matches to consider distinct locations
            max_representatives: Maximum number of representative matches to return

        Returns:
            List of match results (one per pattern that matched), including
            representative matches grouped by proximity and total match count for each.

        """
        if not content.strip():
            return []

        results: list[PatternMatchResult] = []

        for pattern in rule.patterns:
            result = self._word_boundary.find_match(
                content, pattern, proximity_threshold, max_representatives
            )
            if result.representative_matches:  # Check new field
                results.append(result)

        for pattern in rule.value_patterns:
            result = self._regex.find_match(
                content, pattern, proximity_threshold, max_representatives
            )
            if result.representative_matches:  # Check new field
                results.append(result)

        return results
