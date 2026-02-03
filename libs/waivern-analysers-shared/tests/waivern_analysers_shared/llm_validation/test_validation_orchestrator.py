"""Tests for ValidationOrchestrator.

Business behaviour: Orchestrates the complete validation flow by composing
grouping, sampling, and LLM validation strategies. Applies group-level
decisions (Case A/B/C) based on sample validation results.
"""

from unittest.mock import Mock

import pytest
from waivern_core.schemas.finding_types import (
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    PatternMatchDetail,
)
from waivern_llm import BaseLLMService

from waivern_analysers_shared.llm_validation.models import (
    LLMValidationOutcome,
    SkippedFinding,
    SkipReason,
)
from waivern_analysers_shared.llm_validation.sampling import SamplingResult
from waivern_analysers_shared.llm_validation.validation_orchestrator import (
    ValidationOrchestrator,
)
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


def make_llm_service() -> Mock:
    """Create mock LLM service."""
    return Mock(spec=BaseLLMService)


# =============================================================================
# Core Orchestration
# =============================================================================


class TestCoreOrchestration:
    """Tests for basic orchestration flow."""

    def test_returns_empty_result_for_empty_findings(self) -> None:
        """Empty input returns empty result without calling LLM."""
        # Arrange
        mock_llm_strategy = Mock()
        orchestrator = ValidationOrchestrator(llm_strategy=mock_llm_strategy)
        config = make_config()
        llm_service = make_llm_service()

        # Act
        result = orchestrator.validate([], config, llm_service)

        # Assert
        assert result.kept_findings == []
        assert result.removed_findings == []
        assert result.removed_groups == []
        assert result.skipped_samples == []
        assert result.samples_validated == 0
        assert result.all_succeeded is True
        mock_llm_strategy.validate_findings.assert_not_called()

    def test_orchestrates_grouping_sampling_validation_flow(self) -> None:
        """Should call group → sample → validate in correct order."""
        # Arrange
        findings = [make_finding("1", "GroupA")]
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=findings,
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],
        )
        mock_grouping = Mock()
        mock_grouping.concern_key = "group"
        mock_grouping.group.return_value = {"GroupA": findings}
        mock_sampling = Mock()
        mock_sampling.sample.return_value = SamplingResult(
            sampled={"GroupA": findings},
            non_sampled={"GroupA": []},
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=mock_grouping,
            sampling_strategy=mock_sampling,
        )

        # Act
        orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - calls made in order
        mock_grouping.group.assert_called_once_with(findings)
        mock_sampling.sample.assert_called_once_with({"GroupA": findings})
        mock_llm_strategy.validate_findings.assert_called_once()

    def test_flattens_samples_for_single_llm_call(self) -> None:
        """All samples from all groups sent in one validate_findings call."""
        # Arrange: 2 groups, 2 samples each
        findings = [
            make_finding("a1", "GroupA"),
            make_finding("a2", "GroupA"),
            make_finding("b1", "GroupB"),
            make_finding("b2", "GroupB"),
        ]
        sampling_strategy = MockSamplingStrategy(
            sampled={
                "GroupA": [findings[0], findings[1]],
                "GroupB": [findings[2], findings[3]],
            },
            non_sampled={"GroupA": [], "GroupB": []},
        )
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=findings,
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=sampling_strategy,
        )

        # Act
        orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - single call with all 4 samples
        mock_llm_strategy.validate_findings.assert_called_once()
        call_args = mock_llm_strategy.validate_findings.call_args
        samples_sent = call_args[0][0]
        assert len(samples_sent) == 4
        assert set(f.id for f in samples_sent) == {"a1", "a2", "b1", "b2"}


# =============================================================================
# No Grouping Mode
# =============================================================================


