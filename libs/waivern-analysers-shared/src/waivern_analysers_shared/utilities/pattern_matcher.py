"""Word boundary-aware pattern matching utility."""

import re
from functools import cache


@cache
def _compile_value_pattern(pattern: str) -> re.Pattern[str]:
    """Compile and cache regex pattern for value matching.

    Args:
        pattern: The regex pattern string to compile

    Returns:
        Compiled regex pattern (case-insensitive)

    """
    return re.compile(pattern, re.IGNORECASE)


@cache
def _build_word_boundary_regex(pattern: str) -> re.Pattern[str]:
    r"""Build and cache regex with word boundaries.

    Uses custom boundary matching that treats only alphanumeric characters
    as word characters. This ensures underscores, hyphens, and other
    punctuation act as boundaries (unlike standard \b which includes
    underscore in word characters).

    The regex is cached to avoid recompilation on repeated calls with
    the same pattern, which significantly improves performance when
    matching many patterns across many lines of content.

    Args:
        pattern: The pattern to wrap with word boundaries

    Returns:
        Compiled regex pattern

    """
    escaped = re.escape(pattern)
    # Use negative lookbehind/lookahead for alphanumeric-only boundaries
    # This treats underscores and all punctuation as word boundaries
    return re.compile(rf"(?<![a-zA-Z0-9]){escaped}(?![a-zA-Z0-9])", re.IGNORECASE)


class PatternMatcher:
    """Utility for word boundary-aware pattern matching.

    This class provides pattern matching that only matches when patterns
    are surrounded by word boundaries (spaces, underscores, punctuation,
    start/end of string), reducing false positives from patterns embedded
    in larger strings like base64 tokens or compound words.
    """

    def matches(self, content: str, pattern: str) -> bool:
        """Check if pattern exists in content with word boundaries.

        Args:
            content: The text to search in
            pattern: The pattern to find

        Returns:
            True if pattern is found with word boundaries, False otherwise

        """
        if not content or not pattern:
            return False

        regex = _build_word_boundary_regex(pattern)
        return regex.search(content) is not None

    def find_all(self, content: str, pattern: str) -> list[tuple[int, int]]:
        """Find all word boundary-delimited matches.

        Args:
            content: The text to search in
            pattern: The pattern to find

        Returns:
            List of (start, end) position tuples for each match

        """
        if not content or not pattern:
            return []

        regex = _build_word_boundary_regex(pattern)
        return [(m.start(), m.end()) for m in regex.finditer(content)]

    def matches_value(self, content: str, regex_pattern: str) -> bool:
        """Check if regex pattern matches anywhere in content.

        Unlike matches(), this performs full regex matching without
        word boundary constraints. Use for value-based detection
        (e.g., finding email addresses, phone numbers).

        Args:
            content: The text to search in
            regex_pattern: The regex pattern to match

        Returns:
            True if pattern matches anywhere in content, False otherwise

        """
        if not content or not regex_pattern:
            return False

        regex = _compile_value_pattern(regex_pattern)
        return regex.search(content) is not None

    def find_all_values(
        self, content: str, regex_pattern: str
    ) -> list[tuple[int, int]]:
        """Find all regex pattern matches in content.

        Unlike find_all(), this performs full regex matching without
        word boundary constraints. Returns positions for evidence extraction.

        Args:
            content: The text to search in
            regex_pattern: The regex pattern to match

        Returns:
            List of (start, end) position tuples for each match

        """
        if not content or not regex_pattern:
            return []

        regex = _compile_value_pattern(regex_pattern)
        return [(m.start(), m.end()) for m in regex.finditer(content)]
