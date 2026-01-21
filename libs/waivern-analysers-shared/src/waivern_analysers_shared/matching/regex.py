"""Regex pattern matcher."""

import re
from functools import cache

from waivern_analysers_shared.types import PatternMatch, PatternType


@cache
def _compile_regex_pattern(pattern: str) -> re.Pattern[str]:
    """Compile regex pattern with case-insensitive matching."""
    return re.compile(pattern, re.IGNORECASE)


class RegexMatcher:
    """Matches using regex patterns directly.

    Used for detecting actual data values like email addresses,
    phone numbers, etc.
    """

    def find_match(self, content: str, pattern: str) -> PatternMatch | None:
        """Find first match of regex pattern in content.

        Args:
            content: Text to search in
            pattern: Regex pattern to find

        Returns:
            PatternMatch if found, None otherwise.

        """
        if not content or not pattern:
            return None

        regex = _compile_regex_pattern(pattern)
        match = regex.search(content)

        if match:
            return PatternMatch(
                pattern=pattern,
                pattern_type=PatternType.REGEX,
                start=match.start(),
                end=match.end(),
            )

        return None
