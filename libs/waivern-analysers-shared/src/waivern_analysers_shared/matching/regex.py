"""Regex pattern matcher."""

import re
from functools import cache

from waivern_analysers_shared.types import (
    PatternMatch,
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

    def find_match(self, content: str, pattern: str) -> PatternMatchResult:
        """Find regex pattern in content.

        Args:
            content: Text to search in
            pattern: Regex pattern to find

        Returns:
            PatternMatchResult with first match position and total count.

        """
        if not content or not pattern:
            return PatternMatchResult(pattern=pattern, first_match=None, match_count=0)

        regex = _compile_regex_pattern(pattern)
        matches = list(regex.finditer(content))

        if not matches:
            return PatternMatchResult(pattern=pattern, first_match=None, match_count=0)

        first = matches[0]
        return PatternMatchResult(
            pattern=pattern,
            first_match=PatternMatch(
                pattern=pattern,
                pattern_type=PatternType.REGEX,
                start=first.start(),
                end=first.end(),
            ),
            match_count=len(matches),
        )
