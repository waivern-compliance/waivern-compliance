"""Stratified evidence sampling for ISO 27001 control assessment.

Reduces the number of evidence items sent to the LLM while preserving
assessment quality through priority-preserving stratified sampling.
"""

from dataclasses import dataclass, field

from waivern_schemas.security_evidence import SecurityEvidenceModel


@dataclass(frozen=True)
class StratumSummary:
    """Per-stratum breakdown for the LLM prompt."""

    evidence_type: str
    total: int
    sampled: int


@dataclass(frozen=True)
class StratifiedSampleResult:
    """Result of stratified evidence sampling."""

    items: list[SecurityEvidenceModel]
    was_sampled: bool
    total_evidence: int = 0
    total_priority: int = 0
    strata: list[StratumSummary] = field(default_factory=list)


def stratified_sample(
    items: list[SecurityEvidenceModel],
    max_items: int,
) -> StratifiedSampleResult:
    """Sample evidence items using priority-preserving stratified sampling.

    Algorithm:
    1. Partition into priority (negative polarity) and non-priority
    2. Include all priority items unconditionally — deduct from budget
    3. Early exit if budget covers all remaining items
    4. Stratify non-priority items by evidence_type
    5. Allocate budget proportionally to each stratum
    6. Select within each stratum via round-robin across sources

    Args:
        items: Evidence items to sample from.
        max_items: Maximum number of items in the result.

    Returns:
        StratifiedSampleResult with selected items and sampling metadata.

    """
    if len(items) <= max_items:
        return StratifiedSampleResult(
            items=list(items), was_sampled=False, total_evidence=len(items)
        )

    # Step 1-2: Partition and include all priority (negative) items
    priority = [i for i in items if i.polarity == "negative"]
    non_priority = [i for i in items if i.polarity != "negative"]
    total = len(items)
    n_priority = len(priority)

    remaining_budget = max_items - n_priority

    # Priority items alone exceed budget — include all negatives anyway
    if remaining_budget <= 0:
        return StratifiedSampleResult(
            items=priority,
            was_sampled=True,
            total_evidence=total,
            total_priority=n_priority,
            strata=_build_strata(non_priority, set()),
        )

    # Step 3: Early exit if budget covers all remaining
    if len(non_priority) <= remaining_budget:
        return StratifiedSampleResult(
            items=list(items), was_sampled=False, total_evidence=total
        )

    # Step 4-6: Stratify, allocate, and select
    selected = _select_from_strata(non_priority, remaining_budget)

    result_items = priority + selected
    selected_ids = {i.id for i in selected}
    return StratifiedSampleResult(
        items=result_items,
        was_sampled=True,
        total_evidence=total,
        total_priority=n_priority,
        strata=_build_strata(non_priority, selected_ids),
    )


def _select_from_strata(
    items: list[SecurityEvidenceModel],
    budget: int,
) -> list[SecurityEvidenceModel]:
    """Allocate budget proportionally across evidence_type strata, then round-robin by source."""
    # Group by evidence_type
    strata: dict[str, list[SecurityEvidenceModel]] = {}
    for item in items:
        strata.setdefault(item.evidence_type, []).append(item)

    # Proportional allocation
    total = len(items)
    allocations: dict[str, int] = {}
    allocated = 0
    sorted_keys = sorted(strata.keys())
    for key in sorted_keys:
        share = max(1, round(len(strata[key]) / total * budget))
        allocations[key] = share
        allocated += share

    # Adjust for rounding — trim from largest or fill from largest with remaining capacity
    while allocated > budget:
        largest = max(sorted_keys, key=lambda k: allocations[k])
        allocations[largest] -= 1
        allocated -= 1
    while allocated < budget:
        # Give spare slots to strata that still have unsampled items
        candidates = [k for k in sorted_keys if allocations[k] < len(strata[k])]
        if not candidates:
            break
        largest = max(candidates, key=lambda k: len(strata[k]) - allocations[k])
        allocations[largest] += 1
        allocated += 1

    # Round-robin selection within each stratum
    selected: list[SecurityEvidenceModel] = []
    for key in sorted_keys:
        selected.extend(_round_robin_by_source(strata[key], allocations[key]))

    return selected


def _round_robin_by_source(
    items: list[SecurityEvidenceModel],
    count: int,
) -> list[SecurityEvidenceModel]:
    """Select items via round-robin across unique metadata.source values."""
    # Group by source, preserving insertion order
    by_source: dict[str, list[SecurityEvidenceModel]] = {}
    for item in items:
        by_source.setdefault(item.metadata.source, []).append(item)

    selected: list[SecurityEvidenceModel] = []
    source_iters = {src: iter(group) for src, group in by_source.items()}
    sources = list(by_source.keys())

    while len(selected) < count and source_iters:
        exhausted: list[str] = []
        for src in sources:
            if src not in source_iters:
                continue
            try:
                selected.append(next(source_iters[src]))
                if len(selected) >= count:
                    break
            except StopIteration:
                exhausted.append(src)
        for src in exhausted:
            del source_iters[src]

    return selected


def _build_strata(
    non_priority_items: list[SecurityEvidenceModel],
    selected_ids: set[str],
) -> list[StratumSummary]:
    """Build per-stratum summaries for the LLM prompt."""
    strata: dict[str, tuple[int, int]] = {}
    for item in non_priority_items:
        total, sampled = strata.get(item.evidence_type, (0, 0))
        strata[item.evidence_type] = (
            total + 1,
            sampled + (1 if item.id in selected_ids else 0),
        )
    return [
        StratumSummary(evidence_type=et, total=total, sampled=sampled)
        for et, (total, sampled) in sorted(strata.items())
    ]


def build_sampling_summary(result: StratifiedSampleResult) -> str:
    """Build a statistical summary section for the LLM prompt.

    Informs the LLM that it is seeing a representative subset, not the
    full evidence set, with per-stratum breakdown.

    Args:
        result: The sampling result containing strata and totals metadata.

    Returns:
        Formatted summary string for prompt injection.

    """
    lines = [
        "**EVIDENCE SAMPLING NOTICE:**",
        f"You are reviewing a representative sample of {len(result.items)} "
        f"out of {result.total_evidence} total evidence items.",
    ]

    if result.total_priority > 0:
        lines.append(
            f"All {result.total_priority} negative-polarity items are included "
            f"unconditionally (never sampled away)."
        )

    if result.strata:
        lines.append("Per-type breakdown (sampled / total):")
        for stratum in result.strata:
            lines.append(
                f"  - {stratum.evidence_type}: {stratum.sampled} / {stratum.total}"
            )

    lines.append(
        "Base your assessment on this sample. The omitted items have "
        "similar characteristics within each evidence type."
    )

    return "\n".join(lines)
