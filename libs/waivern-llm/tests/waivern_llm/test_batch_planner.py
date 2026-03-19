"""Tests for BatchPlanner in LLM Service v2.

Business behaviour: Plans batches for LLM processing using bin-packed groups
(EXTENDED_CONTEXT), one-group-per-batch isolation (INDEPENDENT),
or count-based splitting (COUNT_BASED).
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


class TestExtendedContextBinPacking:
    """Tests for EXTENDED_CONTEXT mode bin-packing behaviour."""

    def test_single_group_creates_single_batch(self) -> None:
        """Single group that fits should create one batch containing that group."""
        # Small content that fits well within limits
        group = _create_group(content="def hello(): pass", item_count=2, group_id="g1")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([group], mode=BatchingMode.EXTENDED_CONTEXT)

        assert len(plan.batches) == 1
        assert len(plan.skipped) == 0
        assert plan.batches[0].groups == [group]

    def test_small_groups_packed_into_single_batch(self) -> None:
        """Multiple small groups that fit within capacity should be packed into one batch."""
        # 3 groups, each ~75 tokens (300 chars × 0.25 + 1 item × 50)
        group1 = _create_group(content="a" * 100, item_count=1, group_id="g1")
        group2 = _create_group(content="b" * 100, item_count=1, group_id="g2")
        group3 = _create_group(content="c" * 100, item_count=1, group_id="g3")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan(
            [group1, group2, group3], mode=BatchingMode.EXTENDED_CONTEXT
        )

        assert len(plan.batches) == 1
        assert len(plan.batches[0].groups) == 3
        assert len(plan.skipped) == 0

    def test_groups_exceeding_capacity_spill_to_new_batch(self) -> None:
        """When groups don't all fit in one batch, they spill into additional batches."""
        # Each group ~5,050 tokens (20,000 chars × 0.25 + 1 × 50)
        # Capacity 6,000 → each group alone fills a batch
        # 3 groups → 3 batches
        group1 = _create_group(content="a" * 20_000, item_count=1, group_id="g1")
        group2 = _create_group(content="b" * 20_000, item_count=1, group_id="g2")
        group3 = _create_group(content="c" * 20_000, item_count=1, group_id="g3")
        planner = BatchPlanner(max_payload_tokens=6_000)

        plan = planner.plan(
            [group1, group2, group3], mode=BatchingMode.EXTENDED_CONTEXT
        )

        assert len(plan.batches) == 3
        assert all(len(b.groups) == 1 for b in plan.batches)
        assert len(plan.skipped) == 0

    def test_largest_groups_placed_first(self) -> None:
        """FFD sorts groups largest-first, so the largest group ends up in the first batch."""
        # Input order: small, medium, large — FFD should place large first
        small = _create_group(content="a" * 100, item_count=1, group_id="small")
        medium = _create_group(content="b" * 2_000, item_count=1, group_id="medium")
        large = _create_group(content="c" * 8_000, item_count=1, group_id="large")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([small, medium, large], mode=BatchingMode.EXTENDED_CONTEXT)

        # All should fit in one batch; first group should be the largest
        assert len(plan.batches) == 1
        group_ids = [g.group_id for g in plan.batches[0].groups]
        assert group_ids[0] == "large"

    def test_small_groups_fill_gaps_after_large_groups(self) -> None:
        """After placing a large group, small groups fill remaining capacity in the same batch."""
        # large: ~4,050 tokens (16,000 chars × 0.25 + 1 × 50)
        # small1, small2: ~75 tokens each (100 chars × 0.25 + 1 × 50)
        # Capacity: 5,000 → large + small1 + small2 = ~4,200, fits in one batch
        large = _create_group(content="a" * 16_000, item_count=1, group_id="large")
        small1 = _create_group(content="b" * 100, item_count=1, group_id="small1")
        small2 = _create_group(content="c" * 100, item_count=1, group_id="small2")
        planner = BatchPlanner(max_payload_tokens=5_000)

        plan = planner.plan([small1, large, small2], mode=BatchingMode.EXTENDED_CONTEXT)

        # All three should be packed into one batch
        assert len(plan.batches) == 1
        assert len(plan.batches[0].groups) == 3

    def test_each_group_fills_capacity_produces_one_batch_per_group(self) -> None:
        """When each group nearly fills capacity, no packing is possible — N groups → N batches."""
        # Each group ~5,050 tokens (20,000 chars × 0.25 + 1 × 50)
        # Capacity 5,100 → each group barely fits alone, no room for another
        group1 = _create_group(content="a" * 20_000, item_count=1, group_id="g1")
        group2 = _create_group(content="b" * 20_000, item_count=1, group_id="g2")
        group3 = _create_group(content="c" * 20_000, item_count=1, group_id="g3")
        planner = BatchPlanner(max_payload_tokens=5_100)

        plan = planner.plan(
            [group1, group2, group3], mode=BatchingMode.EXTENDED_CONTEXT
        )

        assert len(plan.batches) == 3
        assert all(len(b.groups) == 1 for b in plan.batches)

    def test_batch_token_estimate_sums_all_groups(self) -> None:
        """PlannedBatch.estimated_tokens should equal the sum of all packed groups' token estimates."""
        from waivern_llm.token_estimation import TOKENS_PER_FINDING, estimate_tokens

        content_a = "a" * 400  # ~100 tokens
        content_b = "b" * 800  # ~200 tokens
        group1 = _create_group(content=content_a, item_count=2, group_id="g1")
        group2 = _create_group(content=content_b, item_count=1, group_id="g2")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([group1, group2], mode=BatchingMode.EXTENDED_CONTEXT)

        # Both should be packed into one batch
        assert len(plan.batches) == 1
        expected = (
            estimate_tokens(content_a)
            + 2 * TOKENS_PER_FINDING
            + estimate_tokens(content_b)
            + 1 * TOKENS_PER_FINDING
        )
        assert plan.batches[0].estimated_tokens == expected


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
# INDEPENDENT Mode
# =============================================================================


