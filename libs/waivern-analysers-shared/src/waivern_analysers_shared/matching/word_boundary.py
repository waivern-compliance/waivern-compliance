"""Word boundary pattern matcher."""

import re
from functools import cache

from waivern_analysers_shared.types import PatternMatch, PatternType


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

    def find_match(self, content: str, pattern: str) -> PatternMatch | None:
        """Find first match of pattern in content at word boundaries.

        Args:
            content: Text to search in
            pattern: Pattern to find

        Returns:
            PatternMatch if found, None otherwise.

        """
        if not content or not pattern:
            return None

        regex = _compile_word_boundary_pattern(pattern)
        match = regex.search(content)

        if match:
            return PatternMatch(
                pattern=pattern,
                pattern_type=PatternType.WORD_BOUNDARY,
                start=match.start(),
                end=match.end(),
            )

        return None
