"""Tests for sampling strategies."""

from waivern_core.schemas.finding_types import BaseFindingEvidence, BaseFindingModel

from waivern_analysers_shared.llm_validation.sampling import (
    RandomSamplingStrategy,
)


class MockFinding(BaseFindingModel):
    """Simple finding for testing."""

    pass


def make_finding(finding_id: str) -> MockFinding:
    """Create a mock finding with required fields."""
    return MockFinding(
        id=finding_id,
        evidence=[BaseFindingEvidence(content="test evidence")],
        matched_patterns=["test_pattern"],
    )


class TestRandomSamplingStrategy:
    """Tests for RandomSamplingStrategy."""

    def test_random_sampling_takes_n_findings_when_group_has_more_than_n(self) -> None:
        """Should sample exactly N findings from groups with more than N findings."""
        # Arrange
        strategy = RandomSamplingStrategy(sample_size=3)
        groups = {
            "Payment": [make_finding(str(i)) for i in range(10)],
            "Analytics": [make_finding(str(i)) for i in range(10, 18)],
        }

        # Act
        result = strategy.sample(groups)

        # Assert
        assert len(result.sampled["Payment"]) == 3
        assert len(result.sampled["Analytics"]) == 3

    def test_random_sampling_uses_all_findings_when_group_has_fewer_than_sample_size(
        self,
    ) -> None:
        """Should use all findings as samples when group has fewer than sample_size."""
        # Arrange
        strategy = RandomSamplingStrategy(sample_size=5)
        groups = {
            "SmallGroup": [make_finding("1"), make_finding("2")],
        }

        # Act
        result = strategy.sample(groups)

        # Assert
        assert len(result.sampled["SmallGroup"]) == 2
        assert len(result.non_sampled["SmallGroup"]) == 0

    def test_random_sampling_preserves_all_findings(self) -> None:
        """Should preserve all findings across sampled and non_sampled (nothing lost)."""
        # Arrange
        strategy = RandomSamplingStrategy(sample_size=3)
        groups = {
            "Payment": [make_finding(str(i)) for i in range(10)],
            "Analytics": [make_finding(str(i)) for i in range(10, 18)],
        }

        # Act
        result = strategy.sample(groups)

        # Assert - all findings accounted for in each group
        for group_key, original_findings in groups.items():
            sampled_ids = {f.id for f in result.sampled[group_key]}
            non_sampled_ids = {f.id for f in result.non_sampled[group_key]}
            original_ids = {f.id for f in original_findings}

            # No overlap between sampled and non_sampled
            assert sampled_ids.isdisjoint(non_sampled_ids)
            # Union equals original
            assert sampled_ids | non_sampled_ids == original_ids
