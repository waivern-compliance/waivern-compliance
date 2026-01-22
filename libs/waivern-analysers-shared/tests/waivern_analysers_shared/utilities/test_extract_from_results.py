"""Tests for EvidenceExtractor.extract_from_results method."""

from datetime import UTC

from waivern_analysers_shared.types import (
    EvidenceContextSize,
    PatternMatch,
    PatternMatchResult,
    PatternType,
)
from waivern_analysers_shared.utilities import EvidenceExtractor


def _make_result(start: int, end: int, pattern: str = "test") -> PatternMatchResult:
    """Helper to create a PatternMatchResult with a single match for testing."""
    match = PatternMatch(
        pattern_type=PatternType.WORD_BOUNDARY,
        start=start,
        end=end,
    )
    return PatternMatchResult(
        pattern=pattern,
        representative_matches=(match,),
        match_count=1,
    )


def _make_result_with_matches(
    pattern: str, positions: list[tuple[int, int]]
) -> PatternMatchResult:
    """Helper to create a PatternMatchResult with multiple matches."""
    matches = tuple(
        PatternMatch(pattern_type=PatternType.WORD_BOUNDARY, start=start, end=end)
        for start, end in positions
    )
    return PatternMatchResult(
        pattern=pattern,
        representative_matches=matches,
        match_count=len(matches),
    )


class TestBasicFunctionality:
    """Test basic functionality of extract_from_results."""

    def test_extracts_evidence_snippet_around_match_position(self) -> None:
        """Test extracting evidence from a match position."""
        extractor = EvidenceExtractor()
        content = "The user email address is test@example.com for contact."
        # "email" starts at position 9
        results = [_make_result(start=9, end=14, pattern="email")]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.SMALL, max_evidence_count=3
        )

        assert len(evidence_list) == 1
        assert "email" in evidence_list[0].content
        assert evidence_list[0].collection_timestamp is not None
        assert evidence_list[0].collection_timestamp.tzinfo == UTC

    def test_preserves_original_case_in_output(self) -> None:
        """Test that output preserves original case from content."""
        extractor = EvidenceExtractor()
        content = "The USERNAME field contains AdminUser123."
        # "USERNAME" starts at position 4
        results = [_make_result(start=4, end=12)]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.SMALL, max_evidence_count=3
        )

        assert len(evidence_list) == 1
        assert "USERNAME" in evidence_list[0].content
        assert "AdminUser123" in evidence_list[0].content

    def test_respects_max_evidence_count(self) -> None:
        """Test that max_evidence_count limits the number of evidence items."""
        extractor = EvidenceExtractor()
        content = "word1 word2 word3 word4 word5"
        results = [
            _make_result(start=0, end=5),
            _make_result(start=6, end=11),
            _make_result(start=12, end=17),
            _make_result(start=18, end=23),
        ]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.SMALL, max_evidence_count=2
        )

        assert len(evidence_list) == 2


class TestContextSizes:
    """Test different context size options."""

    def test_small_context_truncates_long_content(self) -> None:
        """Test that small context truncates content appropriately."""
        extractor = EvidenceExtractor()
        prefix = "x" * 100
        suffix = "y" * 100
        content = prefix + " target_pattern " + suffix
        results = [_make_result(start=101, end=115)]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.SMALL, max_evidence_count=3
        )

        assert len(evidence_list) == 1
        assert "target_pattern" in evidence_list[0].content
        assert len(evidence_list[0].content) < len(content)

    def test_medium_context_provides_more_than_small(self) -> None:
        """Test that medium context provides more context than small."""
        extractor = EvidenceExtractor()
        prefix = "a" * 150
        suffix = "b" * 150
        content = prefix + " target_pattern " + suffix
        results = [_make_result(start=151, end=165)]

        small_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.SMALL, max_evidence_count=3
        )
        medium_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.MEDIUM, max_evidence_count=3
        )

        assert "target_pattern" in small_list[0].content
        assert "target_pattern" in medium_list[0].content
        assert len(medium_list[0].content) > len(small_list[0].content)

    def test_large_context_provides_more_than_medium(self) -> None:
        """Test that large context provides more context than medium."""
        extractor = EvidenceExtractor()
        prefix = "a" * 300
        suffix = "b" * 300
        content = prefix + " target_pattern " + suffix
        results = [_make_result(start=301, end=315)]

        medium_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.MEDIUM, max_evidence_count=3
        )
        large_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.LARGE, max_evidence_count=3
        )

        assert "target_pattern" in medium_list[0].content
        assert "target_pattern" in large_list[0].content
        assert len(large_list[0].content) > len(medium_list[0].content)

    def test_full_context_returns_entire_content(self) -> None:
        """Test that full context returns the entire content."""
        extractor = EvidenceExtractor()
        content = "Start of document. The important pattern is here. End of document."
        results = [_make_result(start=33, end=40)]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.FULL, max_evidence_count=3
        )

        assert evidence_list[0].content == content.strip()


