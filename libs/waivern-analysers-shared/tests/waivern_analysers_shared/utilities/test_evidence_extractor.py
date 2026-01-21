"""Tests for EvidenceExtractor utility class.

This module tests the public API of EvidenceExtractor, focusing on black-box
testing of the extract_from_match method without accessing private implementation details.
"""

from datetime import UTC

from waivern_analysers_shared.types import PatternMatch, PatternType
from waivern_analysers_shared.utilities import EvidenceExtractor


def _make_match(pattern: str, start: int, end: int) -> PatternMatch:
    """Helper to create a PatternMatch for testing."""
    return PatternMatch(
        pattern=pattern,
        pattern_type=PatternType.WORD_BOUNDARY,
        start=start,
        end=end,
    )


class TestExtractFromMatchBasicFunctionality:
    """Test basic functionality of extract_from_match."""

    def test_extracts_evidence_snippet_around_match_position(self) -> None:
        """Test extracting evidence from a match position."""
        extractor = EvidenceExtractor()
        content = "The user email address is test@example.com for contact."
        # "email" starts at position 9
        match = _make_match("email", start=9, end=14)

        evidence = extractor.extract_from_match(content, match, context_size="small")

        assert "email" in evidence.content
        assert evidence.collection_timestamp is not None
        assert evidence.collection_timestamp.tzinfo == UTC

    def test_preserves_original_case_in_output(self) -> None:
        """Test that output preserves original case from content."""
        extractor = EvidenceExtractor()
        content = "The USERNAME field contains AdminUser123."
        # "USERNAME" starts at position 4
        match = _make_match("username", start=4, end=12)

        evidence = extractor.extract_from_match(content, match, context_size="small")

        assert "USERNAME" in evidence.content  # Original case preserved
        assert "AdminUser123" in evidence.content


class TestExtractFromMatchContextSizes:
    """Test different context size options."""

    def test_small_context_truncates_long_content(self) -> None:
        """Test that small context truncates content appropriately."""
        extractor = EvidenceExtractor()
        # Create content with pattern in the middle
        prefix = "x" * 100
        suffix = "y" * 100
        content = prefix + " target_pattern " + suffix
        match = _make_match("target_pattern", start=101, end=115)

        evidence = extractor.extract_from_match(content, match, context_size="small")

        assert "target_pattern" in evidence.content
        assert len(evidence.content) < len(content)

    def test_medium_context_provides_more_than_small(self) -> None:
        """Test that medium context provides more context than small."""
        extractor = EvidenceExtractor()
        prefix = "a" * 150
        suffix = "b" * 150
        content = prefix + " target_pattern " + suffix
        match = _make_match("target_pattern", start=151, end=165)

        small_evidence = extractor.extract_from_match(
            content, match, context_size="small"
        )
        medium_evidence = extractor.extract_from_match(
            content, match, context_size="medium"
        )

        assert "target_pattern" in small_evidence.content
        assert "target_pattern" in medium_evidence.content
        assert len(medium_evidence.content) > len(small_evidence.content)

    def test_large_context_provides_more_than_medium(self) -> None:
        """Test that large context provides more context than medium."""
        extractor = EvidenceExtractor()
        prefix = "a" * 300
        suffix = "b" * 300
        content = prefix + " target_pattern " + suffix
        match = _make_match("target_pattern", start=301, end=315)

        medium_evidence = extractor.extract_from_match(
            content, match, context_size="medium"
        )
        large_evidence = extractor.extract_from_match(
            content, match, context_size="large"
        )

        assert "target_pattern" in medium_evidence.content
        assert "target_pattern" in large_evidence.content
        assert len(large_evidence.content) > len(medium_evidence.content)

    def test_full_context_returns_entire_content(self) -> None:
        """Test that full context returns the entire content."""
        extractor = EvidenceExtractor()
        content = "Start of document. The important pattern is here. End of document."
        match = _make_match("pattern", start=33, end=40)

        evidence = extractor.extract_from_match(content, match, context_size="full")

        assert evidence.content == content.strip()

    def test_unknown_context_defaults_to_small(self) -> None:
        """Test that unknown context size defaults to small behaviour."""
        extractor = EvidenceExtractor()
        prefix = "x" * 100
        suffix = "y" * 100
        content = prefix + " target_pattern " + suffix
        match = _make_match("target_pattern", start=101, end=115)

        small_evidence = extractor.extract_from_match(
            content, match, context_size="small"
        )
        unknown_evidence = extractor.extract_from_match(
            content, match, context_size="unknown_size"
        )

        # Should behave the same as small context
        assert small_evidence.content == unknown_evidence.content


