"""Word boundary pattern matcher."""

import re
from functools import cache

from waivern_analysers_shared.types import (
    PatternMatch,
    PatternMatchResult,
    PatternType,
)


@cache
def _compile_word_boundary_pattern(pattern: str) -> re.Pattern[str]:
    """Compile pattern with word boundaries.

    Uses custom boundaries where only alphanumerics are word characters.
    Underscores and punctuation act as boundaries.
    """
    escaped = re.escape(pattern)
    return re.compile(rf"(?<![a-zA-Z0-9]){escaped}(?![a-zA-Z0-9])", re.IGNORECASE)


class WordBoundaryMatcher:
    """Matches patterns at word boundaries only.

    Reduces false positives from patterns embedded in larger strings
    like base64 tokens or compound identifiers.
    """

    def find_match(self, content: str, pattern: str) -> PatternMatchResult:
        """Find pattern in content at word boundaries.

        Args:
            content: Text to search in
            pattern: Pattern to find

        Returns:
            PatternMatchResult with first match position and total count.

        """
        if not content or not pattern:
            return PatternMatchResult(first_match=None, match_count=0)

        regex = _compile_word_boundary_pattern(pattern)
        matches = list(regex.finditer(content))

        if not matches:
            return PatternMatchResult(first_match=None, match_count=0)

        first = matches[0]
        return PatternMatchResult(
            first_match=PatternMatch(
                pattern=pattern,
                pattern_type=PatternType.WORD_BOUNDARY,
                start=first.start(),
                end=first.end(),
            ),
            match_count=len(matches),
        )
