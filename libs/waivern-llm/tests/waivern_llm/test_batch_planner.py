"""Tests for BatchPlanner in LLM Service v2.

Business behaviour: Plans batches for LLM processing using either
token-aware bin-packing (EXTENDED_CONTEXT) or count-based splitting (COUNT_BASED).
"""

from waivern_llm.batch_planner import BatchPlanner
from waivern_llm.types import BatchingMode, ItemGroup, SkipReason

# =============================================================================
# Test Fixtures
# =============================================================================


class MockMetadata:
    """Minimal metadata satisfying FindingMetadata protocol."""

    def __init__(self, source: str = "test.py") -> None:
        self._source = source

    @property
    def source(self) -> str:
        return self._source


class MockFinding:
    """Minimal finding for testing (satisfies Finding protocol)."""

    def __init__(self, finding_id: str, source: str = "test.py") -> None:
        self._id = finding_id
        self._metadata = MockMetadata(source)

    @property
    def id(self) -> str:
        return self._id

    @property
    def metadata(self) -> MockMetadata:
        return self._metadata


def _create_group(
    content: str | None,
    item_count: int = 1,
    group_id: str | None = None,
) -> ItemGroup[MockFinding]:
    """Create a test ItemGroup with the specified content and item count."""
    items = [MockFinding(f"finding-{i}") for i in range(item_count)]
    return ItemGroup(items=items, content=content, group_id=group_id)


# =============================================================================
# EXTENDED_CONTEXT Mode - Basic Batching
# =============================================================================


class TestExtendedContextBasicBatching:
    """Tests for EXTENDED_CONTEXT mode basic batching behaviour."""

    def test_single_group_creates_single_batch(self) -> None:
        """Single group that fits should create one batch containing that group."""
        # Small content that fits well within limits
        group = _create_group(content="def hello(): pass", item_count=2, group_id="g1")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([group], mode=BatchingMode.EXTENDED_CONTEXT)

        assert len(plan.batches) == 1
        assert len(plan.skipped) == 0
        assert plan.batches[0].groups == [group]

    def test_multiple_groups_fit_in_single_batch(self) -> None:
        """Groups whose combined tokens fit should be in one batch."""
        # Two small groups that together fit within 10,000 tokens
        group1 = _create_group(
            content="a" * 100, item_count=2, group_id="g1"
        )  # ~25 + 100 tokens
        group2 = _create_group(
            content="b" * 100, item_count=2, group_id="g2"
        )  # ~25 + 100 tokens
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([group1, group2], mode=BatchingMode.EXTENDED_CONTEXT)

        assert len(plan.batches) == 1
        assert len(plan.batches[0].groups) == 2
        assert group1 in plan.batches[0].groups
        assert group2 in plan.batches[0].groups

    def test_groups_split_into_multiple_batches_when_exceeding_limit(self) -> None:
        """Groups that don't fit together should be split into multiple batches."""
        # Each group is ~2500 tokens (10,000 chars × 0.25), so only one fits in 3,000
        group1 = _create_group(content="a" * 10_000, item_count=1, group_id="g1")
        group2 = _create_group(content="b" * 10_000, item_count=1, group_id="g2")
        planner = BatchPlanner(max_payload_tokens=3_000)

        plan = planner.plan([group1, group2], mode=BatchingMode.EXTENDED_CONTEXT)

        assert len(plan.batches) == 2
        assert len(plan.batches[0].groups) == 1
        assert len(plan.batches[1].groups) == 1

    def test_largest_groups_placed_first_for_better_packing(self) -> None:
        """Groups should be sorted by tokens descending for first-fit decreasing.

        Verifies the algorithm sorts groups largest-first by checking the OUTPUT
        order reflects the sorted order, not the input order.
        """
        # Create groups with clearly different sizes
        small = _create_group(
            content="a" * 100, item_count=1, group_id="small"
        )  # ~25 tokens
        large = _create_group(
            content="c" * 4000, item_count=1, group_id="large"
        )  # ~1000 tokens
        planner = BatchPlanner(max_payload_tokens=2_000)

        # Input order: small THEN large
        plan = planner.plan([small, large], mode=BatchingMode.EXTENDED_CONTEXT)

        # After sorting: large, small (both fit in one batch)
        assert len(plan.batches) == 1
        # Large should be FIRST because sorting processes largest first
        assert plan.batches[0].groups[0].group_id == "large"
        assert plan.batches[0].groups[1].group_id == "small"


# =============================================================================
# EXTENDED_CONTEXT Mode - Edge Cases
# =============================================================================


