"""Tests for RiskModifierValidationStrategy.

Tests focus on the behaviour specific to this strategy:
- Category-level aggregation of modifiers
- Union semantics for combining modifiers
- Average confidence calculation
- Failure handling

LLMService batching and caching are tested in waivern-llm and NOT re-tested here.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail
from waivern_llm import LLMCompletionResult, LLMService, SkippedFinding, SkipReason
from waivern_rulesets import RiskModifier

from waivern_gdpr_data_subject_classifier.schemas import (
    GDPRDataSubjectFindingMetadata,
    GDPRDataSubjectFindingModel,
)
from waivern_gdpr_data_subject_classifier.validation.models import (
    RiskModifierResultModel,
    RiskModifierValidationResponseModel,
)
from waivern_gdpr_data_subject_classifier.validation.strategy import (
    RiskModifierValidationStrategy,
)


def make_finding(
    finding_id: str,
    category: str,
    evidence_text: str = "Test evidence",
) -> GDPRDataSubjectFindingModel:
    """Create a test finding with specified ID and category."""
    finding = GDPRDataSubjectFindingModel(
        data_subject_category=category,
        confidence_score=80,
        evidence=[BaseFindingEvidence(content=evidence_text)],
        matched_patterns=[PatternMatchDetail(pattern="test_pattern", match_count=1)],
        metadata=GDPRDataSubjectFindingMetadata(source="test_source"),
    )
    # Override auto-generated ID for deterministic testing
    object.__setattr__(finding, "id", finding_id)
    return finding


def make_llm_result(
    finding_id: str,
    modifiers: list[str],
    confidence: float = 0.85,
) -> RiskModifierResultModel:
    """Create an LLM result for a finding."""
    return RiskModifierResultModel(
        finding_id=finding_id,
        risk_modifiers=modifiers,
        confidence=confidence,
        reasoning="Test reasoning",
    )


def make_response(
    results: list[RiskModifierResultModel],
) -> RiskModifierValidationResponseModel:
    """Wrap results in a response model."""
    return RiskModifierValidationResponseModel(results=results)


def make_completion_result(
    responses: list[RiskModifierValidationResponseModel],
    skipped: list[SkippedFinding[GDPRDataSubjectFindingModel]] | None = None,
) -> LLMCompletionResult[
    GDPRDataSubjectFindingModel, RiskModifierValidationResponseModel
]:
    """Create an LLMCompletionResult for testing."""
    return LLMCompletionResult(
        responses=responses,
        skipped=skipped or [],
    )


class TestRiskModifierValidationStrategy:
    """Test suite for RiskModifierValidationStrategy."""

    @pytest.fixture
    def available_modifiers(self) -> list[RiskModifier]:
        """Create test risk modifiers from ruleset."""
        return [
            RiskModifier(
                modifier="minor",
                article_references=["Article 8"],
                patterns=["minor", "child"],
            ),
            RiskModifier(
                modifier="vulnerable_individual",
                article_references=["Recital 75"],
                patterns=["vulnerable", "elderly"],
            ),
        ]

    @pytest.fixture
    def llm_service(self) -> Mock:
        """Create mock LLM service with async complete method."""
        mock = Mock(spec=LLMService)
        mock.complete = AsyncMock()
        return mock

    @pytest.fixture
    def strategy(
        self,
        available_modifiers: list[RiskModifier],
        llm_service: Mock,
    ) -> RiskModifierValidationStrategy:
        """Create strategy instance with LLMService injected."""
        return RiskModifierValidationStrategy(
            available_modifiers=available_modifiers,
            llm_service=llm_service,
        )

    @pytest.fixture
    def run_id(self) -> str:
        """Provide a test run ID for cache scoping."""
        return "test-run-123"

    # -------------------------------------------------------------------------
    # Category-Level Aggregation
    # -------------------------------------------------------------------------

    def test_aggregates_modifiers_by_category(
        self,
        strategy: RiskModifierValidationStrategy,
        llm_service: Mock,
        run_id: str,
    ) -> None:
        """Findings from different categories produce separate CategoryRiskModifierResult entries."""
        # Arrange: Two findings from different categories
        findings = [
            make_finding(
                "finding-1", category="patient", evidence_text="8-year-old patient"
            ),
            make_finding(
                "finding-2", category="employee", evidence_text="elderly employee"
            ),
        ]

        # LLM returns modifiers for each finding
        llm_service.complete.return_value = make_completion_result(
            responses=[
                make_response(
                    [
                        make_llm_result(
                            "finding-1", modifiers=["minor"], confidence=0.9
                        ),
                        make_llm_result(
                            "finding-2",
                            modifiers=["vulnerable_individual"],
                            confidence=0.8,
                        ),
                    ]
                )
            ]
        )

        # Act
        result = strategy.enrich(findings, run_id)

        # Assert: Two separate category results
        assert len(result.category_results) == 2

        # Find results by category
        results_by_cat = {r.category: r for r in result.category_results}

        assert "patient" in results_by_cat
        assert results_by_cat["patient"].detected_modifiers == ["minor"]

        assert "employee" in results_by_cat
        assert results_by_cat["employee"].detected_modifiers == [
            "vulnerable_individual"
        ]

        assert result.validation_succeeded is True

    def test_combines_modifiers_as_union_within_category(
        self,
        strategy: RiskModifierValidationStrategy,
        llm_service: Mock,
        run_id: str,
    ) -> None:
        """Multiple findings in same category produce union of modifiers, not duplicates."""
        # Arrange: Three findings in same category with overlapping modifiers
        findings = [
            make_finding(
                "finding-1", category="patient", evidence_text="8-year-old patient"
            ),
            make_finding(
                "finding-2", category="patient", evidence_text="elderly patient"
            ),
            make_finding(
                "finding-3", category="patient", evidence_text="child with disability"
            ),
        ]

        # LLM returns different modifiers for each, with some overlap
        llm_service.complete.return_value = make_completion_result(
            responses=[
                make_response(
                    [
                        make_llm_result("finding-1", modifiers=["minor"]),
                        make_llm_result(
                            "finding-2", modifiers=["vulnerable_individual"]
                        ),
                        make_llm_result(
                            "finding-3", modifiers=["minor", "vulnerable_individual"]
                        ),
                    ]
                )
            ]
        )

        # Act
        result = strategy.enrich(findings, run_id)

        # Assert: Single category with union of all modifiers (no duplicates, sorted)
        assert len(result.category_results) == 1

        patient_result = result.category_results[0]
        assert patient_result.category == "patient"
        assert patient_result.detected_modifiers == ["minor", "vulnerable_individual"]
        assert patient_result.sample_count == 3

    def test_calculates_average_confidence_per_category(
        self,
        strategy: RiskModifierValidationStrategy,
        llm_service: Mock,
        run_id: str,
    ) -> None:
        """Category confidence is the average of all finding confidences in that category."""
        # Arrange: Two findings in same category with different confidences
        findings = [
            make_finding("finding-1", category="patient"),
            make_finding("finding-2", category="patient"),
        ]

        # LLM returns different confidence scores: 0.8 and 0.6 → average = 0.7
        llm_service.complete.return_value = make_completion_result(
            responses=[
                make_response(
                    [
                        make_llm_result(
                            "finding-1", modifiers=["minor"], confidence=0.8
                        ),
                        make_llm_result(
                            "finding-2", modifiers=["minor"], confidence=0.6
                        ),
                    ]
                )
            ]
        )

        # Act
        result = strategy.enrich(findings, run_id)

        # Assert: Confidence is average of 0.8 and 0.6
        assert len(result.category_results) == 1
        assert abs(result.category_results[0].confidence - 0.7) < 1e-9

    # -------------------------------------------------------------------------
    # Failure Handling
    # -------------------------------------------------------------------------

    def test_handles_skipped_findings_gracefully(
        self,
        strategy: RiskModifierValidationStrategy,
        llm_service: Mock,
        run_id: str,
    ) -> None:
        """When LLMService returns skipped findings, aggregate what was processed."""
        # Arrange: 4 findings - 2 will be processed, 2 will be skipped
        findings = [
            make_finding("finding-1", category="patient"),
            make_finding("finding-2", category="patient"),
            make_finding("finding-3", category="employee"),
            make_finding("finding-4", category="employee"),
        ]

        # LLMService returns partial results + skipped findings
        llm_service.complete.return_value = make_completion_result(
            responses=[
                make_response(
                    [
                        make_llm_result(
                            "finding-1", modifiers=["minor"], confidence=0.9
                        ),
                        make_llm_result("finding-2", modifiers=[], confidence=0.8),
                    ]
                )
            ],
            skipped=[
                SkippedFinding(finding=findings[2], reason=SkipReason.BATCH_ERROR),
                SkippedFinding(finding=findings[3], reason=SkipReason.BATCH_ERROR),
            ],
        )

        # Act
        result = strategy.enrich(findings, run_id)

        # Assert: Partial success - processed findings aggregated, validation marked failed
        assert result.validation_succeeded is False
        assert result.total_findings == 4
        assert result.total_sampled == 2  # Only processed findings counted

        # First two findings (patient category) still present
        assert len(result.category_results) == 1
        assert result.category_results[0].category == "patient"

    def test_returns_fail_safe_result_on_total_failure(
        self,
        strategy: RiskModifierValidationStrategy,
        llm_service: Mock,
        run_id: str,
    ) -> None:
        """Complete failure returns empty category_results with validation_succeeded=False."""
        # Arrange: Findings that will all fail
        findings = [
            make_finding("finding-1", category="patient"),
            make_finding("finding-2", category="employee"),
        ]

        # LLM service raises exception
        llm_service.complete.side_effect = Exception("LLM service unavailable")

        # Act
        result = strategy.enrich(findings, run_id)

        # Assert: Fail-safe result
        assert result.validation_succeeded is False
        assert result.category_results == []
        assert result.total_findings == 2
        assert result.total_sampled == 0