class TestExtractFromMatchEllipsisHandling:
    """Test ellipsis markers in truncated evidence."""

    def test_adds_prefix_ellipsis_when_truncated_at_start(self) -> None:
        """Test that prefix ellipsis is added when start is truncated."""
        extractor = EvidenceExtractor()
        prefix = "x" * 200
        content = prefix + " target "
        match = _make_match("target", start=201, end=207)

        evidence = extractor.extract_from_match(content, match, context_size="small")

        assert evidence.content.startswith("...")
        assert "target" in evidence.content

    def test_adds_suffix_ellipsis_when_truncated_at_end(self) -> None:
        """Test that suffix ellipsis is added when end is truncated."""
        extractor = EvidenceExtractor()
        suffix = "y" * 200
        content = " target " + suffix
        match = _make_match("target", start=1, end=7)

        evidence = extractor.extract_from_match(content, match, context_size="small")

        assert evidence.content.endswith("...")
        assert "target" in evidence.content

    def test_adds_both_ellipses_when_truncated_at_both_ends(self) -> None:
        """Test that both ellipses are added when content is truncated at both ends."""
        extractor = EvidenceExtractor()
        prefix = "x" * 200
        suffix = "y" * 200
        content = prefix + " target " + suffix
        match = _make_match("target", start=201, end=207)

        evidence = extractor.extract_from_match(content, match, context_size="small")

        assert evidence.content.startswith("...")
        assert evidence.content.endswith("...")
        assert "target" in evidence.content

    def test_no_ellipsis_for_full_context(self) -> None:
        """Test that no ellipsis is added when using full context."""
        extractor = EvidenceExtractor()
        content = "Short content with target_pattern here."
        match = _make_match("target_pattern", start=19, end=33)

        evidence = extractor.extract_from_match(content, match, context_size="full")

        assert evidence.content == content.strip()
        assert not evidence.content.startswith("...")
        assert not evidence.content.endswith("...")

    def test_no_ellipsis_when_content_fits_in_context(self) -> None:
        """Test that no ellipsis is added when content fits within context window."""
        extractor = EvidenceExtractor()
        content = "short target here"
        match = _make_match("target", start=6, end=12)

        evidence = extractor.extract_from_match(content, match, context_size="small")

        assert not evidence.content.startswith("...")
        assert not evidence.content.endswith("...")


class TestExtractFromMatchBoundaryConditions:
    """Test boundary conditions and edge cases."""

    def test_match_at_start_of_content(self) -> None:
        """Test extraction when match is at the start of content."""
        extractor = EvidenceExtractor()
        content = "target followed by more text here"
        match = _make_match("target", start=0, end=6)

        evidence = extractor.extract_from_match(content, match, context_size="small")

        assert "target" in evidence.content
        # Should not have prefix ellipsis since we're at the start
        assert not evidence.content.startswith("...")

    def test_match_at_end_of_content(self) -> None:
        """Test extraction when match is at the end of content."""
        extractor = EvidenceExtractor()
        content = "Some text before the target"
        match = _make_match("target", start=21, end=27)

        evidence = extractor.extract_from_match(content, match, context_size="small")

        assert "target" in evidence.content
        # Should not have suffix ellipsis since we're at the end
        assert not evidence.content.endswith("...")

    def test_single_character_match(self) -> None:
        """Test extraction with single character match."""
        extractor = EvidenceExtractor()
        content = "a"
        match = _make_match("a", start=0, end=1)

        evidence = extractor.extract_from_match(content, match, context_size="small")

        assert evidence.content == "a"


class TestExtractFromMatchDefaultParameters:
    """Test default parameter behaviour."""

    def test_uses_small_context_by_default(self) -> None:
        """Test that small context is used by default."""
        extractor = EvidenceExtractor()
        prefix = "x" * 200
        suffix = "y" * 200
        content = prefix + " target " + suffix
        match = _make_match("target", start=201, end=207)

        # Call without context_size parameter
        default_evidence = extractor.extract_from_match(content, match)
        small_evidence = extractor.extract_from_match(
            content, match, context_size="small"
        )

        assert default_evidence.content == small_evidence.content
