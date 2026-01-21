"""Utility for extracting evidence snippets from content."""

from waivern_core.schemas import BaseFindingEvidence

from waivern_analysers_shared.utilities.pattern_matcher import PatternMatcher


class EvidenceExtractor:
    """Utility for extracting evidence snippets from content where patterns are found."""

    # Context size constants (in characters)
    _CONTEXT_SIZE_SMALL = 50
    _CONTEXT_SIZE_MEDIUM = 100
    _CONTEXT_SIZE_LARGE = 200

    # Default values
    _DEFAULT_MAX_EVIDENCE = 3
    _DEFAULT_CONTEXT_SIZE = "small"

    # Special markers
    _ELLIPSIS_PREFIX = "..."
    _ELLIPSIS_SUFFIX = "..."

    # Context size options
    _CONTEXT_SIZE_FULL = "full"

    def extract_evidence(
        self,
        content: str,
        pattern: str,
        max_evidence: int = _DEFAULT_MAX_EVIDENCE,
        context_size: str = _DEFAULT_CONTEXT_SIZE,
        is_value_pattern: bool = False,
    ) -> list[BaseFindingEvidence]:
        """Extract evidence snippets where the pattern was found.

        Args:
            content: The full content to search in
            pattern: The pattern that was matched (word-boundary or regex)
            max_evidence: Maximum number of evidence snippets to collect
            context_size: Size of context around evidence matches
                         ('small': 50 chars, 'medium': 100 chars, 'large': 200 chars, 'full': entire content)
            is_value_pattern: If True, use regex matching; if False, use word-boundary matching

        Returns:
            List of unique evidence items with content and collection timestamps

        """
        if not content or not pattern:
            return []

        if max_evidence <= 0:
            return []

        evidence_content_set: set[str] = set()  # Use set to avoid duplicate content
        evidence_items: list[BaseFindingEvidence] = []

        # Use PatternMatcher with appropriate matching strategy
        matcher = PatternMatcher()
        if is_value_pattern:
            matches = matcher.find_all_values(content, pattern)
        else:
            matches = matcher.find_all(content, pattern)

        # Extract evidence from each match position
        for match_start, match_end in matches:
            if len(evidence_content_set) >= max_evidence:
                break

            # Calculate actual match length (important for regex where len(pattern) != match length)
            match_length = match_end - match_start
            evidence_snippet = self._extract_evidence_snippet(
                content, match_start, match_length, context_size
            )

            if evidence_snippet and evidence_snippet not in evidence_content_set:
                evidence_content_set.add(evidence_snippet)
                evidence_items.append(BaseFindingEvidence(content=evidence_snippet))

            # For 'full' context, only include one snippet since it contains everything
            if self._is_full_context(context_size):
                break

        # Return evidence items sorted by content for consistent ordering
        return sorted(evidence_items, key=lambda item: item.content)

    def _extract_evidence_snippet(
        self, content: str, match_pos: int, match_length: int, context_size: str
    ) -> str:
        """Extract a single evidence snippet with appropriate context.

        Args:
            content: Original content
            match_pos: Position where pattern was found
            match_length: Length of the matched text
            context_size: Context size specification

        Returns:
            Evidence snippet with context, or empty string if extraction fails

        """
        context_size_chars = self._get_context_size(context_size)

        if context_size_chars is None:
            # 'full' option: include entire content without truncation
            return content.strip()
        else:
            # Standard context window extraction
            return self._extract_windowed_context(
                content, match_pos, match_length, context_size_chars
            )

    def _extract_windowed_context(
        self, content: str, match_pos: int, match_length: int, context_chars: int
    ) -> str:
        """Extract evidence with a fixed-size context window around the match.

        Args:
            content: Original content
            match_pos: Position where pattern was found
            match_length: Length of the matched text
            context_chars: Number of characters for context window

        Returns:
            Evidence snippet with context window and ellipsis markers if truncated

        """
        context_start = max(0, match_pos - context_chars)
        context_end = min(len(content), match_pos + match_length + context_chars)

        # Extract the evidence with context
        evidence_snippet = content[context_start:context_end].strip()

        # Add ellipsis if we truncated the context
        if context_start > 0:
            evidence_snippet = self._ELLIPSIS_PREFIX + evidence_snippet
        if context_end < len(content):
            evidence_snippet = evidence_snippet + self._ELLIPSIS_SUFFIX

        return evidence_snippet

    def _get_context_size(self, context_size: str) -> int | None:
        """Get the context size in characters based on the configured level.

        Args:
            context_size: Context size specification string

        Returns:
            Number of characters to include before and after each match,
            or None for full content (no truncation)

        """
        size_mapping = {
            "small": self._CONTEXT_SIZE_SMALL,
            "medium": self._CONTEXT_SIZE_MEDIUM,
            "large": self._CONTEXT_SIZE_LARGE,
            self._CONTEXT_SIZE_FULL: None,
        }
        return size_mapping.get(context_size.lower(), self._CONTEXT_SIZE_SMALL)

    def _is_full_context(self, context_size: str) -> bool:
        """Check if the context size is set to 'full'.

        Args:
            context_size: Context size specification string

        Returns:
            True if context size is 'full', False otherwise

        """
        return context_size.lower() == self._CONTEXT_SIZE_FULL
