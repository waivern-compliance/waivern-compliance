"""Utility for extracting evidence snippets from content."""

from waivern_core.schemas import BaseFindingEvidence

from waivern_analysers_shared.types import PatternMatch


class EvidenceExtractor:
    """Utility for extracting evidence snippets from content where patterns are found."""

    # Context size constants (in characters)
    _CONTEXT_SIZE_SMALL = 50
    _CONTEXT_SIZE_MEDIUM = 100
    _CONTEXT_SIZE_LARGE = 200

    # Default values
    _DEFAULT_CONTEXT_SIZE = "small"

    # Special markers
    _ELLIPSIS_PREFIX = "..."
    _ELLIPSIS_SUFFIX = "..."

    # Context size options
    _CONTEXT_SIZE_FULL = "full"

    def extract_from_match(
        self,
        content: str,
        match: PatternMatch,
        context_size: str = _DEFAULT_CONTEXT_SIZE,
    ) -> BaseFindingEvidence:
        """Extract a single evidence snippet from a pattern match.

        Uses the match position directly - no re-searching required.

        Args:
            content: The full content
            match: PatternMatch with position information
            context_size: Size of context around evidence
                ('small': 50 chars, 'medium': 100 chars, 'large': 200 chars, 'full': entire content)

        Returns:
            Evidence item with content snippet around the match

        """
        snippet = self._extract_evidence_snippet(
            content,
            match.start,
            match.matched_text_length,
            context_size,
        )
        return BaseFindingEvidence(content=snippet)

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
