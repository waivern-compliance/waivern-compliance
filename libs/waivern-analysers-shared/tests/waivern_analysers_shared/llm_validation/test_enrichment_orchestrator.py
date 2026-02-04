"""Tests for EnrichmentOrchestrator.

Business behaviour: Orchestrates the enrichment flow by composing
grouping, sampling, and enrichment strategies. Unlike ValidationOrchestrator,
it does not make group-level decisions - it returns results for consumer
interpretation.

Reference: .local/plans/step-14a-enrichment-orchestrator-spec.md
"""

from unittest.mock import Mock

from waivern_core.schemas.finding_types import (
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    PatternMatchDetail,
)

from waivern_analysers_shared.llm_validation.sampling import SamplingResult
from waivern_analysers_shared.types import LLMValidationConfig


class MockFinding(BaseFindingModel[BaseFindingMetadata]):
    """Simple finding for testing with group attribute."""

    group: str


def make_finding(finding_id: str, group: str) -> MockFinding:
    """Create a mock finding with required fields."""
    return MockFinding(
        id=finding_id,
        group=group,
        evidence=[BaseFindingEvidence(content=f"Evidence for {finding_id}")],
        matched_patterns=[PatternMatchDetail(pattern="test_pattern", match_count=1)],
        metadata=BaseFindingMetadata(source="test_source"),
    )


def make_config() -> LLMValidationConfig:
    """Create default test config."""
    return LLMValidationConfig(
        enable_llm_validation=True,
        llm_batch_size=10,
    )


# =============================================================================
# Core Orchestration
# =============================================================================


class TestCoreOrchestration:
    """Tests for basic orchestration flow."""

    def test_returns_empty_result_for_empty_findings(self) -> None:
        """Empty input returns empty result without calling strategy."""
        # Arrange
        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        mock_strategy = Mock()
        orchestrator: EnrichmentOrchestrator[MockFinding, str] = EnrichmentOrchestrator(
            enrichment_strategy=mock_strategy,
        )

        # Act
        result = orchestrator.enrich(
            findings=[],
            config=make_config(),
            run_id="test-run",
        )

        # Assert
        assert result.all_findings == []
        assert result.strategy_result is None
        assert result.groups is None
        assert result.skipped == []
        assert result.all_succeeded is True
        mock_strategy.enrich.assert_not_called()

    def test_calls_strategy_with_all_findings_when_no_grouping_or_sampling(
        self,
    ) -> None:
        """No grouping or sampling → all findings sent to strategy."""
        # Arrange
        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        findings = [make_finding("1", "A"), make_finding("2", "B")]
        mock_strategy = Mock()
        mock_strategy.enrich.return_value = "enrichment_result"
        config = make_config()

        orchestrator: EnrichmentOrchestrator[MockFinding, str] = EnrichmentOrchestrator(
            enrichment_strategy=mock_strategy,
        )

        # Act
        orchestrator.enrich(findings=findings, config=config, run_id="test-run")

        # Assert - strategy called with all findings
        mock_strategy.enrich.assert_called_once_with(findings, config, "test-run")

    def test_returns_strategy_result_in_enrichment_result(self) -> None:
        """Strategy result passed through unchanged in EnrichmentResult."""
        # Arrange
        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        findings = [make_finding("1", "A")]
        expected_result = {"risk_modifiers": ["high_risk"]}
        mock_strategy = Mock()
        mock_strategy.enrich.return_value = expected_result

        orchestrator: EnrichmentOrchestrator[MockFinding, dict[str, list[str]]] = (
            EnrichmentOrchestrator(
                enrichment_strategy=mock_strategy,
            )
        )

        # Act
        result = orchestrator.enrich(
            findings=findings, config=make_config(), run_id="test-run"
        )

        # Assert - strategy result passed through unchanged
        assert result.strategy_result is expected_result

    def test_returns_all_findings_in_result(self) -> None:
        """all_findings contains the original input findings."""
        # Arrange
        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        findings = [make_finding("1", "A"), make_finding("2", "B")]
        mock_strategy = Mock()
        mock_strategy.enrich.return_value = "result"

        orchestrator: EnrichmentOrchestrator[MockFinding, str] = EnrichmentOrchestrator(
            enrichment_strategy=mock_strategy,
        )

        # Act
        result = orchestrator.enrich(
            findings=findings, config=make_config(), run_id="test-run"
        )

        # Assert
        assert result.all_findings == findings


