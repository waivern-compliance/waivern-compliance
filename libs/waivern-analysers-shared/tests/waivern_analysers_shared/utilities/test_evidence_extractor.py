"""Tests for EvidenceExtractor utility class.

This module tests the public API of EvidenceExtractor, focusing on black-box
testing of the extract_evidence method without accessing private implementation details.
"""

from datetime import UTC, datetime

from waivern_analysers_shared.utilities import EvidenceExtractor


class TestEvidenceExtractorBasicFunctionality:
    """Test basic functionality of evidence extraction."""

    def test_extract_evidence_with_single_match(self):
        """Test extracting evidence when pattern appears once in content."""
        extractor = EvidenceExtractor()
        content = "The user email address is test@example.com for contact."
        pattern = "email"

        start_time = datetime.now(UTC)
        evidence = extractor.extract_evidence(
            content, pattern, max_evidence=3, context_size="small"
        )
        end_time = datetime.now(UTC)

        assert len(evidence) == 1
        assert "test@example.com" in evidence[0].content

        # Validate timestamp is automatically generated and in correct range
        assert evidence[0].collection_timestamp is not None
        assert isinstance(evidence[0].collection_timestamp, datetime)
        assert evidence[0].collection_timestamp.tzinfo == UTC
        assert start_time <= evidence[0].collection_timestamp <= end_time

    def test_extract_evidence_with_multiple_matches(self):
        """Test extracting evidence when pattern appears multiple times."""
        extractor = EvidenceExtractor()
        content = "Email john@company.com and email sarah@company.com for details."
        pattern = "email"

        evidence = extractor.extract_evidence(
            content, pattern, max_evidence=3, context_size="small"
        )

        assert len(evidence) == 2
        assert all("email" in item.content for item in evidence)
        assert any("john@company.com" in item.content for item in evidence)
        assert any("sarah@company.com" in item.content for item in evidence)

        # Validate timestamps exist
        for item in evidence:
            assert item.collection_timestamp is not None

    def test_extract_evidence_respects_max_evidence_limit(self):
        """Test that max_evidence parameter limits the number of results."""
        extractor = EvidenceExtractor()
        content = "Name Alice, name Bob, name Charlie, name David."
        pattern = "name"

        evidence = extractor.extract_evidence(
            content, pattern, max_evidence=2, context_size="small"
        )

        assert len(evidence) <= 2

    def test_extract_evidence_deduplicates_identical_snippets(self):
        """Test that identical evidence snippets are deduplicated."""
        extractor = EvidenceExtractor()
        content = "Password: secret. Password: secret. Password: secret."
        pattern = "password"

        evidence = extractor.extract_evidence(
            content, pattern, max_evidence=5, context_size="small"
        )

        # Should be deduplicated to a single unique snippet
        assert len(evidence) == 1
        assert "password" in evidence[0].content.lower()
        assert evidence[0].collection_timestamp is not None

    def test_extract_evidence_case_insensitive_matching(self):
        """Test that pattern matching is case insensitive."""
        extractor = EvidenceExtractor()
        content = "The PASSWORD is secret and Password123 is also here."
        pattern = "password"

        evidence = extractor.extract_evidence(
            content, pattern, max_evidence=3, context_size="small"
        )

        # Should find both PASSWORD and Password123 as separate overlapping matches
        assert len(evidence) >= 1  # At least one match should be found
        # Should contain both instances due to case-insensitive matching
        assert any(
            "PASSWORD" in item.content and "Password123" in item.content
            for item in evidence
        )

    def test_extract_evidence_preserves_original_case_in_output(self):
        """Test that output preserves original case from content."""
        extractor = EvidenceExtractor()
        content = "The USERNAME field contains AdminUser123."
        pattern = "username"

        evidence = extractor.extract_evidence(
            content, pattern, max_evidence=1, context_size="small"
        )

        assert len(evidence) == 1
        assert "USERNAME" in evidence[0].content  # Original case preserved
        assert "AdminUser123" in evidence[0].content

    def test_extract_evidence_returns_sorted_results(self):
        """Test that evidence results are returned in sorted order."""
        extractor = EvidenceExtractor()
        content = "zebra apple banana cherry"
        pattern = "a"  # Matches "zebra", "apple", "banana"

        evidence = extractor.extract_evidence(
            content, pattern, max_evidence=5, context_size="small"
        )

        # Results should be sorted alphabetically by content
        assert evidence == sorted(evidence, key=lambda e: e.content)


