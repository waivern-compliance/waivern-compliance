"""Tests for GDPRDataSubjectClassifier LLM validation behaviour.

These tests verify the LLM validation integration for risk modifier detection.
Unlike analysers which use LLM for filtering, the classifier uses LLM for
ENRICHMENT: detecting risk modifiers at the category level.

Key behaviour difference:
- Regex path: Per-finding risk modifier detection
- LLM path: Category-level detection → apply to ALL findings in that category
"""

from collections.abc import Sequence
from unittest.mock import AsyncMock, Mock

import pytest
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm.v2 import ItemGroup, LLMCompletionResult, LLMService

from waivern_gdpr_data_subject_classifier.classifier import GDPRDataSubjectClassifier
from waivern_gdpr_data_subject_classifier.schemas import GDPRDataSubjectFindingModel
from waivern_gdpr_data_subject_classifier.types import GDPRDataSubjectClassifierConfig
from waivern_gdpr_data_subject_classifier.validation.models import (
    RiskModifierResultModel,
    RiskModifierValidationResponseModel,
)


class TestGDPRDataSubjectClassifierLLMValidation:
    """Test LLM validation behaviour for risk modifier detection."""

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLM service with async complete method."""
        service = Mock(spec=LLMService)
        service.complete = AsyncMock()
        return service

    @pytest.fixture
    def input_message_with_findings(self) -> Message:
        """Create input message with data subject indicator findings.

        Contains two findings:
        - One 'patient' category finding with evidence mentioning a child
          (word "child" matches 'minor' risk modifier pattern)
        - One 'employee' category finding with neutral evidence
        """
        return Message(
            id="test_input",
            content={
                "findings": [
                    {
                        "subject_category": "patient",
                        "confidence_score": 85,
                        # "child" matches the 'minor' risk modifier pattern
                        "evidence": [{"content": "child patient admitted to ward"}],
                        "matched_patterns": [{"pattern": "patient", "match_count": 1}],
                        "metadata": {"source": "medical_records"},
                    },
                    {
                        "subject_category": "employee",
                        "confidence_score": 90,
                        "evidence": [{"content": "Employee John Smith"}],
                        "matched_patterns": [{"pattern": "employee", "match_count": 1}],
                        "metadata": {"source": "hr_database"},
                    },
                ]
            },
            schema=Schema("data_subject_indicator", "1.0.0"),
            run_id="test-run-id",
        )

    @pytest.fixture
    def input_message_multiple_same_category(self) -> Message:
        """Create input message with multiple findings in the same category.

        Contains three 'patient' findings - used to test category-level application.
        """
        return Message(
            id="test_input_same_cat",
            content={
                "findings": [
                    {
                        "subject_category": "patient",
                        "confidence_score": 85,
                        "evidence": [{"content": "Patient record A"}],
                        "matched_patterns": [{"pattern": "patient", "match_count": 1}],
                        "metadata": {"source": "records_a"},
                    },
                    {
                        "subject_category": "patient",
                        "confidence_score": 80,
                        "evidence": [{"content": "Patient record B"}],
                        "matched_patterns": [{"pattern": "patient", "match_count": 1}],
                        "metadata": {"source": "records_b"},
                    },
                    {
                        "subject_category": "patient",
                        "confidence_score": 75,
                        "evidence": [{"content": "Patient record C"}],
                        "matched_patterns": [{"pattern": "patient", "match_count": 1}],
                        "metadata": {"source": "records_c"},
                    },
                ]
            },
            schema=Schema("data_subject_indicator", "1.0.0"),
            run_id="test-run-id",
        )

    # -------------------------------------------------------------------------
    # LLM Validation Tests
    # -------------------------------------------------------------------------

    def test_process_uses_regex_when_llm_disabled(
        self,
        mock_llm_service: Mock,
        input_message_with_findings: Message,
    ) -> None:
        """When LLM validation disabled, uses regex-based risk detection per-finding.

        The first finding has "child" which should match the 'minor' pattern.
        LLM service should NOT be called.
        """
        # Arrange: LLM validation disabled
        config = GDPRDataSubjectClassifierConfig.from_properties(
            {"llm_validation": {"enable_llm_validation": False}}
        )
        classifier = GDPRDataSubjectClassifier(
            config=config, llm_service=mock_llm_service
        )

        # Act
        result = classifier.process(
            [input_message_with_findings],
            Schema("gdpr_data_subject", "1.0.0"),
        )

        # Assert: LLM not called
        mock_llm_service.complete.assert_not_called()

        # Assert: Regex-based detection found 'minor' in the healthcare finding
        # Note: "patient" indicator category maps to "healthcare" data_subject_category
        findings = result.content["findings"]
        healthcare_finding = next(
            f for f in findings if f["data_subject_category"] == "healthcare"
        )
        assert "minor" in healthcare_finding["risk_modifiers"]

    def test_process_calls_llm_strategy_when_enabled(
        self,
        mock_llm_service: Mock,
        input_message_with_findings: Message,
    ) -> None:
        """When LLM validation enabled, calls the LLM service via strategy."""
        # Arrange: LLM validation enabled
        config = GDPRDataSubjectClassifierConfig.from_properties(
            {"llm_validation": {"enable_llm_validation": True}}
        )

        # Mock LLM to return category-level modifiers
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[
                RiskModifierValidationResponseModel(
                    results=[
                        RiskModifierResultModel(
                            finding_id="any-id",  # Will be matched by strategy
                            risk_modifiers=["minor"],
                            confidence=0.9,
                            reasoning="Test reasoning",
                        )
                    ]
                )
            ],
            skipped=[],
        )

        classifier = GDPRDataSubjectClassifier(
            config=config, llm_service=mock_llm_service
        )

        # Act
        classifier.process(
            [input_message_with_findings],
            Schema("gdpr_data_subject", "1.0.0"),
        )

        # Assert: LLM service was called (via strategy)
        mock_llm_service.complete.assert_called()

    def test_process_applies_category_level_modifiers_from_llm(
        self,
        mock_llm_service: Mock,
        input_message_multiple_same_category: Message,
    ) -> None:
        """LLM-detected modifiers apply to ALL findings in that category.

        When LLM detects 'minor' for the 'healthcare' category, ALL three
        patient findings should get risk_modifiers=['minor'], not just the
        one that was sampled/validated.
        """
        # Arrange: LLM validation enabled
        config = GDPRDataSubjectClassifierConfig.from_properties(
            {"llm_validation": {"enable_llm_validation": True}}
        )

        # We need to capture finding IDs dynamically since they're UUID-generated
        # The strategy will call complete() with ItemGroups containing findings
        def mock_complete_response(
            groups: Sequence[ItemGroup[GDPRDataSubjectFindingModel]],
            **_kwargs: object,
        ) -> LLMCompletionResult[
            GDPRDataSubjectFindingModel, RiskModifierValidationResponseModel
        ]:
            # Extract findings from the ItemGroup to get their IDs
            finding_ids = [item.id for group in groups for item in group.items]

            # Return modifiers for at least one finding per category
            results: list[RiskModifierResultModel] = []
            if finding_ids:
                results.append(
                    RiskModifierResultModel(
                        finding_id=finding_ids[0],
                        risk_modifiers=["minor"],
                        confidence=0.9,
                        reasoning="Child patient detected",
                    )
                )

            return LLMCompletionResult(
                responses=[RiskModifierValidationResponseModel(results=results)],
                skipped=[],
            )

        mock_llm_service.complete.side_effect = mock_complete_response

        classifier = GDPRDataSubjectClassifier(
            config=config, llm_service=mock_llm_service
        )

        # Act
        result = classifier.process(
            [input_message_multiple_same_category],
            Schema("gdpr_data_subject", "1.0.0"),
        )

        # Assert: ALL three findings should have 'minor' modifier
        # (category-level application, not per-finding)
        findings = result.content["findings"]
        assert len(findings) == 3

        for finding in findings:
            assert finding["data_subject_category"] == "healthcare"
            assert "minor" in finding["risk_modifiers"], (
                f"Expected 'minor' in risk_modifiers for all findings, "
                f"got {finding['risk_modifiers']}"
            )

    def test_process_falls_back_to_regex_on_llm_failure(
        self,
        mock_llm_service: Mock,
        input_message_with_findings: Message,
    ) -> None:
        """When LLM validation fails, falls back to regex detection.

        The input has 'child patient' evidence which should match 'minor'
        via regex fallback when LLM fails.
        """
        # Arrange: LLM validation enabled but service will fail
        config = GDPRDataSubjectClassifierConfig.from_properties(
            {"llm_validation": {"enable_llm_validation": True}}
        )

        # LLM service throws exception
        mock_llm_service.complete.side_effect = Exception("LLM service unavailable")

        classifier = GDPRDataSubjectClassifier(
            config=config, llm_service=mock_llm_service
        )

        # Act
        result = classifier.process(
            [input_message_with_findings],
            Schema("gdpr_data_subject", "1.0.0"),
        )

        # Assert: Should fall back to regex and detect 'minor' from 'child' evidence
        findings = result.content["findings"]
        healthcare_finding = next(
            f for f in findings if f["data_subject_category"] == "healthcare"
        )

        # Regex should have detected 'minor' from "child patient" evidence
        assert "minor" in healthcare_finding["risk_modifiers"], (
            f"Expected 'minor' from regex fallback, got {healthcare_finding['risk_modifiers']}"
        )
