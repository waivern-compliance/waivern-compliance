"""Tests for RiskModifierValidationStrategy.

Tests focus on the NEW behaviour specific to this strategy:
- Category-level aggregation of modifiers
- Union semantics for combining modifiers
- Average confidence calculation
- Failure handling

Base class behaviours (batching, error routing) are already tested in
waivern-analysers-shared and are NOT re-tested here.
"""

from unittest.mock import Mock

import pytest
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail
from waivern_llm import BaseLLMService
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
    def strategy(
        self, available_modifiers: list[RiskModifier]
    ) -> RiskModifierValidationStrategy:
        """Create strategy instance with test modifiers."""
        return RiskModifierValidationStrategy(available_modifiers=available_modifiers)

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
    # Category-Level Aggregation
    # -------------------------------------------------------------------------

    def test_aggregates_modifiers_by_category(
        self,
        strategy: RiskModifierValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
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
        llm_service.invoke_with_structured_output.return_value = make_response(
            [
                make_llm_result("finding-1", modifiers=["minor"], confidence=0.9),
                make_llm_result(
                    "finding-2", modifiers=["vulnerable_individual"], confidence=0.8
                ),
            ]
        )

        # Act
        result = strategy.validate_findings(findings, config, llm_service)

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
        config: LLMValidationConfig,
        llm_service: Mock,
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
        llm_service.invoke_with_structured_output.return_value = make_response(
            [
                make_llm_result("finding-1", modifiers=["minor"]),
                make_llm_result("finding-2", modifiers=["vulnerable_individual"]),
                make_llm_result(
                    "finding-3", modifiers=["minor", "vulnerable_individual"]
                ),  # Both
            ]
        )

        # Act
        result = strategy.validate_findings(findings, config, llm_service)

        # Assert: Single category with union of all modifiers (no duplicates, sorted)
        assert len(result.category_results) == 1

        patient_result = result.category_results[0]
        assert patient_result.category == "patient"
        assert patient_result.detected_modifiers == ["minor", "vulnerable_individual"]
        assert patient_result.sample_count == 3

    def test_calculates_average_confidence_per_category(
        self,
        strategy: RiskModifierValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """Category confidence is the average of all finding confidences in that category."""
        # Arrange: Two findings in same category with different confidences
        findings = [
            make_finding("finding-1", category="patient"),
            make_finding("finding-2", category="patient"),
        ]

        # LLM returns different confidence scores: 0.8 and 0.6 → average = 0.7
        llm_service.invoke_with_structured_output.return_value = make_response(
            [
                make_llm_result("finding-1", modifiers=["minor"], confidence=0.8),
                make_llm_result("finding-2", modifiers=["minor"], confidence=0.6),
            ]
        )

        # Act
        result = strategy.validate_findings(findings, config, llm_service)

        # Assert: Confidence is average of 0.8 and 0.6
        assert len(result.category_results) == 1
        assert abs(result.category_results[0].confidence - 0.7) < 1e-9

    # -------------------------------------------------------------------------
    # Failure Handling
    # -------------------------------------------------------------------------

    def test_marks_validation_failed_when_any_batch_fails(
        self,
        strategy: RiskModifierValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """When some batches fail, validation_succeeded is False and counts are correct."""
        # Arrange: 4 findings with batch_size=2 → 2 batches
        findings = [
            make_finding("finding-1", category="patient"),
            make_finding("finding-2", category="patient"),
            make_finding("finding-3", category="employee"),
            make_finding("finding-4", category="employee"),
        ]
        config.llm_batch_size = 2

        # First batch succeeds, second batch fails
        llm_service.invoke_with_structured_output.side_effect = [
            make_response(
                [
                    make_llm_result("finding-1", modifiers=["minor"], confidence=0.9),
                    make_llm_result("finding-2", modifiers=[], confidence=0.8),
                ]
            ),
            Exception("LLM service unavailable"),
        ]

        # Act
        result = strategy.validate_findings(findings, config, llm_service)

        # Assert: Partial success
        assert result.validation_succeeded is False
        assert result.total_findings == 4  # All findings counted
        assert result.total_sampled == 2  # Only first batch sampled

        # First batch results still present
        assert len(result.category_results) == 1
        assert result.category_results[0].category == "patient"

    def test_returns_fail_safe_result_on_total_failure(
        self,
        strategy: RiskModifierValidationStrategy,
        config: LLMValidationConfig,
        llm_service: Mock,
    ) -> None:
        """Complete failure returns empty category_results with validation_succeeded=False."""
        # Arrange: Findings that will all fail
        findings = [
            make_finding("finding-1", category="patient"),
            make_finding("finding-2", category="employee"),
        ]

        # LLM fails for all batches
        llm_service.invoke_with_structured_output.side_effect = Exception(
            "LLM service unavailable"
        )

        # Act
        result = strategy.validate_findings(findings, config, llm_service)

        # Assert: Fail-safe result
        assert result.validation_succeeded is False
        assert result.category_results == []
        assert result.total_findings == 2
        assert result.total_sampled == 0
