"""Tests for stratified evidence sampling."""

from waivern_schemas.security_evidence import SecurityEvidenceModel

from waivern_iso27001_control_assessor.sampling import (
    build_sampling_summary,
    stratified_sample,
)


def _item(
    evidence_type: str = "CODE",
    polarity: str = "positive",
    source: str = "file.py",
    domain: str = "encryption",
) -> SecurityEvidenceModel:
    """Build a minimal SecurityEvidenceModel for sampling tests."""
    return SecurityEvidenceModel(
        metadata={"source": source},
        evidence_type=evidence_type,
        security_domain=domain,
        polarity=polarity,
        confidence=0.9,
        description=f"{evidence_type} evidence from {source}",
    )


class TestStratifiedSample:
    """Tests for stratified_sample() — core sampling algorithm."""

    def test_returns_all_items_when_within_budget(self) -> None:
        """Budget >= total items → was_sampled=False, all items returned."""
        items = [_item(), _item(source="other.py"), _item(evidence_type="CONFIG")]

        result = stratified_sample(items, max_items=10)

        assert result.was_sampled is False
        assert len(result.items) == 3

    def test_negative_items_always_included(self) -> None:
        """Negative polarity items are never excluded regardless of budget."""
        neg1 = _item(polarity="negative", source="vuln.py")
        neg2 = _item(polarity="negative", source="weak.py")
        positives = [_item(source=f"file{i}.py") for i in range(10)]

        result = stratified_sample([neg1, neg2, *positives], max_items=5)

        assert result.was_sampled is True
        result_ids = {i.id for i in result.items}
        assert neg1.id in result_ids
        assert neg2.id in result_ids
        assert len(result.items) == 5

    def test_proportional_allocation_across_evidence_types(self) -> None:
        """Budget distributed proportionally across CODE/CONFIG strata."""
        # 8 CODE items, 2 CONFIG items → budget of 5 should give ~4 CODE, ~1 CONFIG
        code_items = [_item(evidence_type="CODE", source=f"c{i}.py") for i in range(8)]
        config_items = [
            _item(evidence_type="CONFIG", source=f"cfg{i}.yaml") for i in range(2)
        ]

        result = stratified_sample([*code_items, *config_items], max_items=5)

        assert result.was_sampled is True
        sampled_code = [i for i in result.items if i.evidence_type == "CODE"]
        sampled_config = [i for i in result.items if i.evidence_type == "CONFIG"]
        # Proportional: CODE gets 80% of 5 = 4, CONFIG gets 20% of 5 = 1
        assert len(sampled_code) == 4
        assert len(sampled_config) == 1

    def test_negative_items_exceeding_budget_still_included(self) -> None:
        """Negatives alone > budget → all negatives kept, was_sampled=True."""
        negatives = [_item(polarity="negative", source=f"v{i}.py") for i in range(5)]
        positives = [_item(source=f"ok{i}.py") for i in range(3)]

        result = stratified_sample([*negatives, *positives], max_items=3)

        assert result.was_sampled is True
        # All 5 negatives included even though budget is 3
        neg_ids = {n.id for n in negatives}
        result_ids = {i.id for i in result.items}
        assert neg_ids.issubset(result_ids)
        assert len(result.items) == 5  # Only negatives, no budget for positives

    def test_round_robin_source_diversity(self) -> None:
        """Within a stratum, items selected via round-robin across sources."""
        # 3 items from source A, 3 from source B — budget 3 should pick from both
        items = [
            _item(source="a.py"),
            _item(source="a.py"),
            _item(source="a.py"),
            _item(source="b.py"),
            _item(source="b.py"),
            _item(source="b.py"),
        ]

        result = stratified_sample(items, max_items=3)

        sources = [i.metadata.source for i in result.items]
        # Round-robin: should pick from both sources, not all from one
        assert "a.py" in sources
        assert "b.py" in sources


class TestBuildSamplingSummary:
    """Tests for build_sampling_summary() — LLM prompt summary."""

    def test_sampling_summary_includes_strata_breakdown(self) -> None:
        """Formatted string has per-stratum total and sampled counts."""
        code_items = [_item(evidence_type="CODE", source=f"c{i}.py") for i in range(8)]
        config_items = [
            _item(evidence_type="CONFIG", source=f"cfg{i}.yaml") for i in range(2)
        ]

        result = stratified_sample([*code_items, *config_items], max_items=5)
        summary = build_sampling_summary(result, total_evidence=10, total_priority=0)

        assert "CODE" in summary
        assert "CONFIG" in summary
        # Should mention total and sampled counts
        assert "10" in summary  # total evidence
        assert "5" in summary  # sampled count