class TestIndependentMode:
    """Tests for INDEPENDENT mode — one group per batch, no bin-packing."""

    def test_each_group_becomes_its_own_batch(self) -> None:
        """N groups should produce N batches, each containing exactly one group."""
        group1 = _create_group(content="a" * 100, item_count=1, group_id="g1")
        group2 = _create_group(content="b" * 100, item_count=2, group_id="g2")
        group3 = _create_group(content="c" * 100, item_count=1, group_id="g3")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([group1, group2, group3], mode=BatchingMode.INDEPENDENT)

        assert len(plan.batches) == 3
        assert len(plan.skipped) == 0
        assert plan.batches[0].groups == [group1]
        assert plan.batches[1].groups == [group2]
        assert plan.batches[2].groups == [group3]

    def test_oversized_group_skipped(self) -> None:
        """Group exceeding token limit should be skipped with OVERSIZED reason."""
        oversized = _create_group(content="x" * 100_000, item_count=1, group_id="huge")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([oversized], mode=BatchingMode.INDEPENDENT)

        assert len(plan.batches) == 0
        assert len(plan.skipped) == 1
        assert plan.skipped[0].reason == SkipReason.OVERSIZED

    def test_missing_content_skipped(self) -> None:
        """Group with content=None should be skipped with MISSING_CONTENT reason."""
        no_content = _create_group(content=None, item_count=2, group_id="no-content")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([no_content], mode=BatchingMode.INDEPENDENT)

        assert len(plan.batches) == 0
        assert len(plan.skipped) == 2
        assert all(s.reason == SkipReason.MISSING_CONTENT for s in plan.skipped)

    def test_empty_groups_returns_empty_plan(self) -> None:
        """Empty input should return empty batches and empty skipped."""
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([], mode=BatchingMode.INDEPENDENT)

        assert len(plan.batches) == 0
        assert len(plan.skipped) == 0

    def test_mixed_valid_and_invalid_groups(self) -> None:
        """Valid groups get individual batches; invalid groups are skipped."""
        valid = _create_group(content="valid content", item_count=1, group_id="valid")
        oversized = _create_group(
            content="x" * 100_000, item_count=1, group_id="oversized"
        )
        no_content = _create_group(content=None, item_count=1, group_id="no-content")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan(
            [valid, oversized, no_content], mode=BatchingMode.INDEPENDENT
        )

        assert len(plan.batches) == 1
        assert plan.batches[0].groups == [valid]
        assert len(plan.skipped) == 2
        skipped_reasons = {s.reason for s in plan.skipped}
        assert skipped_reasons == {SkipReason.OVERSIZED, SkipReason.MISSING_CONTENT}

    def test_token_estimation_scales_with_content(self) -> None:
        """Batch with more content should have higher estimated_tokens."""
        small_group = _create_group(content="a" * 100, item_count=1, group_id="small")
        large_group = _create_group(content="a" * 4000, item_count=1, group_id="large")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([small_group, large_group], mode=BatchingMode.INDEPENDENT)

        assert plan.batches[0].estimated_tokens < plan.batches[1].estimated_tokens

    def test_group_order_preserved(self) -> None:
        """Batches should preserve input group order (no sorting unlike EXTENDED_CONTEXT)."""
        small = _create_group(content="a" * 100, item_count=1, group_id="small")
        large = _create_group(content="c" * 4000, item_count=1, group_id="large")
        planner = BatchPlanner(max_payload_tokens=10_000)

        plan = planner.plan([small, large], mode=BatchingMode.INDEPENDENT)

        assert len(plan.batches) == 2
        assert plan.batches[0].groups[0].group_id == "small"
        assert plan.batches[1].groups[0].group_id == "large"


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
