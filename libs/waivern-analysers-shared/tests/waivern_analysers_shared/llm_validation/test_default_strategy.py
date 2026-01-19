"""Tests for DefaultLLMValidationStrategy base class behaviour.

These tests verify the count-based batching, error handling, and fail-safe
behaviours implemented in the abstract base class. Concrete strategy
implementations inherit this behaviour and should NOT re-test it.
"""

from typing import override
from unittest.mock import Mock

import pytest
from waivern_core.schemas import BaseFindingEvidence, BaseFindingModel
from waivern_llm import BaseLLMService

from waivern_analysers_shared.llm_validation.default_strategy import (
    DefaultLLMValidationStrategy,
)
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_analysers_shared.types import LLMValidationConfig

# =============================================================================
# Test Fixtures
# =============================================================================


class MockFinding(BaseFindingModel):
    """Minimal finding type for testing."""

    category: str = "test"


class ConcreteTestStrategy(DefaultLLMValidationStrategy[MockFinding]):
    """Concrete implementation for testing the abstract base class."""

    @override
    def get_validation_prompt(
        self,
        findings_batch: list[MockFinding],
        config: LLMValidationConfig,
    ) -> str:
        """Generate simple test prompt with finding IDs."""
        del config  # Unused in test implementation
        ids = [f.id for f in findings_batch]
        return f"Validate findings: {', '.join(ids)}"


def make_finding(finding_id: str | None = None, category: str = "test") -> MockFinding:
    """Create a mock finding."""
    finding = MockFinding(
        category=category,
        evidence=[BaseFindingEvidence(content=f"Evidence for {category}")],
        matched_patterns=["test_pattern"],
    )
    if finding_id:
        # Override the auto-generated ID for deterministic testing
        object.__setattr__(finding, "id", finding_id)
    return finding


def make_false_positive_result(finding_id: str) -> LLMValidationResultModel:
    """Create a FALSE_POSITIVE validation result."""
    return LLMValidationResultModel(
        finding_id=finding_id,
        validation_result="FALSE_POSITIVE",
        confidence=0.9,
        reasoning="Test fixture data",
        recommended_action="discard",
    )


def make_response(
    results: list[LLMValidationResultModel],
) -> LLMValidationResponseModel:
    """Wrap results in a response model."""
    return LLMValidationResponseModel(results=results)


# =============================================================================
# Test Class
# =============================================================================


