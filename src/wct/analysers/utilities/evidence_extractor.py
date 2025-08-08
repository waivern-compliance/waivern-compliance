"""Utility for extracting evidence snippets from content."""


class EvidenceExtractor:
    """Utility for extracting evidence snippets from content where patterns are found."""

    def extract_evidence(
        self,
        content: str,
        pattern: str,
        max_evidence: int = 3,
        context_size: str = "small",
    ) -> list[str]:
        """Extract evidence snippets where the pattern was found.

        Args:
            content: The full content to search in
            pattern: The pattern that was matched
            max_evidence: Maximum number of evidence snippets to collect
            context_size: Size of context around evidence matches
                         ('small': 50 chars, 'medium': 100 chars, 'large': 200 chars, 'full': entire content)

        Returns:
            List of unique evidence snippets showing context around matches
        """
        evidence_set = set()  # Use set to avoid duplicates
        content_lower = content.lower()
        pattern_lower = pattern.lower()

        # Find all occurrences of the pattern
        start_pos = 0
        while len(evidence_set) < max_evidence:
            match_pos = content_lower.find(pattern_lower, start_pos)
            if match_pos == -1:
                break

            # Extract context around the match
            context_size_chars = self.get_context_size(context_size)

            if context_size_chars is None:
                # 'full' option: include entire content without truncation
                evidence_snippet = content.strip()
            else:
                # Standard context window extraction
                context_start = max(0, match_pos - context_size_chars)
                context_end = min(
                    len(content), match_pos + len(pattern) + context_size_chars
                )

                # Extract the evidence with context
                evidence_snippet = content[context_start:context_end].strip()

                # Add ellipsis if we truncated the context
                if context_start > 0:
                    evidence_snippet = "..." + evidence_snippet
                if context_end < len(content):
                    evidence_snippet = evidence_snippet + "..."

            # Add to set to automatically deduplicate
            evidence_set.add(evidence_snippet)

            # Move past this match to find the next occurrence
            start_pos = match_pos + 1

            # For 'full' context, only include one snippet since it contains everything
            if context_size_chars is None:
                break

        # Convert set back to list and maintain consistent ordering
        return sorted(list(evidence_set))

    def get_context_size(self, context_size: str) -> int | None:
        """Get the context size in characters based on the configured level.

        Returns:
            Number of characters to include before and after each match,
            or None for full content (no truncation)
        """
        size_mapping = {"small": 50, "medium": 100, "large": 200, "full": None}
        return size_mapping.get(context_size.lower(), 50)