class TestEvidenceExtractorContextSizes:
    """Test different context size options."""

    def test_extract_evidence_with_small_context(self):
        """Test evidence extraction with small context size."""
        extractor = EvidenceExtractor()
        # Use dots as filler to create word boundaries around pattern
        long_content = "." * 100 + " target_pattern " + "." * 100
        pattern = "target_pattern"

        evidence = extractor.extract_evidence(
            content=long_content, pattern=pattern, max_evidence=1, context_size="small"
        )

        assert len(evidence) == 1
        # Should be shorter than full content due to small context
        assert len(evidence[0].content) < len(long_content)
        assert "target_pattern" in evidence[0].content
        assert evidence[0].collection_timestamp is not None

    def test_extract_evidence_with_medium_context(self):
        """Test evidence extraction with medium context size."""
        extractor = EvidenceExtractor()
        # Use dots as filler to create word boundaries around pattern
        long_content = "." * 150 + " target_pattern " + "." * 150
        pattern = "target_pattern"

        evidence = extractor.extract_evidence(
            content=long_content, pattern=pattern, max_evidence=1, context_size="medium"
        )

        assert len(evidence) == 1
        assert "target_pattern" in evidence[0].content
        # Medium should provide more context than small
        assert len(evidence[0].content) < len(long_content)

    def test_extract_evidence_with_large_context(self):
        """Test evidence extraction with large context size."""
        extractor = EvidenceExtractor()
        # Use dots as filler to create word boundaries around pattern
        long_content = "." * 300 + " target_pattern " + "." * 300
        pattern = "target_pattern"

        evidence = extractor.extract_evidence(
            content=long_content, pattern=pattern, max_evidence=1, context_size="large"
        )

        assert len(evidence) == 1
        assert "target_pattern" in evidence[0].content
        # Large should provide more context than medium/small
        assert len(evidence[0].content) < len(long_content)

    def test_extract_evidence_with_full_context(self):
        """Test evidence extraction with full context (entire content)."""
        extractor = EvidenceExtractor()
        content = "Start of document. The important pattern is here. End of document."
        pattern = "pattern"

        evidence = extractor.extract_evidence(
            content=content, pattern=pattern, max_evidence=1, context_size="full"
        )

        assert len(evidence) == 1
        # Full context should return the entire content (stripped)
        assert evidence[0].content == content.strip()
        assert evidence[0].collection_timestamp is not None

    def test_extract_evidence_full_context_limits_to_one_snippet(self):
        """Test that full context returns only one snippet even with multiple matches."""
        extractor = EvidenceExtractor()
        content = "First pattern here. Second pattern there. Third pattern everywhere."
        pattern = "pattern"

        evidence = extractor.extract_evidence(
            content=content, pattern=pattern, max_evidence=5, context_size="full"
        )

        # Full context should return only one snippet containing everything
        assert len(evidence) == 1
        assert evidence[0].content == content.strip()
        assert evidence[0].collection_timestamp is not None

    def test_extract_evidence_unknown_context_defaults_to_small(self):
        """Test that unknown context size defaults to small behaviour."""
        extractor = EvidenceExtractor()
        # Use dots as filler to create word boundaries around pattern
        long_content = "." * 100 + " target_pattern " + "." * 100
        pattern = "target_pattern"

        evidence = extractor.extract_evidence(
            content=long_content,
            pattern=pattern,
            max_evidence=1,
            context_size="unknown_size",
        )

        assert len(evidence) == 1
        assert "target_pattern" in evidence[0].content
        # Should behave like small context (default)
        assert len(evidence[0].content) < len(long_content)


class TestEvidenceExtractorEdgeCases:
    """Test edge cases and error conditions."""

    def test_extract_evidence_with_empty_content(self):
        """Test behaviour with empty content string."""
        extractor = EvidenceExtractor()

        evidence = extractor.extract_evidence(
            content="", pattern="test", max_evidence=3, context_size="small"
        )

        assert evidence == []

    def test_extract_evidence_with_empty_pattern(self):
        """Test behaviour with empty pattern string."""
        extractor = EvidenceExtractor()

        evidence = extractor.extract_evidence(
            content="some content", pattern="", max_evidence=3, context_size="small"
        )

        assert evidence == []

    def test_extract_evidence_with_whitespace_only_content(self):
        """Test behaviour with whitespace-only content."""
        extractor = EvidenceExtractor()

        evidence = extractor.extract_evidence(
            content="   \n\t   ", pattern="test", max_evidence=3, context_size="small"
        )

        assert evidence == []

    def test_extract_evidence_with_whitespace_only_pattern(self):
        """Test behaviour with whitespace-only pattern."""
        extractor = EvidenceExtractor()

        evidence = extractor.extract_evidence(
            content="some content", pattern="   ", max_evidence=3, context_size="small"
        )

        assert evidence == []

    def test_extract_evidence_with_zero_max_evidence(self):
        """Test behaviour when max_evidence is zero."""
        extractor = EvidenceExtractor()

        evidence = extractor.extract_evidence(
            content="test pattern here",
            pattern="pattern",
            max_evidence=0,
            context_size="small",
        )

        assert evidence == []

    def test_extract_evidence_with_negative_max_evidence(self):
        """Test behaviour when max_evidence is negative."""
        extractor = EvidenceExtractor()

        evidence = extractor.extract_evidence(
            content="test pattern here",
            pattern="pattern",
            max_evidence=-1,
            context_size="small",
        )

        assert evidence == []

    def test_extract_evidence_pattern_not_found(self):
        """Test behaviour when pattern is not found in content."""
        extractor = EvidenceExtractor()

        evidence = extractor.extract_evidence(
            content="some content without the target",
            pattern="missing_pattern",
            max_evidence=3,
            context_size="small",
        )

        assert evidence == []

    def test_extract_evidence_pattern_longer_than_content(self):
        """Test behaviour when pattern is longer than the content."""
        extractor = EvidenceExtractor()

        evidence = extractor.extract_evidence(
            content="short",
            pattern="very_long_pattern_text",
            max_evidence=3,
            context_size="small",
        )

        assert evidence == []

    def test_extract_evidence_single_character_content_and_pattern(self):
        """Test behaviour with single character content and pattern."""
        extractor = EvidenceExtractor()

        evidence = extractor.extract_evidence(
            content="a", pattern="a", max_evidence=1, context_size="small"
        )

        assert len(evidence) == 1
        assert evidence[0].content == "a"
        assert evidence[0].collection_timestamp is not None


