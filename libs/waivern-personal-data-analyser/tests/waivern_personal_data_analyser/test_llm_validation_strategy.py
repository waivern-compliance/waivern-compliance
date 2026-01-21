"""Tests for PersonalDataValidationStrategy.

These tests verify behaviour specific to the PersonalDataValidationStrategy.
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

from waivern_personal_data_analyser.llm_validation_strategy import (
    PersonalDataValidationStrategy,
)
from waivern_personal_data_analyser.schemas.types import (
    PersonalDataIndicatorMetadata,
    PersonalDataIndicatorModel,
)


def _make_finding(
    category: str = "email",
    pattern: str = "test@example.com",
    source: str = "test_source",
) -> PersonalDataIndicatorModel:
    """Create a finding with minimal boilerplate."""
    return PersonalDataIndicatorModel(
        category=category,
        matched_patterns=[PatternMatchDetail(pattern=pattern, match_count=1)],
        evidence=[BaseFindingEvidence(content=f"Content: {pattern}")],
        metadata=PersonalDataIndicatorMetadata(source=source),
    )


def _make_result(
    finding_id: str,
    *,
    is_false_positive: bool = False,
) -> LLMValidationResultModel:
    """Create a validation result. Defaults to TRUE_POSITIVE."""
    return LLMValidationResultModel(
        finding_id=finding_id,
        validation_result="FALSE_POSITIVE" if is_false_positive else "TRUE_POSITIVE",
        confidence=0.9,
        reasoning="Example" if is_false_positive else "Valid",
        recommended_action="discard" if is_false_positive else "keep",
    )


def _make_response(
    results: list[LLMValidationResultModel],
) -> LLMValidationResponseModel:
    """Wrap results in a response model."""
    return LLMValidationResponseModel(results=results)


class TestPersonalDataValidationStrategy:
    """Test suite for PersonalDataValidationStrategy-specific behaviour."""

    @pytest.fixture
    def strategy(self) -> PersonalDataValidationStrategy:
        """Create strategy instance."""
        return PersonalDataValidationStrategy()

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
    def sample_findings(self) -> list[PersonalDataIndicatorModel]:
        """Create two sample findings for testing."""
        return [
            _make_finding("email", "test@example.com", "contact_form.php"),
            _make_finding("phone", "123-456-7890", "customer_db"),
        ]

    def test_keeps_true_positive_findings(
        self,
        strategy: PersonalDataValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[PersonalDataIndicatorModel],
    ) -> None:
        """Findings marked TRUE_POSITIVE are kept."""
        llm_service.invoke_with_structured_output.return_value = _make_response(
            [
                _make_result(sample_findings[0].id),
                _make_result(sample_findings[1].id),
            ]
        )

        outcome = strategy.validate_findings(sample_findings, config, llm_service)

        assert len(outcome.kept_findings) == 2
        assert outcome.kept_findings[0].category == "email"
        assert outcome.kept_findings[1].category == "phone"
        assert outcome.validation_succeeded is True

    def test_filters_out_false_positive_findings(
        self,
        strategy: PersonalDataValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[PersonalDataIndicatorModel],
    ) -> None:
        """Findings marked FALSE_POSITIVE are removed."""
        llm_service.invoke_with_structured_output.return_value = _make_response(
            [
                _make_result(sample_findings[0].id, is_false_positive=True),
                _make_result(sample_findings[1].id),
            ]
        )

        outcome = strategy.validate_findings(sample_findings, config, llm_service)

        assert len(outcome.kept_findings) == 1
        assert outcome.kept_findings[0].category == "phone"
        assert outcome.validation_succeeded is True
        assert len(outcome.llm_validated_removed) == 1

    def test_keeps_findings_not_flagged_by_llm(
        self,
        strategy: PersonalDataValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[PersonalDataIndicatorModel],
    ) -> None:
        """Findings omitted from LLM response are kept (fail-safe)."""
        # LLM only returns result for first finding
        llm_service.invoke_with_structured_output.return_value = _make_response(
            [_make_result(sample_findings[0].id)]
        )

        outcome = strategy.validate_findings(sample_findings, config, llm_service)

        # Both kept - second one wasn't flagged as false positive
        assert len(outcome.kept_findings) == 2
        assert {f.category for f in outcome.kept_findings} == {"email", "phone"}
        assert outcome.validation_succeeded is True
        assert len(outcome.llm_not_flagged) == 1

    def test_generates_prompt_with_finding_details(
        self,
        strategy: PersonalDataValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[PersonalDataIndicatorModel],
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

        # Should include categories
        assert "email" in prompt
        assert "phone" in prompt
