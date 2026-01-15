"""Tests for PersonalDataValidationStrategy."""

from unittest.mock import Mock

import pytest
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core.schemas import BaseFindingEvidence
from waivern_llm import AnthropicLLMService

from waivern_personal_data_analyser.llm_validation_strategy import (
    PersonalDataValidationStrategy,
)
from waivern_personal_data_analyser.schemas.types import (
    PersonalDataIndicatorMetadata,
    PersonalDataIndicatorModel,
)

# =============================================================================
# Test Helpers
# =============================================================================


def _make_finding(
    category: str = "email",
    pattern: str = "test@example.com",
    source: str = "test_source",
) -> PersonalDataIndicatorModel:
    """Create a finding with minimal boilerplate."""
    return PersonalDataIndicatorModel(
        category=category,
        matched_patterns=[pattern],
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


# =============================================================================
# Test Class
# =============================================================================


class TestPersonalDataValidationStrategy:
    """Test suite for PersonalDataValidationStrategy."""

    # -------------------------------------------------------------------------
    # Fixtures
    # -------------------------------------------------------------------------

    @pytest.fixture
    def strategy(self) -> PersonalDataValidationStrategy:
        """Create strategy instance."""
        return PersonalDataValidationStrategy()

    @pytest.fixture
    def config(self) -> LLMValidationConfig:
        """Create standard LLM configuration."""
        return LLMValidationConfig(
            enable_llm_validation=True,
            llm_batch_size=10,  # Large batch to avoid batching in most tests
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

    # -------------------------------------------------------------------------
    # Core Validation Behaviour
    # -------------------------------------------------------------------------

    def test_returns_empty_list_when_no_findings_provided(
        self,
        strategy: PersonalDataValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """Empty input returns empty output without calling LLM."""
        result, success = strategy.validate_findings([], config, llm_service)

        assert result == []
        assert success is True
        llm_service.invoke_with_structured_output.assert_not_called()

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

        result, success = strategy.validate_findings(
            sample_findings, config, llm_service
        )

        assert len(result) == 2
        assert result[0].category == "email"
        assert result[1].category == "phone"
        assert success is True

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

        result, success = strategy.validate_findings(
            sample_findings, config, llm_service
        )

        assert len(result) == 1
        assert result[0].category == "phone"
        assert success is True

    def test_preserves_original_finding_objects(
        self,
        strategy: PersonalDataValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[PersonalDataIndicatorModel],
    ) -> None:
        """Returned findings are the same object instances as input."""
        llm_service.invoke_with_structured_output.return_value = _make_response(
            [
                _make_result(sample_findings[0].id),
                _make_result(sample_findings[1].id),
            ]
        )

        result, _ = strategy.validate_findings(sample_findings, config, llm_service)

        # Same instances, not copies
        assert result[0] is sample_findings[0]
        assert result[1] is sample_findings[1]

    # -------------------------------------------------------------------------
    # Fail-Safe Behaviour
    # -------------------------------------------------------------------------

    def test_includes_findings_not_returned_by_llm(
        self,
        strategy: PersonalDataValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[PersonalDataIndicatorModel],
    ) -> None:
        """Findings omitted from LLM response are kept (fail-safe)."""
        # LLM only returns result for first finding
        llm_service.invoke_with_structured_output.return_value = _make_response(
            [
                _make_result(sample_findings[0].id),
            ]
        )

        result, success = strategy.validate_findings(
            sample_findings, config, llm_service
        )

        # Both kept - second one wasn't flagged as false positive
        assert len(result) == 2
        assert {f.category for f in result} == {"email", "phone"}
        assert success is True

    def test_keeps_findings_with_unknown_validation_result(
        self,
        strategy: PersonalDataValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[PersonalDataIndicatorModel],
    ) -> None:
        """UNKNOWN validation result keeps the finding (conservative)."""
        llm_service.invoke_with_structured_output.return_value = _make_response(
            [
                _make_result(sample_findings[0].id),
                LLMValidationResultModel(
                    finding_id=sample_findings[1].id,
                    validation_result="UNKNOWN",
                    confidence=0.5,
                    reasoning="Uncertain",
                    recommended_action="flag_for_review",
                ),
            ]
        )

        result, success = strategy.validate_findings(
            sample_findings, config, llm_service
        )

        assert len(result) == 2
        assert success is True

    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "error_message",
        [
            "LLM service unavailable",
            "Validation error: invalid response format",
            "Network timeout",
        ],
    )
    def test_returns_original_findings_on_llm_error(
        self,
        strategy: PersonalDataValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        sample_findings: list[PersonalDataIndicatorModel],
        error_message: str,
    ) -> None:
        """On any LLM error, return original findings with success=False."""
        llm_service.invoke_with_structured_output.side_effect = Exception(error_message)

        result, success = strategy.validate_findings(
            sample_findings, config, llm_service
        )

        assert result == sample_findings
        assert success is False

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
        strategy: PersonalDataValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        batch_size: int,
        expected_calls: int,
    ) -> None:
        """Findings are batched according to config."""
        findings = [_make_finding("email", f"user{i}@test.com") for i in range(3)]
        config.llm_batch_size = batch_size

        # Return TRUE_POSITIVE for whatever findings are in each batch
        def mock_invoke(prompt: str, model: type) -> LLMValidationResponseModel:
            # Extract finding IDs from the prompt (they appear as UUIDs)
            results = [_make_result(f.id) for f in findings if f.id in prompt]
            return _make_response(results)

        llm_service.invoke_with_structured_output.side_effect = mock_invoke

        result, success = strategy.validate_findings(findings, config, llm_service)

        assert len(result) == 3
        assert llm_service.invoke_with_structured_output.call_count == expected_calls
        assert success is True

    def test_continues_processing_after_batch_error(
        self,
        strategy: PersonalDataValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """If one batch fails, continue with remaining batches."""
        findings = [_make_finding("email", f"user{i}@test.com") for i in range(4)]
        config.llm_batch_size = 2

        # First batch fails, second succeeds
        llm_service.invoke_with_structured_output.side_effect = [
            Exception("Batch 1 failed"),
            _make_response(
                [
                    _make_result(findings[2].id),
                    _make_result(findings[3].id),
                ]
            ),
        ]

        result, success = strategy.validate_findings(findings, config, llm_service)

        # All 4 findings returned (2 from failed batch unvalidated, 2 validated)
        assert len(result) == 4
        assert success is False  # Not all batches succeeded
