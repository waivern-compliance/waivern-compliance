"""Tests for DataSubjectValidationStrategy.

These tests verify behaviour specific to the DataSubjectValidationStrategy.
Base class behaviour (batching, error handling) is tested in
waivern_analysers_shared/llm_validation/test_default_strategy.py.
"""

from unittest.mock import Mock

import pytest
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail
from waivern_llm import AnthropicLLMService

from waivern_data_subject_analyser.llm_validation_strategy import (
    DataSubjectValidationStrategy,
)
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


class TestDataSubjectValidationStrategy:
    """Test suite for DataSubjectValidationStrategy-specific behaviour."""

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

    def test_generates_prompt_with_finding_details(
        self,
        strategy: DataSubjectValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[DataSubjectIndicatorModel],
    ) -> None:
        """Prompt includes finding IDs, categories, and evidence."""
        llm_service.invoke_with_structured_output.return_value = _make_response([])

        strategy.validate_findings(sample_findings, config, llm_service)

        # Verify prompt was generated with finding details
        call_args = llm_service.invoke_with_structured_output.call_args
        prompt = call_args[0][0]

        # Should include finding IDs for response matching
        assert sample_findings[0].id in prompt
        assert sample_findings[1].id in prompt

        # Should include subject categories
        assert "Customer" in prompt
        assert "Employee" in prompt