class TestNoGroupingMode:
    """Tests for direct validation without grouping."""

    def test_validates_directly_when_no_grouping_strategy(self) -> None:
        """No grouping strategy → calls LLM directly, no group decisions."""
        # Arrange
        findings = [make_finding("1", "A"), make_finding("2", "B")]
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],
            llm_validated_removed=[findings[1]],
            llm_not_flagged=[],
            skipped=[],
        )
        orchestrator = ValidationOrchestrator(llm_strategy=mock_llm_strategy)
        config = make_config()
        llm_service = make_llm_service()

        # Act
        result = orchestrator.validate(findings, config, llm_service)

        # Assert - LLM strategy called directly with all findings
        mock_llm_strategy.validate_findings.assert_called_once_with(
            findings, config, llm_service, None
        )
        # Results mapped directly from LLMValidationOutcome
        assert result.kept_findings == [findings[0]]
        assert result.removed_findings == [findings[1]]
        assert result.samples_validated == 2
        assert result.all_succeeded is True

    def test_removed_groups_empty_when_no_grouping(self) -> None:
        """No grouping → removed_groups is always empty list."""
        # Arrange - even when all findings are FALSE_POSITIVE
        findings = [make_finding("1", "A"), make_finding("2", "B")]
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[],
            llm_validated_removed=findings,  # All removed
            llm_not_flagged=[],
            skipped=[],
        )
        orchestrator = ValidationOrchestrator(llm_strategy=mock_llm_strategy)
        config = make_config()
        llm_service = make_llm_service()

        # Act
        result = orchestrator.validate(findings, config, llm_service)

        # Assert - no group removal, just individual removal
        assert result.removed_groups == []
        assert result.removed_findings == findings

    def test_raises_error_when_sampling_without_grouping(self) -> None:
        """Sampling strategy without grouping strategy raises ValueError."""
        # Arrange
        mock_llm_strategy = Mock()
        mock_sampling_strategy = Mock()

        # Act & Assert
        with pytest.raises(ValueError, match="sampling_strategy requires grouping"):
            ValidationOrchestrator(
                llm_strategy=mock_llm_strategy,
                grouping_strategy=None,
                sampling_strategy=mock_sampling_strategy,
            )


# =============================================================================
# Group-Level Decisions (Case A/B/C)
# =============================================================================


class MockGroupingStrategy:
    """Mock grouping strategy that groups by 'group' attribute."""

    @property
    def concern_key(self) -> str:
        return "group"

    def group(self, findings: list[MockFinding]) -> dict[str, list[MockFinding]]:
        groups: dict[str, list[MockFinding]] = {}
        for finding in findings:
            groups.setdefault(finding.group, []).append(finding)
        return groups


class MockSamplingStrategy:
    """Mock sampling strategy with configurable results."""

    def __init__(
        self,
        sampled: dict[str, list[MockFinding]],
        non_sampled: dict[str, list[MockFinding]],
    ) -> None:
        self._sampled = sampled
        self._non_sampled = non_sampled

    def sample(
        self, groups: dict[str, list[MockFinding]]
    ) -> SamplingResult[MockFinding]:
        return SamplingResult(sampled=self._sampled, non_sampled=self._non_sampled)