class TestExtendedContextEdgeCases:
    """Tests for EXTENDED_CONTEXT mode edge cases."""

    def test_oversized_group_skipped_with_reason(self) -> None:
        """Findings in oversized group should be skipped with OVERSIZED."""
        # Group with ~25,000 tokens (100,000 chars × 0.25)
        oversized = _create_group(content="x" * 100_000, item_count=1, group_id="huge")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([oversized], mode=BatchingMode.EXTENDED_CONTEXT)

        assert len(plan.batches) == 0
        assert len(plan.skipped) == 1
        assert plan.skipped[0].finding == oversized.items[0]
        assert plan.skipped[0].reason == SkipReason.OVERSIZED

    def test_missing_content_skipped_with_reason(self) -> None:
        """Findings in group with content=None should be skipped with MISSING_CONTENT."""
        # Group without content (extended context requires content)
        no_content = _create_group(content=None, item_count=2, group_id="no-content")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([no_content], mode=BatchingMode.EXTENDED_CONTEXT)

        assert len(plan.batches) == 0
        # All 2 findings in the group should be skipped
        assert len(plan.skipped) == 2
        assert plan.skipped[0].finding == no_content.items[0]
        assert plan.skipped[0].reason == SkipReason.MISSING_CONTENT
        assert plan.skipped[1].finding == no_content.items[1]
        assert plan.skipped[1].reason == SkipReason.MISSING_CONTENT

    def test_empty_groups_returns_empty_plan(self) -> None:
        """Empty input should return empty batches and empty skipped."""
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([], mode=BatchingMode.EXTENDED_CONTEXT)

        assert len(plan.batches) == 0
        assert len(plan.skipped) == 0

    def test_mixed_valid_and_invalid_groups(self) -> None:
        """Mix of valid, oversized, and missing content should be handled correctly."""
        valid = _create_group(content="valid content", item_count=1, group_id="valid")
        oversized = _create_group(
            content="x" * 100_000, item_count=1, group_id="oversized"
        )
        no_content = _create_group(content=None, item_count=1, group_id="no-content")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan(
            [valid, oversized, no_content], mode=BatchingMode.EXTENDED_CONTEXT
        )

        # Valid group should be batched
        assert len(plan.batches) == 1
        assert plan.batches[0].groups == [valid]

        # Findings from invalid groups should be skipped with correct reasons
        assert len(plan.skipped) == 2
        # Map by finding object identity
        skipped_by_finding = {id(s.finding): s for s in plan.skipped}
        assert skipped_by_finding[id(oversized.items[0])].reason == SkipReason.OVERSIZED
        assert (
            skipped_by_finding[id(no_content.items[0])].reason
            == SkipReason.MISSING_CONTENT
        )


# =============================================================================
# COUNT_BASED Mode
# =============================================================================


class TestCountBasedMode:
    """Tests for COUNT_BASED mode."""

    def test_count_based_flattens_items_across_groups(self) -> None:
        """Items from multiple groups should be combined into batches."""
        # Two groups with 2 items each
        group1 = _create_group(content="content1", item_count=2, group_id="g1")
        group2 = _create_group(content="content2", item_count=2, group_id="g2")
        planner = BatchPlanner(max_payload_tokens=10_000, batch_size=10)

        plan = planner.plan([group1, group2], mode=BatchingMode.COUNT_BASED)

        # All 4 items should be in a single batch (batch_size=10 > 4 items)
        assert len(plan.batches) == 1
        assert len(plan.batches[0].groups) == 1  # Synthetic group
        assert len(plan.batches[0].groups[0].items) == 4

    def test_count_based_splits_by_batch_size(self) -> None:
        """Items exceeding batch_size should be split into multiple batches."""
        # Group with 5 items, batch_size=2
        group = _create_group(content="content", item_count=5, group_id="g1")
        planner = BatchPlanner(max_payload_tokens=10_000, batch_size=2)

        plan = planner.plan([group], mode=BatchingMode.COUNT_BASED)

        # 5 items with batch_size=2 → 3 batches (2, 2, 1)
        assert len(plan.batches) == 3
        assert len(plan.batches[0].groups[0].items) == 2
        assert len(plan.batches[1].groups[0].items) == 2
        assert len(plan.batches[2].groups[0].items) == 1

    def test_count_based_ignores_content(self) -> None:
        """Groups with content should have content=None in output batches."""
        group = _create_group(content="this content should be ignored", item_count=2)
        planner = BatchPlanner(max_payload_tokens=10_000, batch_size=10)

        plan = planner.plan([group], mode=BatchingMode.COUNT_BASED)

        # Output groups should have no content
        assert len(plan.batches) == 1
        assert plan.batches[0].groups[0].content is None

    def test_count_based_empty_groups_returns_empty_plan(self) -> None:
        """Empty groups should return empty plan."""
        planner = BatchPlanner(max_payload_tokens=10_000, batch_size=10)

        plan = planner.plan([], mode=BatchingMode.COUNT_BASED)

        assert len(plan.batches) == 0
        assert len(plan.skipped) == 0


# =============================================================================
# Token Estimation Integration
# =============================================================================


class TestTokenEstimationIntegration:
    """Tests for token estimation in batch planning."""

    def test_estimated_tokens_includes_content_and_items(self) -> None:
        """PlannedBatch.estimated_tokens should equal content tokens + items × TOKENS_PER_FINDING."""
        from waivern_llm.token_estimation import TOKENS_PER_FINDING, estimate_tokens

        content = "a" * 400  # ~100 tokens (400 × 0.25)
        group = _create_group(content=content, item_count=3)  # 3 × 50 = 150 tokens
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([group], mode=BatchingMode.EXTENDED_CONTEXT)

        expected_tokens = estimate_tokens(content) + 3 * TOKENS_PER_FINDING
        assert plan.batches[0].estimated_tokens == expected_tokens