# =============================================================================
# Grouping Behaviour
# =============================================================================


class TestGroupingBehaviour:
    """Tests for grouping strategy integration."""

    def test_groups_findings_using_grouping_strategy(self) -> None:
        """Grouping strategy is called with input findings."""
        # Arrange
        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        findings = [make_finding("1", "A"), make_finding("2", "B")]
        mock_strategy = Mock()
        mock_strategy.enrich.return_value = "result"
        mock_grouping = Mock()
        mock_grouping.group.return_value = {"A": [findings[0]], "B": [findings[1]]}

        orchestrator: EnrichmentOrchestrator[MockFinding, str] = EnrichmentOrchestrator(
            enrichment_strategy=mock_strategy,
            grouping_strategy=mock_grouping,
        )

        # Act
        orchestrator.enrich(findings=findings, config=make_config(), run_id="test-run")

        # Assert
        mock_grouping.group.assert_called_once_with(findings)

    def test_returns_groups_in_result_when_grouping_used(self) -> None:
        """groups dict is populated in result when grouping enabled."""
        # Arrange
        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        findings = [make_finding("1", "A"), make_finding("2", "B")]
        expected_groups = {"A": [findings[0]], "B": [findings[1]]}
        mock_strategy = Mock()
        mock_strategy.enrich.return_value = "result"
        mock_grouping = Mock()
        mock_grouping.group.return_value = expected_groups

        orchestrator: EnrichmentOrchestrator[MockFinding, str] = EnrichmentOrchestrator(
            enrichment_strategy=mock_strategy,
            grouping_strategy=mock_grouping,
        )

        # Act
        result = orchestrator.enrich(
            findings=findings, config=make_config(), run_id="test-run"
        )

        # Assert
        assert result.groups == expected_groups

    def test_groups_is_none_when_no_grouping_strategy(self) -> None:
        """groups is None when no grouping strategy provided."""
        # Arrange
        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        findings = [make_finding("1", "A")]
        mock_strategy = Mock()
        mock_strategy.enrich.return_value = "result"

        orchestrator: EnrichmentOrchestrator[MockFinding, str] = EnrichmentOrchestrator(
            enrichment_strategy=mock_strategy,
        )

        # Act
        result = orchestrator.enrich(
            findings=findings, config=make_config(), run_id="test-run"
        )

        # Assert
        assert result.groups is None


# =============================================================================
# Sampling Behaviour
# =============================================================================


