"""Tests for PersonalDataValidationStrategy.

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

from waivern_personal_data_analyser.llm_validation_strategy import (
    PersonalDataValidationStrategy,
)
from waivern_personal_data_analyser.prompts.prompt_builder import (
    PersonalDataPromptBuilder,
)
from waivern_personal_data_analyser.schemas.types import (
    PersonalDataIndicatorMetadata,
    PersonalDataIndicatorModel,
)


def _make_finding(
    category: str = "email",
    pattern: str = "test@example.com",
) -> PersonalDataIndicatorModel:
    """Create a finding for testing."""
    return PersonalDataIndicatorModel(
        category=category,
        matched_patterns=[PatternMatchDetail(pattern=pattern, match_count=1)],
        evidence=[BaseFindingEvidence(content=f"Content: {pattern}")],
        metadata=PersonalDataIndicatorMetadata(source="test"),
    )


class TestPersonalDataValidationStrategy:
    """Test suite for PersonalDataValidationStrategy."""

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLMService."""
        service = Mock(spec=LLMService)
        service.complete = AsyncMock()
        return service

    @pytest.fixture
    def config(self) -> LLMValidationConfig:
        """Create standard config."""
        return LLMValidationConfig(
            enable_llm_validation=True,
            llm_batch_size=10,
            llm_validation_mode="standard",
        )

    def test_calls_llm_service_complete_with_correct_args(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
    ) -> None:
        """Strategy calls LLMService.complete() with ItemGroup, prompt_builder."""
        findings = [_make_finding("email"), _make_finding("phone")]
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[LLMValidationResponseModel(results=[])],
            skipped=[],
        )
        strategy = PersonalDataValidationStrategy(mock_llm_service)

        # llm_service param is required by interface but ignored by this strategy
        strategy.validate_findings(findings, config, Mock(), run_id="test-run")

        mock_llm_service.complete.assert_called_once()
        call_kwargs = mock_llm_service.complete.call_args.kwargs

        # Verify ItemGroup
        groups = mock_llm_service.complete.call_args.args[0]
        assert len(groups) == 1
        assert isinstance(groups[0], ItemGroup)
        assert len(groups[0].items) == 2

        # Verify other args
        assert isinstance(call_kwargs["prompt_builder"], PersonalDataPromptBuilder)
        assert call_kwargs["response_model"] == LLMValidationResponseModel
        assert call_kwargs["batching_mode"] == BatchingMode.COUNT_BASED

    def test_raises_error_when_run_id_not_provided(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
    ) -> None:
        """Strategy raises ValueError if run_id is not provided."""
        findings = [_make_finding("email")]
        strategy = PersonalDataValidationStrategy(mock_llm_service)

        with pytest.raises(ValueError, match="run_id is required"):
            strategy.validate_findings(findings, config, Mock())  # No run_id

    def test_maps_true_positive_to_kept_findings(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
    ) -> None:
        """Findings marked TRUE_POSITIVE are in llm_validated_kept."""
        findings = [_make_finding("email"), _make_finding("phone")]
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[
                LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=findings[0].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid email",
                            recommended_action="keep",
                        ),
                        LLMValidationResultModel(
                            finding_id=findings[1].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.85,
                            reasoning="Valid phone",
                            recommended_action="keep",
                        ),
                    ]
                )
            ],
            skipped=[],
        )
        strategy = PersonalDataValidationStrategy(mock_llm_service)

        outcome = strategy.validate_findings(
            findings, config, Mock(), run_id="test-run"
        )

        assert len(outcome.llm_validated_kept) == 2
        assert outcome.llm_validated_removed == []
        assert outcome.llm_not_flagged == []
        kept_ids = {f.id for f in outcome.llm_validated_kept}
        assert kept_ids == {findings[0].id, findings[1].id}

    def test_maps_false_positive_to_removed_findings(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
    ) -> None:
        """Findings marked FALSE_POSITIVE are in llm_validated_removed."""
        findings = [_make_finding("email"), _make_finding("phone")]
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[
                LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=findings[0].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid email",
                            recommended_action="keep",
                        ),
                        LLMValidationResultModel(
                            finding_id=findings[1].id,
                            validation_result="FALSE_POSITIVE",
                            confidence=0.95,
                            reasoning="Example data in documentation",
                            recommended_action="discard",
                        ),
                    ]
                )
            ],
            skipped=[],
        )
        strategy = PersonalDataValidationStrategy(mock_llm_service)

        outcome = strategy.validate_findings(
            findings, config, Mock(), run_id="test-run"
        )

        assert len(outcome.llm_validated_kept) == 1
        assert outcome.llm_validated_kept[0].id == findings[0].id
        assert len(outcome.llm_validated_removed) == 1
        assert outcome.llm_validated_removed[0].id == findings[1].id

    def test_unflagged_findings_kept_via_failsafe(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
    ) -> None:
        """Findings not mentioned in response are in llm_not_flagged."""
        findings = [
            _make_finding("email"),
            _make_finding("phone"),
            _make_finding("name"),
        ]
        # LLM only returns result for first finding, omits others
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[
                LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=findings[0].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid email",
                            recommended_action="keep",
                        ),
                    ]
                )
            ],
            skipped=[],
        )
        strategy = PersonalDataValidationStrategy(mock_llm_service)

        outcome = strategy.validate_findings(
            findings, config, Mock(), run_id="test-run"
        )

        # One explicitly kept, two kept via fail-safe
        assert len(outcome.llm_validated_kept) == 1
        assert outcome.llm_validated_kept[0].id == findings[0].id
        assert len(outcome.llm_not_flagged) == 2
        not_flagged_ids = {f.id for f in outcome.llm_not_flagged}
        assert not_flagged_ids == {findings[1].id, findings[2].id}

    def test_total_failure_returns_all_skipped(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
    ) -> None:
        """Exception from LLMService returns all findings as skipped."""
        findings = [_make_finding("email"), _make_finding("phone")]
        mock_llm_service.complete.side_effect = Exception("LLM API unavailable")
        strategy = PersonalDataValidationStrategy(mock_llm_service)

        outcome = strategy.validate_findings(
            findings, config, Mock(), run_id="test-run"
        )

        # All findings should be skipped with BATCH_ERROR reason
        assert outcome.llm_validated_kept == []
        assert outcome.llm_validated_removed == []
        assert outcome.llm_not_flagged == []
        assert len(outcome.skipped) == 2
        skipped_ids = {s.finding.id for s in outcome.skipped}
        assert skipped_ids == {findings[0].id, findings[1].id}
        for skipped in outcome.skipped:
            assert skipped.reason == SkipReason.BATCH_ERROR