class TestDefaultLLMValidationStrategy:
    """Test suite for DefaultLLMValidationStrategy base class behaviour."""

    @pytest.fixture
    def strategy(self) -> ConcreteTestStrategy:
        """Create concrete strategy instance."""
        return ConcreteTestStrategy()

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
        return Mock(spec=BaseLLMService)

    # -------------------------------------------------------------------------
    # Empty Input Handling
    # -------------------------------------------------------------------------

    def test_returns_empty_outcome_when_no_findings_provided(
        self,
        strategy: ConcreteTestStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """Empty input returns empty outcome without calling LLM."""
        outcome = strategy.validate_findings([], config, llm_service)

        assert outcome.kept_findings == []
        assert outcome.llm_validated_kept == []
        assert outcome.llm_validated_removed == []
        assert outcome.llm_not_flagged == []
        assert outcome.skipped == []
        assert outcome.validation_succeeded is True
        llm_service.invoke_with_structured_output.assert_not_called()

    # -------------------------------------------------------------------------
    # Batch Processing
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "batch_params",
        [
            (1, 3, 3),  # 3 findings, batch size 1 = 3 calls
            (2, 3, 2),  # 3 findings, batch size 2 = 2 calls (2+1)
            (3, 3, 1),  # 3 findings, batch size 3 = 1 call
            (5, 3, 1),  # 3 findings, batch size 5 = 1 call (larger than count)
            (2, 5, 3),  # 5 findings, batch size 2 = 3 calls (2+2+1)
        ],
        ids=[
            "batch1_find3",
            "batch2_find3",
            "batch3_find3",
            "batch5_find3",
            "batch2_find5",
        ],
    )
    def test_processes_findings_in_batches(
        self,
        strategy: ConcreteTestStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
        batch_params: tuple[int, int, int],
    ) -> None:
        """Findings are batched according to config."""
        batch_size, num_findings, expected_calls = batch_params
        findings = [make_finding(category=f"cat_{i}") for i in range(num_findings)]
        config.llm_batch_size = batch_size

        # Return empty response for each batch (all findings kept as not_flagged)
        llm_service.invoke_with_structured_output.return_value = make_response([])

        outcome = strategy.validate_findings(findings, config, llm_service)

        assert len(outcome.kept_findings) == num_findings
        assert llm_service.invoke_with_structured_output.call_count == expected_calls
        assert outcome.validation_succeeded is True
        # All findings should be in not_flagged since LLM returned empty
        assert len(outcome.llm_not_flagged) == num_findings

    def test_batch_prompt_contains_correct_findings(
        self,
        strategy: ConcreteTestStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """Each batch prompt contains only the findings for that batch."""
        findings = [make_finding(f"finding_{i}") for i in range(3)]
        config.llm_batch_size = 2

        llm_service.invoke_with_structured_output.return_value = make_response([])

        strategy.validate_findings(findings, config, llm_service)

        # Check the prompts passed to LLM
        calls = llm_service.invoke_with_structured_output.call_args_list
        assert len(calls) == 2

        # First batch should have finding_0 and finding_1
        first_prompt = calls[0][0][0]
        assert "finding_0" in first_prompt
        assert "finding_1" in first_prompt
        assert "finding_2" not in first_prompt

        # Second batch should have finding_2
        second_prompt = calls[1][0][0]
        assert "finding_2" in second_prompt
        assert "finding_0" not in second_prompt

    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    def test_continues_processing_after_batch_error(
        self,
        strategy: ConcreteTestStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """If one batch fails, continue with remaining batches."""
        findings = [make_finding(f"finding_{i}") for i in range(4)]
        config.llm_batch_size = 2

        # First batch fails, second succeeds
        llm_service.invoke_with_structured_output.side_effect = [
            Exception("Batch 1 failed"),
            make_response([]),  # Second batch returns empty (all kept)
        ]

        outcome = strategy.validate_findings(findings, config, llm_service)

        # All 4 findings kept (2 from failed batch as skipped, 2 not flagged)
        assert len(outcome.kept_findings) == 4
        assert outcome.validation_succeeded is False  # Not all batches succeeded
        assert len(outcome.skipped) == 2  # First batch was skipped
        assert len(outcome.llm_not_flagged) == 2  # Second batch not flagged

    def test_returns_all_findings_as_skipped_on_total_failure(
        self,
        strategy: ConcreteTestStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """If all batches fail, all findings are marked as skipped."""
        findings = [make_finding(f"finding_{i}") for i in range(3)]
        config.llm_batch_size = 2

        # All batches fail
        llm_service.invoke_with_structured_output.side_effect = Exception(
            "LLM unavailable"
        )

        outcome = strategy.validate_findings(findings, config, llm_service)

        # All findings returned but marked as skipped
        assert len(outcome.kept_findings) == 3
        assert outcome.validation_succeeded is False
        assert len(outcome.skipped) == 3
        assert len(outcome.llm_validated_kept) == 0
        assert len(outcome.llm_not_flagged) == 0

    # -------------------------------------------------------------------------
    # Fail-Safe Behaviour
    # -------------------------------------------------------------------------

    def test_keeps_findings_not_flagged_by_llm(
        self,
        strategy: ConcreteTestStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """Findings not mentioned in LLM response are kept (fail-safe)."""
        findings = [make_finding(f"finding_{i}") for i in range(3)]

        # LLM returns empty response - no findings flagged
        llm_service.invoke_with_structured_output.return_value = make_response([])

        outcome = strategy.validate_findings(findings, config, llm_service)

        # All findings kept as not_flagged
        assert len(outcome.kept_findings) == 3
        assert outcome.validation_succeeded is True
        assert len(outcome.llm_not_flagged) == 3
        assert len(outcome.llm_validated_kept) == 0

    def test_keeps_findings_with_partial_llm_response(
        self,
        strategy: ConcreteTestStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """Findings omitted from partial LLM response are kept."""
        findings = [make_finding(f"finding_{i}") for i in range(3)]

        # LLM only flags one finding as false positive
        llm_service.invoke_with_structured_output.return_value = make_response(
            [make_false_positive_result("finding_1")]
        )

        outcome = strategy.validate_findings(findings, config, llm_service)

        # 2 kept (not flagged), 1 removed (false positive)
        assert len(outcome.kept_findings) == 2
        assert len(outcome.llm_validated_removed) == 1
        assert len(outcome.llm_not_flagged) == 2
        assert outcome.validation_succeeded is True

    # -------------------------------------------------------------------------
    # False Positive Filtering
    # -------------------------------------------------------------------------

    def test_filters_out_false_positive_findings(
        self,
        strategy: ConcreteTestStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """Findings marked FALSE_POSITIVE by LLM are removed."""
        findings = [make_finding(f"finding_{i}") for i in range(2)]

        # LLM marks first finding as FALSE_POSITIVE
        llm_service.invoke_with_structured_output.return_value = make_response(
            [make_false_positive_result("finding_0")]
        )

        outcome = strategy.validate_findings(findings, config, llm_service)

        # Only second finding kept (first was FALSE_POSITIVE)
        assert len(outcome.kept_findings) == 1
        assert outcome.validation_succeeded is True
        assert len(outcome.llm_validated_removed) == 1
        # The second finding was not flagged (not in LLM response)
        assert len(outcome.llm_not_flagged) == 1

    def test_handles_unknown_finding_id_from_llm(
        self,
        strategy: ConcreteTestStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """Unknown finding IDs from LLM are logged and ignored."""
        findings = [make_finding("finding_0")]

        # LLM returns result for unknown finding ID
        llm_service.invoke_with_structured_output.return_value = make_response(
            [make_false_positive_result("unknown_finding_id")]
        )

        outcome = strategy.validate_findings(findings, config, llm_service)

        # Original finding kept as not_flagged (unknown ID ignored)
        assert len(outcome.kept_findings) == 1
        assert len(outcome.llm_not_flagged) == 1
        assert outcome.validation_succeeded is True