class TestGroupLevelDecisions:
    """Tests for group-level validation decisions."""

    def test_case_c_keeps_entire_group_when_no_false_positives(self) -> None:
        """All samples TRUE_POSITIVE → keep all (sampled + non-sampled)."""
        # Arrange: 1 group with 3 findings, sample 1
        findings = [
            make_finding("1", "GroupA"),
            make_finding("2", "GroupA"),
            make_finding("3", "GroupA"),
        ]
        sampling_strategy = MockSamplingStrategy(
            sampled={"GroupA": [findings[0]]},
            non_sampled={"GroupA": [findings[1], findings[2]]},
        )
        # LLM marks sample as TRUE_POSITIVE (kept)
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=sampling_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - all 3 findings kept (1 sampled + 2 non-sampled)
        assert len(result.kept_findings) == 3
        assert set(f.id for f in result.kept_findings) == {"1", "2", "3"}
        assert result.removed_findings == []
        assert result.removed_groups == []
        assert result.samples_validated == 1
        assert result.all_succeeded is True

    def test_case_b_removes_only_false_positive_samples(self) -> None:
        """Mixed results → keep group, remove FPs, keep non-sampled."""
        # Arrange: 1 group with 4 findings, sample 2
        findings = [
            make_finding("1", "GroupA"),
            make_finding("2", "GroupA"),
            make_finding("3", "GroupA"),
            make_finding("4", "GroupA"),
        ]
        sampling_strategy = MockSamplingStrategy(
            sampled={"GroupA": [findings[0], findings[1]]},
            non_sampled={"GroupA": [findings[2], findings[3]]},
        )
        # LLM: one TRUE_POSITIVE, one FALSE_POSITIVE
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],
            llm_validated_removed=[findings[1]],
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=sampling_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - 3 kept (1 validated + 2 non-sampled), 1 removed (the FP)
        assert len(result.kept_findings) == 3
        assert set(f.id for f in result.kept_findings) == {"1", "3", "4"}
        assert len(result.removed_findings) == 1
        assert result.removed_findings[0].id == "2"
        assert result.removed_groups == []  # Group not removed (Case B, not A)
        assert result.samples_validated == 2  # Both samples were validated
        assert result.all_succeeded is True

    def test_case_a_removes_entire_group_when_all_samples_false_positive(self) -> None:
        """All samples FALSE_POSITIVE → remove entire group."""
        # Arrange: 1 group with 3 findings, sample 2, both FP
        findings = [
            make_finding("1", "GroupA"),
            make_finding("2", "GroupA"),
            make_finding("3", "GroupA"),
        ]
        sampling_strategy = MockSamplingStrategy(
            sampled={"GroupA": [findings[0], findings[1]]},
            non_sampled={"GroupA": [findings[2]]},
        )
        # LLM marks both samples as FALSE_POSITIVE
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[],
            llm_validated_removed=[findings[0], findings[1]],
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=sampling_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - entire group removed (including non-sampled finding)
        assert result.kept_findings == []
        assert len(result.removed_findings) == 3
        assert set(f.id for f in result.removed_findings) == {"1", "2", "3"}
        assert len(result.removed_groups) == 1
        assert result.samples_validated == 2
        assert result.all_succeeded is True

    def test_case_a_creates_removed_group_with_correct_metadata(self) -> None:
        """RemovedGroup has correct concern_key, counts, require_review=True."""
        # Arrange: group with known key and findings
        findings = [
            make_finding("1", "DocumentationExample"),
            make_finding("2", "DocumentationExample"),
            make_finding("3", "DocumentationExample"),
        ]
        sampling_strategy = MockSamplingStrategy(
            sampled={"DocumentationExample": [findings[0]]},
            non_sampled={"DocumentationExample": [findings[1], findings[2]]},
        )
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[],
            llm_validated_removed=[findings[0]],
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=sampling_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - RemovedGroup metadata
        assert len(result.removed_groups) == 1
        removed_group = result.removed_groups[0]
        assert removed_group.concern_key == "group"  # From MockGroupingStrategy
        assert removed_group.concern_value == "DocumentationExample"
        assert removed_group.findings_count == 3
        assert removed_group.samples_validated == 1
        assert removed_group.require_review is True
        assert "false positive" in removed_group.reason.lower()


# =============================================================================
# Skipped Samples Handling
# =============================================================================