class TestSamplingBehaviour:
    """Tests for sampling strategy integration."""

    def test_samples_findings_using_sampling_strategy(self) -> None:
        """Sampling strategy is called with groups."""
        # Arrange
        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        findings = [
            make_finding("1", "A"),
            make_finding("2", "A"),
            make_finding("3", "B"),
        ]
        mock_strategy = Mock()
        mock_strategy.enrich.return_value = "result"
        mock_grouping = Mock()
        groups = {"A": [findings[0], findings[1]], "B": [findings[2]]}
        mock_grouping.group.return_value = groups
        mock_sampling = Mock()
        mock_sampling.sample.return_value = SamplingResult(
            sampled={"A": [findings[0]], "B": [findings[2]]},
            non_sampled={"A": [findings[1]], "B": []},
        )

        orchestrator: EnrichmentOrchestrator[MockFinding, str] = EnrichmentOrchestrator(
            enrichment_strategy=mock_strategy,
            grouping_strategy=mock_grouping,
            sampling_strategy=mock_sampling,
        )

        # Act
        orchestrator.enrich(findings=findings, config=make_config(), run_id="test-run")

        # Assert - sampling called with groups
        mock_sampling.sample.assert_called_once_with(groups)

    def test_only_sampled_findings_sent_to_strategy(self) -> None:
        """Strategy receives only sampled subset, not all findings."""
        # Arrange
        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        findings = [
            make_finding("1", "A"),
            make_finding("2", "A"),
            make_finding("3", "B"),
        ]
        mock_strategy = Mock()
        mock_strategy.enrich.return_value = "result"
        mock_grouping = Mock()
        mock_grouping.group.return_value = {
            "A": [findings[0], findings[1]],
            "B": [findings[2]],
        }
        mock_sampling = Mock()
        # Sampling returns 2 of 3 findings
        mock_sampling.sample.return_value = SamplingResult(
            sampled={"A": [findings[0]], "B": [findings[2]]},
            non_sampled={"A": [findings[1]], "B": []},
        )
        config = make_config()

        orchestrator: EnrichmentOrchestrator[MockFinding, str] = EnrichmentOrchestrator(
            enrichment_strategy=mock_strategy,
            grouping_strategy=mock_grouping,
            sampling_strategy=mock_sampling,
        )

        # Act
        orchestrator.enrich(findings=findings, config=config, run_id="test-run")

        # Assert - strategy called with sampled findings only (flattened)
        mock_strategy.enrich.assert_called_once()
        call_args = mock_strategy.enrich.call_args[0]
        sent_findings = call_args[0]
        assert len(sent_findings) == 2
        assert set(f.id for f in sent_findings) == {"1", "3"}

    def test_all_findings_preserved_when_sampling(self) -> None:
        """all_findings still contains all originals even after sampling."""
        # Arrange
        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        findings = [make_finding("1", "A"), make_finding("2", "A")]
        mock_strategy = Mock()
        mock_strategy.enrich.return_value = "result"
        mock_grouping = Mock()
        mock_grouping.group.return_value = {"A": findings}
        mock_sampling = Mock()
        mock_sampling.sample.return_value = SamplingResult(
            sampled={"A": [findings[0]]},
            non_sampled={"A": [findings[1]]},
        )

        orchestrator: EnrichmentOrchestrator[MockFinding, str] = EnrichmentOrchestrator(
            enrichment_strategy=mock_strategy,
            grouping_strategy=mock_grouping,
            sampling_strategy=mock_sampling,
        )

        # Act
        result = orchestrator.enrich(
            findings=findings, config=make_config(), run_id="test-run"
        )

        # Assert - all_findings has all originals
        assert result.all_findings == findings

    def test_sampling_without_grouping_treats_as_single_group(self) -> None:
        """Sampling without grouping uses implicit single group."""
        # Arrange
        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        findings = [make_finding("1", "A"), make_finding("2", "B")]
        mock_strategy = Mock()
        mock_strategy.enrich.return_value = "result"
        mock_sampling = Mock()
        mock_sampling.sample.return_value = SamplingResult(
            sampled={"_all": [findings[0]]},
            non_sampled={"_all": [findings[1]]},
        )

        orchestrator: EnrichmentOrchestrator[MockFinding, str] = EnrichmentOrchestrator(
            enrichment_strategy=mock_strategy,
            sampling_strategy=mock_sampling,  # No grouping strategy
        )

        # Act
        orchestrator.enrich(findings=findings, config=make_config(), run_id="test-run")

        # Assert - sampling called with implicit single group
        mock_sampling.sample.assert_called_once_with({"_all": findings})


# =============================================================================
# Failure Handling
# =============================================================================


class TestFailureHandling:
    """Tests for strategy failure scenarios."""

    def test_returns_skipped_when_strategy_raises(self) -> None:
        """When strategy raises, all findings are marked as skipped."""
        # Arrange
        from waivern_llm.v2 import SkipReason

        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        findings = [make_finding("1", "A"), make_finding("2", "B")]
        mock_strategy = Mock()
        mock_strategy.enrich.side_effect = RuntimeError("LLM API error")

        orchestrator: EnrichmentOrchestrator[MockFinding, str] = EnrichmentOrchestrator(
            enrichment_strategy=mock_strategy,
        )

        # Act
        result = orchestrator.enrich(
            findings=findings, config=make_config(), run_id="test-run"
        )

        # Assert
        assert result.strategy_result is None
        assert len(result.skipped) == 2
        assert all(s.reason == SkipReason.BATCH_ERROR for s in result.skipped)
        assert result.all_succeeded is False

    def test_all_succeeded_true_when_no_errors(self) -> None:
        """all_succeeded is True when strategy succeeds."""
        # Arrange
        from waivern_analysers_shared.llm_validation.enrichment_orchestrator import (
            EnrichmentOrchestrator,
        )

        findings = [make_finding("1", "A")]
        mock_strategy = Mock()
        mock_strategy.enrich.return_value = "result"

        orchestrator: EnrichmentOrchestrator[MockFinding, str] = EnrichmentOrchestrator(
            enrichment_strategy=mock_strategy,
        )

        # Act
        result = orchestrator.enrich(
            findings=findings, config=make_config(), run_id="test-run"
        )

        # Assert
        assert result.skipped == []
        assert result.all_succeeded is True
