"""Utility for extracting evidence snippets from content."""

from collections.abc import Iterable

from waivern_core.schemas import BaseFindingEvidence

from waivern_analysers_shared.types import EvidenceContextSize, PatternMatchResult


class EvidenceExtractor:
    """Extracts evidence snippets from content where patterns are found."""

    _ELLIPSIS = "..."

    def extract_from_results(
        self,
        content: str,
        results: Iterable[PatternMatchResult],
        context_size: EvidenceContextSize,
        max_evidence_count: int,
    ) -> list[BaseFindingEvidence]:
        """Extract evidence items from pattern match results.

        Uses round-robin collection across patterns to ensure diverse evidence.

        Args:
            content: The full content to extract evidence from
            results: Iterable of PatternMatchResult objects
            context_size: Size of context window around matches
            max_evidence_count: Maximum number of evidence items to extract

        Returns:
            List of evidence items, up to max_evidence_count

        """
        evidence_items: list[BaseFindingEvidence] = []

        # Round-robin collection: take one match from each pattern before taking
        # a second from any. This ensures evidence is representative across all
        # matched patterns, rather than being dominated by whichever pattern
        # happens to have the most matches.
        #
        # Example with max_evidence_count=3:
        #   Pattern A: 5 matches, Pattern B: 2 matches, Pattern C: 1 match
        #   Result: [A[0], B[0], C[0]] - one from each pattern
        #
        # Without round-robin, we'd get [A[0], A[1], A[2]] - all from pattern A.
        results_list = list(results)

        # Track progress through each pattern's matches independently.
        # positions[i] = index of next match to take from results_list[i]
        positions = [0] * len(results_list)

        while len(evidence_items) < max_evidence_count:
            added_any = False

            for i, result in enumerate(results_list):
                if len(evidence_items) >= max_evidence_count:
                    return evidence_items

                if positions[i] < len(result.representative_matches):
                    match = result.representative_matches[positions[i]]
                    snippet = self.extract_snippet(
                        content,
                        match.start,
                        match.matched_text_length,
                        context_size,
                    )
                    evidence_items.append(BaseFindingEvidence(content=snippet))
                    positions[i] += 1
                    added_any = True

            if not added_any:
                break

        return evidence_items

    def extract_snippet(
        self,
        content: str,
        match_start: int,
        match_length: int,
        context_size: EvidenceContextSize,
    ) -> str:
        """Extract a text snippet with context window around a position.

        Args:
            content: The full text content
            match_start: Start position of the region of interest
            match_length: Length of the region
            context_size: How much context to include on each side

        Returns:
            Snippet with ellipsis markers if truncated

        """
        context_chars = context_size.char_count

        if context_chars is None:
            return content.strip()

        # Extract a window of text centred on the match:
        #
        #   content: "Hello, my email is test@example.com for contact"
        #   match:             |email|  (start=10, length=5)
        #   context_chars: 10
        #
        #   start = max(0, 10 - 10) = 0
        #   end   = min(47, 10 + 5 + 10) = 25
        #   snippet = content[0:25] = "Hello, my email is test@"
        #
        start = max(0, match_start - context_chars)
        end = min(len(content), match_start + match_length + context_chars)

        snippet = content[start:end].strip()

        if start > 0:
            snippet = self._ELLIPSIS + snippet
        if end < len(content):
            snippet = snippet + self._ELLIPSIS

        return snippet
