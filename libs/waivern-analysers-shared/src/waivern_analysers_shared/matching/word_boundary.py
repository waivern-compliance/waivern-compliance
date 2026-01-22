"""Word boundary pattern matcher."""

import re
from functools import cache

from waivern_analysers_shared.matching.grouping import group_matches_by_proximity
from waivern_analysers_shared.types import (
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

    Prevents false positives when patterns are embedded in compound words
    or encoded strings (e.g., base64, JWT tokens).
    """

    def find_match(
        self,
        content: str,
        pattern: str,
        proximity_threshold: int = 200,
        max_representatives: int = 10,
    ) -> PatternMatchResult:
        """Find pattern in content at word boundaries.

        Args:
            content: Text to search in
            pattern: Pattern to find
            proximity_threshold: Characters between matches to consider distinct locations
            max_representatives: Maximum number of representative matches to return

        Returns:
            PatternMatchResult with representative matches grouped by proximity.

        """
        if not content or not pattern:
            return PatternMatchResult(
                pattern=pattern, representative_matches=(), match_count=0
            )

        regex = _compile_word_boundary_pattern(pattern)
        matches = list(regex.finditer(content))

        if not matches:
            return PatternMatchResult(
                pattern=pattern, representative_matches=(), match_count=0
            )

        # Group matches by proximity and get representatives
        representatives = group_matches_by_proximity(
            matches, proximity_threshold, max_representatives, PatternType.WORD_BOUNDARY
        )

        return PatternMatchResult(
            pattern=pattern,
            representative_matches=representatives,
            match_count=len(matches),
        )
