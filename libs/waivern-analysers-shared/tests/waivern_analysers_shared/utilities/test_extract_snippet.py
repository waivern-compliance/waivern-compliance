"""Tests for EvidenceExtractor.extract_snippet method."""

from waivern_analysers_shared.types import EvidenceContextSize
from waivern_analysers_shared.utilities import EvidenceExtractor


class TestBasicFunctionality:
    """Test basic functionality of extract_snippet."""

    def test_extracts_snippet_with_context_around_position(self) -> None:
        """Test extracting a snippet with context around a given position."""
        extractor = EvidenceExtractor()
        content = "The user email address is test@example.com for contact."
        # "email" is at position 9-14

        snippet = extractor.extract_snippet(
            content,
            match_start=9,
            match_length=5,
            context_size=EvidenceContextSize.SMALL,
        )

        assert "email" in snippet
        assert len(snippet) <= len(content)

    def test_full_context_returns_entire_content_stripped(self) -> None:
        """Test that FULL context returns the entire content stripped."""
        extractor = EvidenceExtractor()
        content = "  Some content with   whitespace  "

        snippet = extractor.extract_snippet(
            content,
            match_start=5,
            match_length=7,
            context_size=EvidenceContextSize.FULL,
        )

        assert snippet == content.strip()


class TestEllipsisHandling:
    """Test ellipsis markers in truncated snippets."""

    def test_adds_prefix_ellipsis_when_truncated_at_start(self) -> None:
        """Test that prefix ellipsis is added when content is truncated at start."""
        extractor = EvidenceExtractor()
        prefix = "x" * 200
        content = prefix + " target "

        snippet = extractor.extract_snippet(
            content,
            match_start=201,
            match_length=6,
            context_size=EvidenceContextSize.SMALL,
        )

        assert snippet.startswith("...")
        assert "target" in snippet

    def test_adds_suffix_ellipsis_when_truncated_at_end(self) -> None:
        """Test that suffix ellipsis is added when content is truncated at end."""
        extractor = EvidenceExtractor()
        suffix = "y" * 200
        content = " target " + suffix

        snippet = extractor.extract_snippet(
            content,
            match_start=1,
            match_length=6,
            context_size=EvidenceContextSize.SMALL,
        )

        assert snippet.endswith("...")
        assert "target" in snippet

    def test_adds_both_ellipses_when_truncated_at_both_ends(self) -> None:
        """Test that both ellipses are added when truncated at both ends."""
        extractor = EvidenceExtractor()
        prefix = "x" * 200
        suffix = "y" * 200
        content = prefix + " target " + suffix

        snippet = extractor.extract_snippet(
            content,
            match_start=201,
            match_length=6,
            context_size=EvidenceContextSize.SMALL,
        )

        assert snippet.startswith("...")
        assert snippet.endswith("...")
        assert "target" in snippet

    def test_no_ellipsis_when_content_fits_in_context(self) -> None:
        """Test that no ellipsis is added when content fits within context window."""
        extractor = EvidenceExtractor()
        content = "short content"

        snippet = extractor.extract_snippet(
            content,
            match_start=0,
            match_length=5,
            context_size=EvidenceContextSize.SMALL,
        )

        assert not snippet.startswith("...")
        assert not snippet.endswith("...")
        assert snippet == content