class TestEllipsisHandling:
    """Test ellipsis markers in truncated evidence."""

    def test_adds_prefix_ellipsis_when_truncated_at_start(self) -> None:
        """Test that prefix ellipsis is added when start is truncated."""
        extractor = EvidenceExtractor()
        prefix = "x" * 200
        content = prefix + " target "
        results = [_make_result(start=201, end=207)]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.SMALL, max_evidence_count=3
        )

        assert evidence_list[0].content.startswith("...")
        assert "target" in evidence_list[0].content

    def test_adds_suffix_ellipsis_when_truncated_at_end(self) -> None:
        """Test that suffix ellipsis is added when end is truncated."""
        extractor = EvidenceExtractor()
        suffix = "y" * 200
        content = " target " + suffix
        results = [_make_result(start=1, end=7)]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.SMALL, max_evidence_count=3
        )

        assert evidence_list[0].content.endswith("...")
        assert "target" in evidence_list[0].content

    def test_adds_both_ellipses_when_truncated_at_both_ends(self) -> None:
        """Test that both ellipses are added when truncated at both ends."""
        extractor = EvidenceExtractor()
        prefix = "x" * 200
        suffix = "y" * 200
        content = prefix + " target " + suffix
        results = [_make_result(start=201, end=207)]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.SMALL, max_evidence_count=3
        )

        assert evidence_list[0].content.startswith("...")
        assert evidence_list[0].content.endswith("...")
        assert "target" in evidence_list[0].content

    def test_no_ellipsis_for_full_context(self) -> None:
        """Test that no ellipsis is added when using full context."""
        extractor = EvidenceExtractor()
        content = "Short content with target_pattern here."
        results = [_make_result(start=19, end=33)]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.FULL, max_evidence_count=3
        )

        assert evidence_list[0].content == content.strip()
        assert not evidence_list[0].content.startswith("...")
        assert not evidence_list[0].content.endswith("...")

    def test_no_ellipsis_when_content_fits_in_context(self) -> None:
        """Test that no ellipsis is added when content fits within context."""
        extractor = EvidenceExtractor()
        content = "short target here"
        results = [_make_result(start=6, end=12)]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.SMALL, max_evidence_count=3
        )

        assert not evidence_list[0].content.startswith("...")
        assert not evidence_list[0].content.endswith("...")


class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""

    def test_match_at_start_of_content(self) -> None:
        """Test extraction when match is at the start of content."""
        extractor = EvidenceExtractor()
        content = "target followed by more text here"
        results = [_make_result(start=0, end=6)]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.SMALL, max_evidence_count=3
        )

        assert "target" in evidence_list[0].content
        assert not evidence_list[0].content.startswith("...")

    def test_match_at_end_of_content(self) -> None:
        """Test extraction when match is at the end of content."""
        extractor = EvidenceExtractor()
        content = "Some text before the target"
        results = [_make_result(start=21, end=27)]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.SMALL, max_evidence_count=3
        )

        assert "target" in evidence_list[0].content
        assert not evidence_list[0].content.endswith("...")

    def test_single_character_match(self) -> None:
        """Test extraction with single character match."""
        extractor = EvidenceExtractor()
        content = "a"
        results = [_make_result(start=0, end=1)]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.SMALL, max_evidence_count=3
        )

        assert evidence_list[0].content == "a"

    def test_empty_results_returns_empty_list(self) -> None:
        """Test that empty results returns empty list."""
        extractor = EvidenceExtractor()
        content = "Some content here"

        evidence_list = extractor.extract_from_results(
            content, [], EvidenceContextSize.SMALL, max_evidence_count=3
        )

        assert evidence_list == []


class TestRoundRobinCollection:
    """Test round-robin evidence collection across patterns."""

    def test_collects_one_from_each_pattern_before_second_from_any(self) -> None:
        """Round-robin ensures diverse evidence across all matched patterns."""
        extractor = EvidenceExtractor()
        # Content: "email phone address extra_email extra_phone"
        #           0     6     12      20          32
        content = "email phone address extra_email extra_phone"

        # Three patterns, each with multiple matches
        results = [
            _make_result_with_matches("email", [(0, 5), (20, 31)]),  # 2 matches
            _make_result_with_matches("phone", [(6, 11), (32, 43)]),  # 2 matches
            _make_result_with_matches("address", [(12, 19)]),  # 1 match
        ]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.FULL, max_evidence_count=3
        )

        # Should get one from each pattern (round-robin), not all from first pattern
        assert len(evidence_list) == 3
        assert "email" in evidence_list[0].content  # First from pattern A
        assert "phone" in evidence_list[1].content  # First from pattern B
        assert "address" in evidence_list[2].content  # First from pattern C

    def test_continues_round_robin_when_some_patterns_exhausted(self) -> None:
        """Continues collecting from patterns that still have matches."""
        extractor = EvidenceExtractor()
        content = "aa bb cc dd ee"

        # Pattern A has 3 matches, Pattern B has 1 match
        results = [
            _make_result_with_matches("pattern_a", [(0, 2), (6, 8), (12, 14)]),
            _make_result_with_matches("pattern_b", [(3, 5)]),
        ]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.FULL, max_evidence_count=4
        )

        # Round 1: A[0], B[0] = 2 items
        # Round 2: A[1] (B exhausted) = 1 item
        # Round 3: A[2] = 1 item
        # Total: 4 items
        assert len(evidence_list) == 4

    def test_single_pattern_with_multiple_matches(self) -> None:
        """Single pattern collects matches sequentially."""
        extractor = EvidenceExtractor()
        content = "first second third"

        results = [
            _make_result_with_matches("word", [(0, 5), (6, 12), (13, 18)]),
        ]

        evidence_list = extractor.extract_from_results(
            content, results, EvidenceContextSize.FULL, max_evidence_count=2
        )

        assert len(evidence_list) == 2
        assert "first" in evidence_list[0].content
        assert "second" in evidence_list[1].content