class TestSkippedSamplesHandling:
    """Tests for handling samples that couldn't be validated."""

    def test_skipped_samples_excluded_from_group_decisions(self) -> None:
        """Only validated samples count for Case determination."""
        # Arrange: 2 samples, one skipped + one TRUE_POSITIVE
        # Without skipped exclusion, this would be "all FP" (Case A)
        # With exclusion, it's Case C (keep group)
        findings = [
            make_finding("1", "GroupA"),
            make_finding("2", "GroupA"),
            make_finding("3", "GroupA"),
        ]
        sampling_strategy = MockSamplingStrategy(
            sampled={"GroupA": [findings[0], findings[1]]},
            non_sampled={"GroupA": [findings[2]]},
        )
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],  # One TRUE_POSITIVE
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[SkippedFinding(findings[1], SkipReason.OVERSIZED)],  # One skipped
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=sampling_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - Group kept (skipped doesn't count as FP)
        # Kept: validated (1) + non-sampled (1) + skipped sample (1) = 3
        assert len(result.kept_findings) == 3
        assert result.removed_groups == []
        assert result.removed_findings == []

    def test_keeps_group_when_all_samples_skipped(self) -> None:
        """No validated samples → keep group (conservative)."""
        # Arrange: all samples skipped
        findings = [
            make_finding("1", "GroupA"),
            make_finding("2", "GroupA"),
        ]
        sampling_strategy = MockSamplingStrategy(
            sampled={"GroupA": [findings[0]]},
            non_sampled={"GroupA": [findings[1]]},
        )
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[SkippedFinding(findings[0], SkipReason.OVERSIZED)],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=sampling_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - conservative: keep group when no validated samples
        assert len(result.kept_findings) == 2
        assert result.removed_groups == []
        assert result.all_succeeded is False  # Skipped = not all succeeded

    def test_skipped_samples_included_in_result(self) -> None:
        """skipped_samples field populated with reasons."""
        # Arrange
        findings = [make_finding("1", "GroupA"), make_finding("2", "GroupA")]
        sampling_strategy = MockSamplingStrategy(
            sampled={"GroupA": [findings[0], findings[1]]},
            non_sampled={"GroupA": []},
        )
        mock_llm_strategy = Mock()
        skipped_finding = SkippedFinding(findings[1], SkipReason.OVERSIZED)
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[skipped_finding],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=sampling_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - skipped_samples populated
        assert len(result.skipped_samples) == 1
        assert result.skipped_samples[0].finding.id == "2"
        assert result.skipped_samples[0].reason == SkipReason.OVERSIZED


# =============================================================================
# Sampling Variations
# =============================================================================


class TestSamplingVariations:
    """Tests for different sampling configurations."""

    def test_validates_all_findings_when_no_sampling_strategy(self) -> None:
        """No sampling strategy → all findings in group are samples."""
        # Arrange: grouping but NO sampling strategy
        findings = [
            make_finding("1", "GroupA"),
            make_finding("2", "GroupA"),
            make_finding("3", "GroupA"),
        ]
        mock_llm_strategy = Mock()
        # All 3 findings should be sent as samples
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=findings,
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=None,  # No sampling
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - all 3 validated as samples
        assert len(result.kept_findings) == 3
        assert result.samples_validated == 3
        # LLM called with all findings
        call_args = mock_llm_strategy.validate_findings.call_args
        assert len(call_args[0][0]) == 3

    def test_non_sampled_findings_kept_when_group_kept(self) -> None:
        """Non-sampled findings included in kept_findings when group kept."""
        # Arrange: explicit test that non-sampled come through
        findings = [
            make_finding("1", "GroupA"),
            make_finding("2", "GroupA"),
            make_finding("3", "GroupA"),
        ]
        sampling_strategy = MockSamplingStrategy(
            sampled={"GroupA": [findings[0]]},  # Only sample finding 1
            non_sampled={"GroupA": [findings[1], findings[2]]},  # 2 and 3 not sampled
        )
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=sampling_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - non-sampled findings (2, 3) are in kept_findings
        kept_ids = {f.id for f in result.kept_findings}
        assert "2" in kept_ids  # Non-sampled
        assert "3" in kept_ids  # Non-sampled
        assert "1" in kept_ids  # Sampled and validated


# =============================================================================
# Multiple Groups
# =============================================================================


class TestMultipleGroups:
    """Tests for handling multiple groups."""

    def test_evaluates_each_group_independently(self) -> None:
        """Group A (Case C) + Group B (Case A) → correct outcomes per group."""
        # Arrange: 2 groups with different outcomes
        # Group A: TRUE_POSITIVE → keep
        # Group B: FALSE_POSITIVE → remove entire group
        findings_a = [make_finding("a1", "GroupA"), make_finding("a2", "GroupA")]
        findings_b = [make_finding("b1", "GroupB"), make_finding("b2", "GroupB")]
        all_findings = findings_a + findings_b

        sampling_strategy = MockSamplingStrategy(
            sampled={
                "GroupA": [findings_a[0]],
                "GroupB": [findings_b[0]],
            },
            non_sampled={
                "GroupA": [findings_a[1]],
                "GroupB": [findings_b[1]],
            },
        )
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings_a[0]],  # Group A sample: TRUE_POSITIVE
            llm_validated_removed=[findings_b[0]],  # Group B sample: FALSE_POSITIVE
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=sampling_strategy,
        )

        # Act
        result = orchestrator.validate(all_findings, make_config(), make_llm_service())

        # Assert - Group A kept (Case C), Group B removed (Case A)
        kept_ids = {f.id for f in result.kept_findings}
        removed_ids = {f.id for f in result.removed_findings}

        assert kept_ids == {"a1", "a2"}  # Group A: sampled + non-sampled
        assert removed_ids == {"b1", "b2"}  # Group B: entire group removed

        assert len(result.removed_groups) == 1
        assert result.removed_groups[0].concern_value == "GroupB"


# =============================================================================
# Marker Callback
# =============================================================================


