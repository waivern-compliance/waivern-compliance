"""Tests for shared validation decision engine."""

from waivern_core.schemas import BaseFindingEvidence, BaseFindingModel

from waivern_analysers_shared.llm_validation import (
    LLMValidationResultModel,
    RecommendedActionType,
    ValidationDecisionEngine,
)


def _create_test_finding(pattern: str = "test_pattern") -> BaseFindingModel:
    """Create a test finding for validation tests."""
    return BaseFindingModel(
        evidence=[BaseFindingEvidence(content="test content")],
        matched_patterns=[pattern],
    )


class TestValidationDecisionEngine:
    """Test validation decision engine logic."""

    def test_should_keep_true_positive_with_keep_action(self) -> None:
        """Test that TRUE_POSITIVE with keep action is kept."""
        finding = _create_test_finding()
        result = LLMValidationResultModel(
            finding_id=finding.id,
            validation_result="TRUE_POSITIVE",
            confidence=0.9,
            reasoning="Valid finding",
            recommended_action="keep",
        )

        assert ValidationDecisionEngine.should_keep_finding(result, finding) is True

    def test_should_keep_flag_for_review_action(self) -> None:
        """Test that FLAG_FOR_REVIEW action is always kept."""
        finding = _create_test_finding()
        result = LLMValidationResultModel(
            finding_id=finding.id,
            validation_result="TRUE_POSITIVE",  # Even with TRUE_POSITIVE
            confidence=0.7,
            reasoning="Requires manual review",
            recommended_action="flag_for_review",
        )

        assert ValidationDecisionEngine.should_keep_finding(result, finding) is True

    def test_should_discard_false_positive(self) -> None:
        """Test that FALSE_POSITIVE findings are discarded."""
        finding = _create_test_finding("email_example")
        result = LLMValidationResultModel(
            finding_id=finding.id,
            validation_result="FALSE_POSITIVE",
            confidence=0.95,
            reasoning="This is documentation example",
            recommended_action="discard",
        )

        assert ValidationDecisionEngine.should_keep_finding(result, finding) is False

    def test_should_keep_uncertain_findings_conservatively(self) -> None:
        """Test that uncertain findings are kept for safety."""
        finding = _create_test_finding("uncertain_pattern")
        result = LLMValidationResultModel(
            finding_id=finding.id,
            validation_result="UNKNOWN",
            confidence=0.5,
            reasoning="Unclear classification",
            recommended_action="keep",
        )

        # Should keep uncertain findings conservatively
        assert ValidationDecisionEngine.should_keep_finding(result, finding) is True

    def test_handles_various_action_types(self) -> None:
        """Test handling of different recommended action types."""
        finding = _create_test_finding()

        # Test all valid action types
        actions_and_expected: list[tuple[RecommendedActionType, bool]] = [
            ("keep", True),
            ("discard", False),  # Only FALSE_POSITIVE with discard should be False
            ("flag_for_review", True),
        ]

        for action, expected in actions_and_expected:
            result = LLMValidationResultModel(
                finding_id=finding.id,
                validation_result="TRUE_POSITIVE" if expected else "FALSE_POSITIVE",
                recommended_action=action,
            )

            actual = ValidationDecisionEngine.should_keep_finding(result, finding)
            assert actual == expected, f"Action '{action}' should result in {expected}"
