"""Regex pattern matcher."""

import re
from functools import cache

from waivern_analysers_shared.matching.grouping import group_matches_by_proximity
from waivern_analysers_shared.types import (
    PatternMatchResult,
    PatternType,
)


@cache
def _compile_regex_pattern(pattern: str) -> re.Pattern[str]:
    """Compile regex pattern with case-insensitive matching."""
    return re.compile(pattern, re.IGNORECASE)


class RegexMatcher:
    """Matches using regex patterns directly.

    Used for detecting actual data values like email addresses,
    phone numbers, etc.
    """

    def find_match(
        self,
        content: str,
        pattern: str,
        proximity_threshold: int = 200,
        max_representatives: int = 10,
    ) -> PatternMatchResult:
        """Find regex pattern in content.

        Args:
            content: Text to search in
            pattern: Regex pattern to find
            proximity_threshold: Characters between matches to consider distinct locations
            max_representatives: Maximum number of representative matches to return

        Returns:
            PatternMatchResult with representative matches grouped by proximity.

        """
        if not content or not pattern:
            return PatternMatchResult(
                pattern=pattern, representative_matches=(), match_count=0
            )

        regex = _compile_regex_pattern(pattern)
        matches = list(regex.finditer(content))

        if not matches:
            return PatternMatchResult(
                pattern=pattern, representative_matches=(), match_count=0
            )

        # Group matches by proximity and get representatives
        representatives = group_matches_by_proximity(
            matches, proximity_threshold, max_representatives, PatternType.REGEX
        )

        return PatternMatchResult(
            pattern=pattern,
            representative_matches=representatives,
            match_count=len(matches),
        )
