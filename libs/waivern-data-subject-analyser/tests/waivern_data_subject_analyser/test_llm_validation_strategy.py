"""Tests for DataSubjectValidationStrategy."""

from unittest.mock import Mock

import pytest
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core.schemas import BaseFindingEvidence
from waivern_llm import AnthropicLLMService

from waivern_data_subject_analyser.llm_validation_strategy import (
    DataSubjectValidationStrategy,
)
from waivern_data_subject_analyser.schemas.types import (
    DataSubjectIndicatorMetadata,
    DataSubjectIndicatorModel,
)

# =============================================================================
# Test Helpers
# =============================================================================


def _make_finding(
    subject_category: str = "Customer",
    pattern: str = "customer_id",
    source: str = "test_source",
) -> DataSubjectIndicatorModel:
    """Create a finding with minimal boilerplate."""
    return DataSubjectIndicatorModel(
        subject_category=subject_category,
        matched_patterns=[pattern],
        confidence_score=80,
        evidence=[BaseFindingEvidence(content=f"Content: {pattern}")],
        metadata=DataSubjectIndicatorMetadata(source=source),
    )


def _make_false_positive_result(finding_id: str) -> LLMValidationResultModel:
    """Create a FALSE_POSITIVE validation result."""
    return LLMValidationResultModel(
        finding_id=finding_id,
        validation_result="FALSE_POSITIVE",
        confidence=0.9,
        reasoning="Test fixture data",
        recommended_action="discard",
    )


def _make_response(
    results: list[LLMValidationResultModel],
) -> LLMValidationResponseModel:
    """Wrap results in a response model."""
    return LLMValidationResponseModel(results=results)


# =============================================================================
# Test Class
# =============================================================================


class TestDataSubjectValidationStrategy:
    """Test suite for DataSubjectValidationStrategy."""

    # -------------------------------------------------------------------------
    # Fixtures
    # -------------------------------------------------------------------------

    @pytest.fixture
    def strategy(self) -> DataSubjectValidationStrategy:
        """Create strategy instance."""
        return DataSubjectValidationStrategy()

    @pytest.fixture
    def config(self) -> LLMValidationConfig:
        """Create standard LLM configuration."""
        return LLMValidationConfig(
            enable_llm_validation=True,
            llm_batch_size=10,
            llm_validation_mode="standard",
        )

    @pytest.fixture
    def llm_service(self) -> Mock:
        """Create mock LLM service."""
        return Mock(spec=AnthropicLLMService)

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

    # -------------------------------------------------------------------------
    # Core Validation Behaviour
    # -------------------------------------------------------------------------

    def test_returns_empty_outcome_when_no_findings_provided(
        self,
        strategy: DataSubjectValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """Empty input returns empty outcome without calling LLM."""
        outcome = strategy.validate_findings([], config, llm_service)

        assert outcome.kept_findings == []
        assert outcome.validation_succeeded is True
        llm_service.invoke_with_structured_output.assert_not_called()

    def test_filters_out_false_positive_findings(
        self,
        strategy: DataSubjectValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[DataSubjectIndicatorModel],
    ) -> None:
        """Findings marked FALSE_POSITIVE by LLM are removed."""
        # LLM marks first finding as FALSE_POSITIVE, doesn't mention second
        llm_service.invoke_with_structured_output.return_value = _make_response(
            [_make_false_positive_result(sample_findings[0].id)]
        )

        outcome = strategy.validate_findings(sample_findings, config, llm_service)

        # Only second finding kept (first was FALSE_POSITIVE, second not flagged)
        assert len(outcome.kept_findings) == 1
        assert outcome.kept_findings[0].subject_category == "Employee"
        assert outcome.validation_succeeded is True
        assert len(outcome.llm_validated_removed) == 1

    def test_keeps_findings_not_flagged_by_llm(
        self,
        strategy: DataSubjectValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[DataSubjectIndicatorModel],
    ) -> None:
        """Findings not mentioned in LLM response are kept (fail-safe)."""
        # LLM returns empty response - no findings flagged
        llm_service.invoke_with_structured_output.return_value = _make_response([])

        outcome = strategy.validate_findings(sample_findings, config, llm_service)

        # Both findings kept as not_flagged
        assert len(outcome.kept_findings) == 2
        assert outcome.validation_succeeded is True
        assert len(outcome.llm_not_flagged) == 2

    def test_returns_same_finding_instances_not_copies(
        self,
        strategy: DataSubjectValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[DataSubjectIndicatorModel],
    ) -> None:
        """Returned findings are the same object instances as input."""
        # LLM returns empty response - all findings kept
        llm_service.invoke_with_structured_output.return_value = _make_response([])

        outcome = strategy.validate_findings(sample_findings, config, llm_service)

        # Same instances, not copies (order may differ due to internal set iteration)
        assert set(id(f) for f in outcome.kept_findings) == set(
            id(f) for f in sample_findings
        )

    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    def test_returns_original_findings_as_skipped_on_llm_error(
        self,
        strategy: DataSubjectValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[DataSubjectIndicatorModel],
    ) -> None:
        """On LLM error, return original findings as skipped."""
        llm_service.invoke_with_structured_output.side_effect = Exception(
            "LLM service unavailable"
        )

        outcome = strategy.validate_findings(sample_findings, config, llm_service)

        # Findings are kept but marked as skipped
        assert len(outcome.kept_findings) == len(sample_findings)
        assert outcome.validation_succeeded is False
        assert len(outcome.skipped) == len(sample_findings)

    # -------------------------------------------------------------------------
    # Batch Processing
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("batch_size", "expected_calls"),
        [
            (1, 3),  # 3 findings, batch size 1 = 3 calls
            (2, 2),  # 3 findings, batch size 2 = 2 calls (2+1)
            (3, 1),  # 3 findings, batch size 3 = 1 call
            (5, 1),  # 3 findings, batch size 5 = 1 call (larger than count)
        ],
    )
    def test_processes_findings_in_batches(
        self,
        strategy: DataSubjectValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        batch_size: int,
        expected_calls: int,
    ) -> None:
        """Findings are batched according to config."""
        findings = [_make_finding("Customer", f"customer_{i}") for i in range(3)]
        config.llm_batch_size = batch_size

        # Return empty response for each batch (all findings kept as not_flagged)
        llm_service.invoke_with_structured_output.return_value = _make_response([])

        outcome = strategy.validate_findings(findings, config, llm_service)

        assert len(outcome.kept_findings) == 3
        assert llm_service.invoke_with_structured_output.call_count == expected_calls
        assert outcome.validation_succeeded is True

    def test_continues_processing_after_batch_error(
        self,
        strategy: DataSubjectValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """If one batch fails, continue with remaining batches."""
        findings = [_make_finding("Customer", f"customer_{i}") for i in range(4)]
        config.llm_batch_size = 2

        # First batch fails, second succeeds
        llm_service.invoke_with_structured_output.side_effect = [
            Exception("Batch 1 failed"),
            _make_response([]),  # Second batch returns empty (all kept)
        ]

        outcome = strategy.validate_findings(findings, config, llm_service)

        # All 4 findings kept (2 from failed batch as skipped, 2 not flagged)
        assert len(outcome.kept_findings) == 4
        assert outcome.validation_succeeded is False  # Not all batches succeeded
        assert len(outcome.skipped) == 2  # First batch was skipped
