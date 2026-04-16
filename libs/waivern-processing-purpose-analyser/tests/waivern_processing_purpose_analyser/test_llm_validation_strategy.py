"""Tests for LLM validation strategies.

Tests verify the strategies correctly use LLMService to validate findings
and map responses to LLMValidationOutcome.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail
from waivern_llm import (
    BatchingMode,
    ItemGroup,
    LLMCompletionResult,
    LLMRequest,
    LLMService,
    SkippedFinding,
    SkipReason,
)
from waivern_schemas.processing_purpose_indicator import (
    ProcessingPurposeIndicatorMetadata,
    ProcessingPurposeIndicatorModel,
)

from waivern_processing_purpose_analyser.llm_validation_strategy import (
    ProcessingPurposeValidationStrategy,
)
from waivern_processing_purpose_analyser.prompts import (
    ProcessingPurposePromptBuilder,
    SourceCodePromptBuilder,
)
from waivern_processing_purpose_analyser.validation.extended_context_strategy import (
    SourceCodeStrategyState,
    SourceCodeValidationStrategy,
)
from waivern_processing_purpose_analyser.validation.providers import (
    SourceCodeSourceProvider,
)


def _make_finding(
    purpose: str = "Payment Processing",
    pattern: str = "payment",
    source: str = "test_source",
) -> ProcessingPurposeIndicatorModel:
    """Create a finding with minimal boilerplate."""
    return ProcessingPurposeIndicatorModel(
        purpose=purpose,
        matched_patterns=[PatternMatchDetail(pattern=pattern, match_count=1)],
        evidence=[BaseFindingEvidence(content=f"Content: {pattern}")],
        metadata=ProcessingPurposeIndicatorMetadata(source=source),
    )


class TestProcessingPurposeValidationStrategy:
    """Test suite for ProcessingPurposeValidationStrategy."""

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
            llm_validation_mode="standard",
        )

    @pytest.fixture
    def sample_findings(self) -> list[ProcessingPurposeIndicatorModel]:
        """Create two sample findings for testing."""
        return [
            _make_finding(
                "Payment Processing",
                "payment",
                "mysql_database_(prod)_table_(payments)",
            ),
            _make_finding(
                "User Analytics", "analytics", "mysql_database_(prod)_table_(events)"
            ),
        ]

    # =========================================================================
    # prepare_validation (dispatcher-ready request construction)
    # =========================================================================

    def test_prepare_validation_builds_count_based_llm_request(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
    ) -> None:
        """prepare_validation returns an LLMRequest configured for COUNT_BASED batching."""
        findings = [
            _make_finding("Payment Processing"),
            _make_finding("User Analytics"),
        ]
        strategy = ProcessingPurposeValidationStrategy(mock_llm_service)

        strategy_findings, request = strategy.prepare_validation(
            findings, config, "test-run"
        )

        assert strategy_findings == findings
        assert isinstance(request, LLMRequest)
        assert request.batching_mode == BatchingMode.COUNT_BASED
        assert request.run_id == "test-run"
        assert isinstance(request.prompt_builder, ProcessingPurposePromptBuilder)
        assert request.response_model == LLMValidationResponseModel
        assert len(request.groups) == 1
        assert isinstance(request.groups[0], ItemGroup)
        assert list(request.groups[0].items) == findings

    def test_prepare_validation_returns_no_request_for_empty_findings(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
    ) -> None:
        """Empty findings -> ([], None) so the orchestrator can skip dispatch."""
        strategy = ProcessingPurposeValidationStrategy(mock_llm_service)

        strategy_findings, request = strategy.prepare_validation([], config, "test-run")

        assert strategy_findings == []
        assert request is None

    # =========================================================================
    # Core Validation Behaviour
    # =========================================================================

    def test_calls_llm_service_complete_with_correct_args(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
    ) -> None:
        """Strategy calls LLMService.complete() with ItemGroup, prompt_builder, BatchingMode."""
        findings = [
            _make_finding("Payment Processing"),
            _make_finding("User Analytics"),
        ]
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[LLMValidationResponseModel(results=[])],
            skipped=[],
        )
        strategy = ProcessingPurposeValidationStrategy(mock_llm_service)

        strategy.validate_findings(findings, config, "test-run")

        mock_llm_service.complete.assert_called_once()
        call_kwargs = mock_llm_service.complete.call_args.kwargs

        # Verify ItemGroup
        groups = mock_llm_service.complete.call_args.args[0]
        assert len(groups) == 1
        assert isinstance(groups[0], ItemGroup)
        assert len(groups[0].items) == 2

        # Verify other args
        assert isinstance(call_kwargs["prompt_builder"], ProcessingPurposePromptBuilder)
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
        sample_findings: list[ProcessingPurposeIndicatorModel],
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
                            reasoning="Valid payment processing",
                            recommended_action="keep",
                        ),
                        LLMValidationResultModel(
                            finding_id=sample_findings[1].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.85,
                            reasoning="Valid analytics tracking",
                            recommended_action="keep",
                        ),
                    ]
                )
            ],
            skipped=[],
        )
        strategy = ProcessingPurposeValidationStrategy(mock_llm_service)

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
        sample_findings: list[ProcessingPurposeIndicatorModel],
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
                            reasoning="Valid analytics tracking",
                            recommended_action="keep",
                        ),
                    ]
                )
            ],
            skipped=[],
        )
        strategy = ProcessingPurposeValidationStrategy(mock_llm_service)

        outcome = strategy.validate_findings(sample_findings, config, "test-run")

        assert len(outcome.llm_validated_kept) == 1
        assert outcome.llm_validated_kept[0].id == sample_findings[1].id
        assert len(outcome.llm_validated_removed) == 1
        assert outcome.llm_validated_removed[0].id == sample_findings[0].id

    def test_keeps_findings_not_flagged_by_llm(
        self,
        mock_llm_service: Mock,
        config: LLMValidationConfig,
        sample_findings: list[ProcessingPurposeIndicatorModel],
    ) -> None:
        """Findings not mentioned in LLM response are kept (fail-safe)."""
        # LLM returns empty response - no findings flagged
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[LLMValidationResponseModel(results=[])],
            skipped=[],
        )
        strategy = ProcessingPurposeValidationStrategy(mock_llm_service)

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
        sample_findings: list[ProcessingPurposeIndicatorModel],
    ) -> None:
        """Exception from LLMService returns all findings as skipped with BATCH_ERROR."""
        mock_llm_service.complete.side_effect = Exception("LLM API unavailable")
        strategy = ProcessingPurposeValidationStrategy(mock_llm_service)

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


class TestSourceCodeValidationStrategy:
    """Test suite for SourceCodeValidationStrategy.

    Tests verify the strategy correctly uses LLMService with EXTENDED_CONTEXT
    batching mode and groups findings by source file.
    """

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLMService."""
        service = Mock(spec=LLMService)
        service.complete = AsyncMock()
        return service

    @pytest.fixture
    def source_contents(self) -> dict[str, str]:
        """Map of source file paths to content."""
        return {
            "/src/PaymentService.php": "<?php class PaymentService { }",
            "/src/AnalyticsService.php": "<?php class AnalyticsService { }",
        }

    @pytest.fixture
    def source_provider(
        self, source_contents: dict[str, str]
    ) -> SourceCodeSourceProvider:
        """Create SourceCodeSourceProvider with test content."""
        return SourceCodeSourceProvider(source_contents)

    @pytest.fixture
    def config(self) -> LLMValidationConfig:
        """Create standard LLM configuration."""
        return LLMValidationConfig(
            enable_llm_validation=True,
            llm_validation_mode="standard",
        )

    @pytest.fixture
    def sample_findings(self) -> list[ProcessingPurposeIndicatorModel]:
        """Create sample findings from different source files."""
        return [
            _make_finding(
                "Payment Processing",
                "payment",
                "/src/PaymentService.php",
            ),
            _make_finding(
                "User Analytics",
                "analytics",
                "/src/AnalyticsService.php",
            ),
        ]

    # =========================================================================
    # prepare_validation (dispatcher-ready request construction)
    # =========================================================================

    def test_prepare_validation_builds_extended_context_llm_request(
        self,
        mock_llm_service: Mock,
        source_provider: SourceCodeSourceProvider,
        config: LLMValidationConfig,
        sample_findings: list[ProcessingPurposeIndicatorModel],
    ) -> None:
        """prepare_validation returns LLMRequest configured for EXTENDED_CONTEXT.

        Groups are created per source file and carry the file content needed for
        context-aware validation.
        """
        strategy = SourceCodeValidationStrategy(mock_llm_service, source_provider)

        strategy_findings, request = strategy.prepare_validation(
            sample_findings, config, "test-run"
        )

        assert strategy_findings == sample_findings
        assert isinstance(request, LLMRequest)
        assert request.batching_mode == BatchingMode.EXTENDED_CONTEXT
        assert request.run_id == "test-run"
        assert isinstance(request.prompt_builder, SourceCodePromptBuilder)
        assert request.response_model == LLMValidationResponseModel
        # One group per source file; content populated from the source provider
        assert len(request.groups) == 2
        assert {g.group_id for g in request.groups} == {
            "/src/PaymentService.php",
            "/src/AnalyticsService.php",
        }
        assert all(g.content is not None for g in request.groups)

    def test_prepare_validation_returns_no_request_for_empty_findings(
        self,
        mock_llm_service: Mock,
        source_provider: SourceCodeSourceProvider,
        config: LLMValidationConfig,
    ) -> None:
        """Empty findings -> ([], None) so the orchestrator can skip dispatch."""
        strategy = SourceCodeValidationStrategy(mock_llm_service, source_provider)

        strategy_findings, request = strategy.prepare_validation([], config, "test-run")

        assert strategy_findings == []
        assert request is None

    # =========================================================================
    # Core Validation Behaviour
    # =========================================================================

    def test_calls_llm_service_complete_with_correct_args(
        self,
        mock_llm_service: Mock,
        source_provider: SourceCodeSourceProvider,
        config: LLMValidationConfig,
        sample_findings: list[ProcessingPurposeIndicatorModel],
    ) -> None:
        """Strategy calls LLMService.complete() with EXTENDED_CONTEXT mode."""
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[LLMValidationResponseModel(results=[])],
            skipped=[],
        )
        strategy = SourceCodeValidationStrategy(mock_llm_service, source_provider)

        strategy.validate_findings(sample_findings, config, "test-run")

        mock_llm_service.complete.assert_called_once()
        call_kwargs = mock_llm_service.complete.call_args.kwargs

        # Verify groups - one per source file
        groups = mock_llm_service.complete.call_args.args[0]
        assert len(groups) == 2  # Two different source files

        # Verify other args
        assert isinstance(call_kwargs["prompt_builder"], SourceCodePromptBuilder)
        assert call_kwargs["response_model"] == LLMValidationResponseModel
        assert call_kwargs["batching_mode"] == BatchingMode.EXTENDED_CONTEXT
        assert call_kwargs["run_id"] == "test-run"

    def test_creates_groups_by_source_file(
        self,
        mock_llm_service: Mock,
        source_provider: SourceCodeSourceProvider,
        config: LLMValidationConfig,
    ) -> None:
        """Strategy creates one ItemGroup per source file with content."""
        # Two findings from the same source file
        findings = [
            _make_finding("Payment Processing", "payment", "/src/PaymentService.php"),
            _make_finding("Billing", "billing", "/src/PaymentService.php"),
        ]
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[LLMValidationResponseModel(results=[])],
            skipped=[],
        )
        strategy = SourceCodeValidationStrategy(mock_llm_service, source_provider)

        strategy.validate_findings(findings, config, "test-run")

        # Verify single group created (same source file)
        groups = mock_llm_service.complete.call_args.args[0]
        assert len(groups) == 1
        assert len(groups[0].items) == 2  # Both findings in same group
        assert groups[0].content == "<?php class PaymentService { }"

    # =========================================================================
    # Response Mapping
    # =========================================================================

    def test_maps_true_positive_to_kept_findings(
        self,
        mock_llm_service: Mock,
        source_provider: SourceCodeSourceProvider,
        config: LLMValidationConfig,
        sample_findings: list[ProcessingPurposeIndicatorModel],
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
                            reasoning="Valid payment processing",
                            recommended_action="keep",
                        ),
                        LLMValidationResultModel(
                            finding_id=sample_findings[1].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.85,
                            reasoning="Valid analytics tracking",
                            recommended_action="keep",
                        ),
                    ]
                )
            ],
            skipped=[],
        )
        strategy = SourceCodeValidationStrategy(mock_llm_service, source_provider)

        outcome = strategy.validate_findings(sample_findings, config, "test-run")

        assert len(outcome.llm_validated_kept) == 2
        assert outcome.llm_validated_removed == []
        assert outcome.llm_not_flagged == []
        kept_ids = {f.id for f in outcome.llm_validated_kept}
        assert kept_ids == {sample_findings[0].id, sample_findings[1].id}

    def test_filters_out_false_positive_findings(
        self,
        mock_llm_service: Mock,
        source_provider: SourceCodeSourceProvider,
        config: LLMValidationConfig,
        sample_findings: list[ProcessingPurposeIndicatorModel],
    ) -> None:
        """Findings marked FALSE_POSITIVE by LLM are removed."""
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
                            reasoning="Valid analytics tracking",
                            recommended_action="keep",
                        ),
                    ]
                )
            ],
            skipped=[],
        )
        strategy = SourceCodeValidationStrategy(mock_llm_service, source_provider)

        outcome = strategy.validate_findings(sample_findings, config, "test-run")

        assert len(outcome.llm_validated_kept) == 1
        assert outcome.llm_validated_kept[0].id == sample_findings[1].id
        assert len(outcome.llm_validated_removed) == 1
        assert outcome.llm_validated_removed[0].id == sample_findings[0].id

    def test_keeps_findings_not_flagged_by_llm(
        self,
        mock_llm_service: Mock,
        source_provider: SourceCodeSourceProvider,
        config: LLMValidationConfig,
        sample_findings: list[ProcessingPurposeIndicatorModel],
    ) -> None:
        """Findings not mentioned in LLM response are kept (fail-safe)."""
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[LLMValidationResponseModel(results=[])],
            skipped=[],
        )
        strategy = SourceCodeValidationStrategy(mock_llm_service, source_provider)

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
        source_provider: SourceCodeSourceProvider,
        config: LLMValidationConfig,
        sample_findings: list[ProcessingPurposeIndicatorModel],
    ) -> None:
        """Exception from LLMService returns all findings as skipped with BATCH_ERROR."""
        mock_llm_service.complete.side_effect = Exception("LLM API unavailable")
        strategy = SourceCodeValidationStrategy(mock_llm_service, source_provider)

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

    def test_skipped_findings_passed_through(
        self,
        mock_llm_service: Mock,
        source_provider: SourceCodeSourceProvider,
        config: LLMValidationConfig,
        sample_findings: list[ProcessingPurposeIndicatorModel],
    ) -> None:
        """Skipped findings from LLMCompletionResult appear in outcome."""
        # First finding is processed, second is skipped by BatchPlanner
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[
                LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=sample_findings[0].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid payment processing",
                            recommended_action="keep",
                        ),
                    ]
                )
            ],
            skipped=[
                SkippedFinding(
                    finding=sample_findings[1],
                    reason=SkipReason.MISSING_CONTENT,
                )
            ],
        )
        strategy = SourceCodeValidationStrategy(mock_llm_service, source_provider)

        outcome = strategy.validate_findings(sample_findings, config, "test-run")

        # First finding kept, second skipped
        assert len(outcome.llm_validated_kept) == 1
        assert outcome.llm_validated_kept[0].id == sample_findings[0].id
        assert len(outcome.skipped) == 1
        assert outcome.skipped[0].finding.id == sample_findings[1].id
        assert outcome.skipped[0].reason == SkipReason.MISSING_CONTENT


class TestStrategyPersistenceState:
    """Tests for export_persistence_state() — captures reconstruction state."""

    def test_source_code_strategy_exports_source_contents(self) -> None:
        """SourceCodeValidationStrategy exports source_contents in a round-trippable form."""
        file_contents = {"a.py": "content_a", "b.py": "content_b"}
        provider = SourceCodeSourceProvider(file_contents)
        strategy = SourceCodeValidationStrategy(Mock(spec=LLMService), provider)

        exported = strategy.export_persistence_state()

        assert exported is not None
        restored = SourceCodeStrategyState.model_validate(exported)
        assert restored.source_contents == file_contents

    def test_processing_purpose_validation_strategy_has_no_persistence_state(
        self,
    ) -> None:
        """ProcessingPurposeValidationStrategy inherits the default None."""
        strategy = ProcessingPurposeValidationStrategy(Mock(spec=LLMService))

        assert strategy.export_persistence_state() is None