class TestMarkerCallback:
    """Tests for the marker callback functionality.

    The marker callback allows analysers to mark findings that were actually
    validated by the LLM, distinguishing them from findings kept by inference
    (non-sampled) or skipped due to errors.
    """

    def test_marker_applied_to_validated_findings_only(self) -> None:
        """Marker is applied to llm_validated_kept and llm_not_flagged only."""
        # Arrange: 2 findings, one validated as kept, one not flagged
        findings = [make_finding("1", "A"), make_finding("2", "A")]

        # Track which findings get marked
        marked_ids: set[str] = set()

        def marker(finding: MockFinding) -> MockFinding:
            marked_ids.add(finding.id)
            return finding

        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],  # Explicitly validated
            llm_validated_removed=[],
            llm_not_flagged=[findings[1]],  # Not flagged = kept
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(llm_strategy=mock_llm_strategy)

        # Act
        orchestrator.validate(
            findings, make_config(), make_llm_service(), marker=marker
        )

        # Assert - both validated findings should be marked
        assert marked_ids == {"1", "2"}

    def test_marker_not_applied_to_skipped_findings(self) -> None:
        """Marker is NOT applied to findings skipped due to errors."""
        # Arrange
        findings = [make_finding("1", "A"), make_finding("2", "A")]

        marked_ids: set[str] = set()

        def marker(finding: MockFinding) -> MockFinding:
            marked_ids.add(finding.id)
            return finding

        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[
                SkippedFinding(finding=findings[1], reason=SkipReason.BATCH_ERROR)
            ],
        )

        orchestrator = ValidationOrchestrator(llm_strategy=mock_llm_strategy)

        # Act
        orchestrator.validate(
            findings, make_config(), make_llm_service(), marker=marker
        )

        # Assert - only validated finding is marked, not skipped one
        assert marked_ids == {"1"}

    def test_marker_not_applied_to_non_sampled_findings(self) -> None:
        """Marker is NOT applied to non-sampled findings (kept by inference)."""
        # Arrange: 3 findings in one group, only 1 sampled
        findings = [
            make_finding("1", "GroupA"),
            make_finding("2", "GroupA"),
            make_finding("3", "GroupA"),
        ]

        marked_ids: set[str] = set()

        def marker(finding: MockFinding) -> MockFinding:
            marked_ids.add(finding.id)
            return finding

        # Only finding "1" is sampled and validated
        sampling_strategy = MockSamplingStrategy(
            sampled={"GroupA": [findings[0]]},
            non_sampled={"GroupA": [findings[1], findings[2]]},
        )
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],  # Sample validated
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_llm_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=sampling_strategy,
        )

        # Act
        result = orchestrator.validate(
            findings, make_config(), make_llm_service(), marker=marker
        )

        # Assert - only sampled finding is marked
        assert marked_ids == {"1"}
        # But all 3 findings are kept (non-sampled kept by inference)
        assert len(result.kept_findings) == 3

    def test_no_marker_callback_still_works(self) -> None:
        """Validation works correctly when no marker callback is provided."""
        # Arrange
        findings = [make_finding("1", "A")]
        mock_llm_strategy = Mock()
        mock_llm_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],
        )
        orchestrator = ValidationOrchestrator(llm_strategy=mock_llm_strategy)

        # Act - no marker provided
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - validation still works
        assert len(result.kept_findings) == 1
        assert result.kept_findings[0].id == "1"


# =============================================================================
# Fallback Validation
# =============================================================================


