"""Batch planner for LLM Service v2.

Plans batches for LLM processing using token-bounded bin-packing
(EXTENDED_CONTEXT), one-group-per-batch isolation (INDEPENDENT),
or count-based splitting (COUNT_BASED).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from waivern_core import Finding

from waivern_llm.token_estimation import TOKENS_PER_FINDING, estimate_tokens
from waivern_llm.types import BatchingMode, ItemGroup, SkippedFinding, SkipReason


@dataclass(frozen=True)
class PlannedBatch[T: Finding]:
    """A planned batch of groups for LLM processing."""

    groups: list[ItemGroup[T]]
    """Groups included in this batch."""

    estimated_tokens: int
    """Estimated total tokens for this batch."""


@dataclass(frozen=True)
class BatchPlan[T: Finding]:
    """Complete batch plan for LLM processing.

    DESIGN NOTE: skipped is a FLAT list of individual findings, not grouped.
    This is intentional - the group structure is an internal batching concern.
    Callers only need to know which findings were skipped and why, not which
    group they came from. Don't add a SkippedGroup type - it's over-engineering.
    """

    batches: list[PlannedBatch[T]]
    """Planned batches ready for processing."""

    skipped: list[SkippedFinding[T]]
    """Individual findings that were skipped with reasons.

    Flattened from skipped groups - the group structure is not preserved.
    This is intentional. See class docstring for rationale.
    """


class BatchPlanner:
    """Plans batches for LLM processing.

    Supports three modes:
    - EXTENDED_CONTEXT: Token-bounded bin-packing (first-fit-decreasing)
    - INDEPENDENT: One group per batch (preserves input order)
    - COUNT_BASED: Simple count-based splitting with flattened items
    """

    def __init__(
        self,
        max_payload_tokens: int,
        batch_size: int = 50,
        tokens_per_item: int = TOKENS_PER_FINDING,
    ) -> None:
        """Initialise the batch planner.

        Args:
            max_payload_tokens: Maximum tokens allowed per batch (EXTENDED_CONTEXT).
            batch_size: Maximum items per batch (COUNT_BASED).
            tokens_per_item: Estimated tokens per item in prompt.

        """
        self._max_payload_tokens = max_payload_tokens
        self._batch_size = batch_size
        self._tokens_per_item = tokens_per_item

    def plan[T: Finding](
        self,
        groups: Sequence[ItemGroup[T]],
        mode: BatchingMode,
    ) -> BatchPlan[T]:
        """Plan batches for the given groups.

        Args:
            groups: Groups of findings to batch.
            mode: Batching strategy to use.

        Returns:
            BatchPlan with planned batches and skipped groups.

        """
        match mode:
            case BatchingMode.EXTENDED_CONTEXT:
                return self._plan_extended_context(groups)
            case BatchingMode.INDEPENDENT:
                return self._plan_independent(groups)
            case BatchingMode.COUNT_BASED:
                return self._plan_count_based(groups)

    def _validate_groups[T: Finding](
        self,
        groups: Sequence[ItemGroup[T]],
    ) -> tuple[list[tuple[ItemGroup[T], int]], list[SkippedFinding[T]]]:
        """Validate groups and estimate tokens, skipping invalid ones.

        Returns:
            Tuple of (valid groups with token estimates, skipped findings).

        """
        valid: list[tuple[ItemGroup[T], int]] = []
        skipped: list[SkippedFinding[T]] = []

        for group in groups:
            if group.content is None:
                for item in group.items:
                    skipped.append(
                        SkippedFinding(finding=item, reason=SkipReason.MISSING_CONTENT)
                    )
                continue

            content_tokens = estimate_tokens(group.content)
            item_tokens = len(group.items) * self._tokens_per_item
            total_tokens = content_tokens + item_tokens

            if total_tokens > self._max_payload_tokens:
                for item in group.items:
                    skipped.append(
                        SkippedFinding(finding=item, reason=SkipReason.OVERSIZED)
                    )
                continue

            valid.append((group, total_tokens))

        return valid, skipped

    def _plan_extended_context[T: Finding](
        self,
        groups: Sequence[ItemGroup[T]],
    ) -> BatchPlan[T]:
        """Plan batches by bin-packing groups into token-bounded batches.

        Algorithm:
        1. Validate groups and estimate tokens
        2. Bin-pack groups into token-bounded batches (first-fit-decreasing)
        3. Create PlannedBatch for each packed batch
        """
        if not groups:
            return BatchPlan(batches=[], skipped=[])

        group_tokens, skipped = self._validate_groups(groups)
        optimised = self._optimise_extended_context_batches(group_tokens)
        batches = [
            PlannedBatch(groups=packed_groups, estimated_tokens=tokens)
            for packed_groups, tokens in optimised
        ]

        return BatchPlan(batches=batches, skipped=skipped)

    def _optimise_extended_context_batches[T: Finding](
        self,
        group_tokens: list[tuple[ItemGroup[T], int]],
    ) -> list[tuple[list[ItemGroup[T]], int]]:
        """Pack groups into token-bounded batches using first-fit-decreasing.

        Algorithm:
        1. Sort groups by token count (largest first)
        2. For each group, find the first batch with enough remaining capacity
        3. If no batch fits, create a new batch
        """
        if not group_tokens:
            return []

        # Sort largest first (first-fit-decreasing)
        sorted_groups = sorted(group_tokens, key=lambda gt: gt[1], reverse=True)

        # Each bin: (list of groups, total tokens)
        bins: list[tuple[list[ItemGroup[T]], int]] = []

        for group, tokens in sorted_groups:
            placed = False
            for i, (bin_groups, bin_tokens) in enumerate(bins):
                if bin_tokens + tokens <= self._max_payload_tokens:
                    bin_groups.append(group)
                    bins[i] = (bin_groups, bin_tokens + tokens)
                    placed = True
                    break

            if not placed:
                bins.append(([group], tokens))

        return bins

    def _plan_independent[T: Finding](
        self,
        groups: Sequence[ItemGroup[T]],
    ) -> BatchPlan[T]:
        """Plan batches with one group per batch — no bin-packing.

        Algorithm:
        1. Validate groups and estimate tokens
        2. Wrap each valid group in its own PlannedBatch
        3. Preserve input order for 1:1 group-to-response mapping
        """
        if not groups:
            return BatchPlan(batches=[], skipped=[])

        group_tokens, skipped = self._validate_groups(groups)
        batches = [
            PlannedBatch(groups=[group], estimated_tokens=tokens)
            for group, tokens in group_tokens
        ]

        return BatchPlan(batches=batches, skipped=skipped)

    def _plan_count_based[T: Finding](
        self,
        groups: Sequence[ItemGroup[T]],
    ) -> BatchPlan[T]:
        """Plan batches using count-based splitting.

        Algorithm:
        1. Flatten all items from all groups
        2. Split into chunks of batch_size
        3. Wrap each chunk in a synthetic ItemGroup with content=None
        """
        # Flatten all items
        all_items: list[T] = []
        for group in groups:
            all_items.extend(group.items)

        if not all_items:
            return BatchPlan(batches=[], skipped=[])

        # Split into chunks
        batches: list[PlannedBatch[T]] = []
        for i in range(0, len(all_items), self._batch_size):
            chunk = all_items[i : i + self._batch_size]
            # Create synthetic group with no content
            synthetic_group: ItemGroup[T] = ItemGroup(items=chunk, content=None)
            # Token estimate is just the item tokens (no content)
            estimated_tokens = len(chunk) * self._tokens_per_item
            batches.append(
                PlannedBatch(
                    groups=[synthetic_group], estimated_tokens=estimated_tokens
                )
            )

        return BatchPlan(batches=batches, skipped=[])