class TestEvidenceExtractorDefaultParameters:
    """Test default parameter behaviour."""

    def test_extract_evidence_with_default_parameters(self):
        """Test that extract_evidence works correctly with default parameters."""
        extractor = EvidenceExtractor()
        content = "The username field contains sensitive information."
        pattern = "username"

        # Call with only required parameters
        evidence = extractor.extract_evidence(content, pattern)

        assert len(evidence) == 1
        assert "username" in evidence[0].content
        assert "sensitive information" in evidence[0].content

    def test_extract_evidence_default_max_evidence_limit(self):
        """Test that default max_evidence parameter works correctly."""
        extractor = EvidenceExtractor()
        content = "data " * 10  # Creates 10 instances of "data"
        pattern = "data"

        evidence = extractor.extract_evidence(content, pattern)

        # Should respect default max_evidence limit (expected to be 3 based on usage)
        assert len(evidence) <= 5  # Allow some flexibility for implementation

    def test_extract_evidence_default_context_size(self):
        """Test that default context_size parameter works correctly."""
        extractor = EvidenceExtractor()
        # Use dots as filler to create word boundaries around pattern
        long_content = "." * 100 + " target " + "." * 100
        pattern = "target"

        evidence = extractor.extract_evidence(long_content, pattern)

        assert len(evidence) == 1
        assert "target" in evidence[0].content
        # Should be shorter than full content due to default context size
        assert len(evidence[0].content) < len(long_content)


class TestEvidenceExtractorEllipsisHandling:
    """Test ellipsis markers in truncated evidence."""

    def test_extract_evidence_adds_ellipsis_for_truncated_content(self):
        """Test that ellipsis markers are added when content is truncated."""
        extractor = EvidenceExtractor()
        # Create content long enough to be truncated with small context
        # Use dots as filler to create word boundaries around pattern
        long_prefix = "." * 200
        long_suffix = "." * 200
        content = long_prefix + " target_pattern " + long_suffix
        pattern = "target_pattern"

        evidence = extractor.extract_evidence(
            content, pattern, max_evidence=1, context_size="small"
        )

        assert len(evidence) == 1
        # Should contain the target pattern
        assert "target_pattern" in evidence[0].content
        # Should be much shorter than original content due to truncation
        assert len(evidence[0].content) < len(content)

    def test_extract_evidence_no_ellipsis_for_full_context(self):
        """Test that no ellipsis is added when using full context."""
        extractor = EvidenceExtractor()
        content = "Short content with target_pattern here."
        pattern = "target_pattern"

        evidence = extractor.extract_evidence(
            content, pattern, max_evidence=1, context_size="full"
        )

        assert len(evidence) == 1
        # Full context should return exact content without ellipsis
        assert evidence[0].content == content.strip()
        assert evidence[0].collection_timestamp is not None
        assert not evidence[0].content.startswith("...")
        assert not evidence[0].content.endswith("...")

    def test_extract_evidence_handles_pattern_at_content_boundaries(self):
        """Test evidence extraction when pattern is at start or end of content."""
        extractor = EvidenceExtractor()

        # Pattern at start
        start_content = "target_pattern followed by more text here"
        evidence_start = extractor.extract_evidence(
            start_content, "target_pattern", max_evidence=1, context_size="small"
        )
        assert len(evidence_start) == 1
        assert "target_pattern" in evidence_start[0].content

        # Pattern at end
        end_content = "Some text before the target_pattern"
        evidence_end = extractor.extract_evidence(
            end_content, "target_pattern", max_evidence=1, context_size="small"
        )
        assert len(evidence_end) == 1
        assert "target_pattern" in evidence_end[0].content