class TestFallbackValidation:
    """Tests for fallback validation of skipped findings.

    When primary strategy skips findings (e.g., oversized source, missing content),
    a fallback strategy can be configured to attempt validation using a different
    approach (e.g., evidence-only instead of full source content).
    """

    def test_fallback_validates_skipped_findings_with_eligible_reason(self) -> None:
        """Fallback validates findings skipped with eligible reasons."""
        # Arrange: Primary skips finding due to oversized source,
        # fallback validates it as TRUE_POSITIVE
        findings = [make_finding("1", "A"), make_finding("2", "A")]

        mock_primary_strategy = Mock()
        mock_primary_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[SkippedFinding(findings[1], SkipReason.OVERSIZED)],
        )

        mock_fallback_strategy = Mock()
        mock_fallback_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[1]],  # Fallback validates it
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_primary_strategy,
            fallback_strategy=mock_fallback_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - both findings are kept (one by primary, one by fallback)
        assert len(result.kept_findings) == 2
        assert set(f.id for f in result.kept_findings) == {"1", "2"}
        # Fallback was called with the skipped finding
        mock_fallback_strategy.validate_findings.assert_called_once()
        fallback_call_args = mock_fallback_strategy.validate_findings.call_args[0][0]
        assert len(fallback_call_args) == 1
        assert fallback_call_args[0].id == "2"
        # No skipped findings in final result (fallback validated it)
        assert result.skipped_samples == []

    def test_fallback_not_called_when_no_skipped_findings(self) -> None:
        """Fallback strategy not invoked when primary validates all findings."""
        # Arrange: Primary validates all findings successfully
        findings = [make_finding("1", "A"), make_finding("2", "A")]

        mock_primary_strategy = Mock()
        mock_primary_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=findings,
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],  # No skipped findings
        )

        mock_fallback_strategy = Mock()

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_primary_strategy,
            fallback_strategy=mock_fallback_strategy,
        )

        # Act
        orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - fallback should NOT be called
        mock_fallback_strategy.validate_findings.assert_not_called()

    def test_fallback_not_called_for_batch_error_skips(self) -> None:
        """Findings skipped with SkipReason.BATCH_ERROR are NOT sent to fallback."""
        # Arrange: Primary skips finding due to SkipReason.BATCH_ERROR (LLM API failure)
        findings = [make_finding("1", "A")]

        mock_primary_strategy = Mock()
        mock_primary_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[
                SkippedFinding(findings[0], SkipReason.BATCH_ERROR)
            ],  # NOT eligible
        )

        mock_fallback_strategy = Mock()

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_primary_strategy,
            fallback_strategy=mock_fallback_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - fallback should NOT be called (SkipReason.BATCH_ERROR not eligible)
        mock_fallback_strategy.validate_findings.assert_not_called()
        # Finding remains skipped
        assert len(result.skipped_samples) == 1
        assert result.skipped_samples[0].reason == SkipReason.BATCH_ERROR

    def test_fallback_merges_kept_and_removed_correctly(self) -> None:
        """Fallback results correctly categorised as kept or removed."""
        # Arrange: Two findings skipped by primary, fallback keeps one, removes one
        findings = [
            make_finding("1", "A"),  # Primary keeps
            make_finding("2", "A"),  # Primary skips, fallback keeps
            make_finding("3", "A"),  # Primary skips, fallback removes
        ]

        mock_primary_strategy = Mock()
        mock_primary_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[
                SkippedFinding(findings[1], SkipReason.OVERSIZED),
                SkippedFinding(findings[2], SkipReason.OVERSIZED),
            ],
        )

        mock_fallback_strategy = Mock()
        mock_fallback_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[1]],  # TRUE_POSITIVE
            llm_validated_removed=[findings[2]],  # FALSE_POSITIVE
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_primary_strategy,
            fallback_strategy=mock_fallback_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - correct categorisation
        assert len(result.kept_findings) == 2
        assert set(f.id for f in result.kept_findings) == {"1", "2"}
        assert len(result.removed_findings) == 1
        assert result.removed_findings[0].id == "3"
        assert result.skipped_samples == []

    def test_fallback_keeps_findings_skipped_by_both_strategies(self) -> None:
        """Findings skipped by both strategies remain in skipped list."""
        # Arrange: Primary skips finding, fallback also skips it
        findings = [make_finding("1", "A")]

        mock_primary_strategy = Mock()
        mock_primary_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[SkippedFinding(findings[0], SkipReason.OVERSIZED)],
        )

        mock_fallback_strategy = Mock()
        mock_fallback_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[
                SkippedFinding(findings[0], SkipReason.BATCH_ERROR)
            ],  # Fallback also fails
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_primary_strategy,
            fallback_strategy=mock_fallback_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - finding remains skipped (with fallback's reason)
        assert len(result.skipped_samples) == 1
        assert result.skipped_samples[0].finding.id == "1"
        assert (
            result.skipped_samples[0].reason == SkipReason.BATCH_ERROR
        )  # Fallback's reason
        # Finding is still kept (conservative - skipped findings are kept)
        assert len(result.kept_findings) == 0  # Without grouping, skipped not in kept
        assert result.all_succeeded is False

    def test_fallback_with_grouping_influences_group_decisions(self) -> None:
        """Fallback-validated findings participate in group decisions.

        Scenario: Group has 2 samples. Primary skips one (oversized), validates
        other as FALSE_POSITIVE. Without fallback, group would have 1 FP out of 1
        validated = Case A (remove group). With fallback validating the skipped
        one as TRUE_POSITIVE, group has 1 TP + 1 FP = Case B (keep group).
        """
        # Arrange
        findings = [
            make_finding("1", "GroupA"),
            make_finding("2", "GroupA"),
            make_finding("3", "GroupA"),  # Non-sampled
        ]
        sampling_strategy = MockSamplingStrategy(
            sampled={"GroupA": [findings[0], findings[1]]},
            non_sampled={"GroupA": [findings[2]]},
        )

        mock_primary_strategy = Mock()
        mock_primary_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[],
            llm_validated_removed=[findings[1]],  # FP
            llm_not_flagged=[],
            skipped=[SkippedFinding(findings[0], SkipReason.OVERSIZED)],
        )

        mock_fallback_strategy = Mock()
        mock_fallback_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],  # TP - changes group decision!
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_primary_strategy,
            grouping_strategy=MockGroupingStrategy(),
            sampling_strategy=sampling_strategy,
            fallback_strategy=mock_fallback_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - Case B: keep group (1 TP + 1 FP), remove only FP sample
        assert len(result.removed_groups) == 0  # Group NOT removed
        assert len(result.removed_findings) == 1
        assert result.removed_findings[0].id == "2"  # Only the FP
        # Kept: fallback-validated (1) + non-sampled (1) = 2
        assert len(result.kept_findings) == 2
        assert set(f.id for f in result.kept_findings) == {"1", "3"}

    def test_marker_applied_to_fallback_validated_findings(self) -> None:
        """Marker callback applied to findings validated by fallback."""
        # Arrange
        findings = [make_finding("1", "A"), make_finding("2", "A")]

        marked_ids: set[str] = set()

        def marker(finding: MockFinding) -> MockFinding:
            marked_ids.add(finding.id)
            return finding

        mock_primary_strategy = Mock()
        mock_primary_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0]],  # Primary validates
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[SkippedFinding(findings[1], SkipReason.OVERSIZED)],
        )

        mock_fallback_strategy = Mock()
        mock_fallback_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[1]],  # Fallback validates
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_primary_strategy,
            fallback_strategy=mock_fallback_strategy,
        )

        # Act
        orchestrator.validate(
            findings, make_config(), make_llm_service(), marker=marker
        )

        # Assert - both findings are marked (primary and fallback validated)
        assert marked_ids == {"1", "2"}

    def test_mixed_skip_reasons_only_eligible_sent_to_fallback(self) -> None:
        """Only findings with eligible skip reasons are sent to fallback."""
        # Arrange: Mix of eligible and ineligible skip reasons
        findings = [
            make_finding("1", "A"),  # SkipReason.OVERSIZED - eligible
            make_finding("2", "A"),  # SkipReason.MISSING_CONTENT - eligible
            make_finding("3", "A"),  # SkipReason.BATCH_ERROR - NOT eligible
        ]

        mock_primary_strategy = Mock()
        mock_primary_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[
                SkippedFinding(findings[0], SkipReason.OVERSIZED),
                SkippedFinding(findings[1], SkipReason.MISSING_CONTENT),
                SkippedFinding(findings[2], SkipReason.BATCH_ERROR),
            ],
        )

        mock_fallback_strategy = Mock()
        mock_fallback_strategy.validate_findings.return_value = LLMValidationOutcome(
            llm_validated_kept=[findings[0], findings[1]],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=mock_primary_strategy,
            fallback_strategy=mock_fallback_strategy,
        )

        # Act
        result = orchestrator.validate(findings, make_config(), make_llm_service())

        # Assert - only eligible findings sent to fallback
        mock_fallback_strategy.validate_findings.assert_called_once()
        fallback_call_args = mock_fallback_strategy.validate_findings.call_args[0][0]
        assert len(fallback_call_args) == 2
        assert set(f.id for f in fallback_call_args) == {"1", "2"}

        # SkipReason.BATCH_ERROR finding remains skipped
        assert len(result.skipped_samples) == 1
        assert result.skipped_samples[0].finding.id == "3"
        assert result.skipped_samples[0].reason == SkipReason.BATCH_ERROR

        # Eligible findings are now kept
        assert len(result.kept_findings) == 2
        assert set(f.id for f in result.kept_findings) == {"1", "2"}
