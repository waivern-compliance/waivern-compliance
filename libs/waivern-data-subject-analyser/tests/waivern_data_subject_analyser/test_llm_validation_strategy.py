"""Tests for DataSubjectValidationStrategy.

Tests verify the strategy correctly uses LLMService to validate findings
and maps responses to LLMValidationOutcome.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail
from waivern_llm.v2 import (
    BatchingMode,
    ItemGroup,
    LLMCompletionResult,
    LLMService,
    SkipReason,
)

from waivern_data_subject_analyser.llm_validation_strategy import (
    DataSubjectValidationStrategy,
)
from waivern_data_subject_analyser.prompts import DataSubjectPromptBuilder
from waivern_data_subject_analyser.schemas.types import (
    DataSubjectIndicatorMetadata,
    DataSubjectIndicatorModel,
)


def _make_finding(
    subject_category: str = "Customer",
    pattern: str = "customer_id",
    source: str = "test_source",
) -> DataSubjectIndicatorModel:
    """Create a finding with minimal boilerplate."""
    return DataSubjectIndicatorModel(
        subject_category=subject_category,
        matched_patterns=[PatternMatchDetail(pattern=pattern, match_count=1)],
        confidence_score=80,
        evidence=[BaseFindingEvidence(content=f"Content: {pattern}")],
        metadata=DataSubjectIndicatorMetadata(source=source),
    )


# =============================================================================
# Fixtures
# =============================================================================


class TestDataSubjectValidationStrategy:
    """Test suite for DataSubjectValidationStrategy."""

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLMService."""
        service = Mock(spec=LLMService)
        service.complete = AsyncMock()
        return service

    @pytest.fixture
    def config(self) -> LLMValidationConfig:
        """Create standard LLM configuration."""
        return LLMValidationConfig(
            enable_llm_validation=True,
            llm_batch_size=10,
            llm_validation_mode="standard",
        )

    @pytest.fixture
    def sample_findings(self) -> list[DataSubjectIndicatorModel]:
        """Create two sample findings for testing."""
        return [
            _make_finding(
                "Customer", "customer_id", "mysql_database_(prod)_table_(customers)"
            ),
            _make_finding(
                "Employee", "employee_id", "mysql_database_(prod)_table_(employees)"
            ),
        ]

    # =========================================================================
    # Core Validation Behaviour
    # =========================================================================

    def test_calls_llm_service_complete_with_correct_args(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
    ) -> None:
        """Strategy calls LLMService.complete() with ItemGroup, prompt_builder, BatchingMode."""
        findings = [_make_finding("Customer"), _make_finding("Employee")]
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[LLMValidationResponseModel(results=[])],
            skipped=[],
        )
        strategy = DataSubjectValidationStrategy(mock_llm_service)

        strategy.validate_findings(findings, config, "test-run")

        mock_llm_service.complete.assert_called_once()
        call_kwargs = mock_llm_service.complete.call_args.kwargs

        # Verify ItemGroup
        groups = mock_llm_service.complete.call_args.args[0]
        assert len(groups) == 1
        assert isinstance(groups[0], ItemGroup)
        assert len(groups[0].items) == 2

        # Verify other args
        assert isinstance(call_kwargs["prompt_builder"], DataSubjectPromptBuilder)
        assert call_kwargs["response_model"] == LLMValidationResponseModel
        assert call_kwargs["batching_mode"] == BatchingMode.COUNT_BASED
        assert call_kwargs["run_id"] == "test-run"

    # =========================================================================
    # Response Mapping
    # =========================================================================

    def test_maps_true_positive_to_kept_findings(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
        sample_findings: list[DataSubjectIndicatorModel],
    ) -> None:
        """Findings marked TRUE_POSITIVE are in llm_validated_kept."""
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[
                LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=sample_findings[0].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid customer data",
                            recommended_action="keep",
                        ),
                        LLMValidationResultModel(
                            finding_id=sample_findings[1].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.85,
                            reasoning="Valid employee data",
                            recommended_action="keep",
                        ),
                    ]
                )
            ],
            skipped=[],
        )
        strategy = DataSubjectValidationStrategy(mock_llm_service)

        outcome = strategy.validate_findings(sample_findings, config, "test-run")

        assert len(outcome.llm_validated_kept) == 2
        assert outcome.llm_validated_removed == []
        assert outcome.llm_not_flagged == []
        kept_ids = {f.id for f in outcome.llm_validated_kept}
        assert kept_ids == {sample_findings[0].id, sample_findings[1].id}

    def test_filters_out_false_positive_findings(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
        sample_findings: list[DataSubjectIndicatorModel],
    ) -> None:
        """Findings marked FALSE_POSITIVE by LLM are removed."""
        # LLM marks first finding as FALSE_POSITIVE, second as TRUE_POSITIVE
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[
                LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=sample_findings[0].id,
                            validation_result="FALSE_POSITIVE",
                            confidence=0.95,
                            reasoning="Test fixture data",
                            recommended_action="discard",
                        ),
                        LLMValidationResultModel(
                            finding_id=sample_findings[1].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid employee data",
                            recommended_action="keep",
                        ),
                    ]
                )
            ],
            skipped=[],
        )
        strategy = DataSubjectValidationStrategy(mock_llm_service)

        outcome = strategy.validate_findings(sample_findings, config, "test-run")

        assert len(outcome.llm_validated_kept) == 1
        assert outcome.llm_validated_kept[0].id == sample_findings[1].id
        assert len(outcome.llm_validated_removed) == 1
        assert outcome.llm_validated_removed[0].id == sample_findings[0].id

    def test_keeps_findings_not_flagged_by_llm(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
        sample_findings: list[DataSubjectIndicatorModel],
    ) -> None:
        """Findings not mentioned in LLM response are kept (fail-safe)."""
        # LLM returns empty response - no findings flagged
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[LLMValidationResponseModel(results=[])],
            skipped=[],
        )
        strategy = DataSubjectValidationStrategy(mock_llm_service)

        outcome = strategy.validate_findings(sample_findings, config, "test-run")

        # Both findings kept via fail-safe (not_flagged)
        assert outcome.llm_validated_kept == []
        assert outcome.llm_validated_removed == []
        assert len(outcome.llm_not_flagged) == 2
        not_flagged_ids = {f.id for f in outcome.llm_not_flagged}
        assert not_flagged_ids == {sample_findings[0].id, sample_findings[1].id}

    # =========================================================================
    # Error Handling
    # =========================================================================

    def test_total_failure_returns_all_skipped(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
        sample_findings: list[DataSubjectIndicatorModel],
    ) -> None:
        """Exception from LLMService returns all findings as skipped with BATCH_ERROR."""
        mock_llm_service.complete.side_effect = Exception("LLM API unavailable")
        strategy = DataSubjectValidationStrategy(mock_llm_service)

        outcome = strategy.validate_findings(sample_findings, config, "test-run")

        # All findings should be skipped with BATCH_ERROR reason
        assert outcome.llm_validated_kept == []
        assert outcome.llm_validated_removed == []
        assert outcome.llm_not_flagged == []
        assert len(outcome.skipped) == 2
        skipped_ids = {s.finding.id for s in outcome.skipped}
        assert skipped_ids == {sample_findings[0].id, sample_findings[1].id}
        for skipped in outcome.skipped:
            assert skipped.reason == SkipReason.BATCH_ERROR
