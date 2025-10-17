"""Tests for shared validation decision engine."""

from unittest.mock import Mock

from waivern_community.analysers.llm_validation import (
    LLMValidationResultModel,
    ValidationDecisionEngine,
)


class TestValidationDecisionEngine:
    """Test validation decision engine logic."""

    def test_should_keep_true_positive_with_keep_action(self) -> None:
        """Test that TRUE_POSITIVE with keep action is kept."""
        result = LLMValidationResultModel(
            validation_result="TRUE_POSITIVE",
            confidence=0.9,
            reasoning="Valid finding",
            recommended_action="keep",
        )

        finding = Mock()
        get_identifier = Mock(return_value="test_finding")

        assert (
            ValidationDecisionEngine.should_keep_finding(
                result, finding, get_identifier
            )
            is True
        )

    def test_should_keep_flag_for_review_action(self) -> None:
        """Test that FLAG_FOR_REVIEW action is always kept."""
        result = LLMValidationResultModel(
            validation_result="TRUE_POSITIVE",  # Even with TRUE_POSITIVE
            confidence=0.7,
            reasoning="Requires manual review",
            recommended_action="flag_for_review",
        )

        finding = Mock()
        get_identifier = Mock(return_value="test_finding")

        assert (
            ValidationDecisionEngine.should_keep_finding(
                result, finding, get_identifier
            )
            is True
        )

    def test_should_discard_false_positive(self) -> None:
        """Test that FALSE_POSITIVE findings are discarded."""
        result = LLMValidationResultModel(
            validation_result="FALSE_POSITIVE",
            confidence=0.95,
            reasoning="This is documentation example",
            recommended_action="discard",
        )

        finding = Mock()
        get_identifier = Mock(return_value="email_example")

        # Should return False and log the removal
        assert (
            ValidationDecisionEngine.should_keep_finding(
                result, finding, get_identifier
            )
            is False
        )
        get_identifier.assert_called_once_with(finding)

    def test_should_keep_uncertain_findings_conservatively(self) -> None:
        """Test that uncertain findings are kept for safety."""
        result = LLMValidationResultModel(
            validation_result="UNKNOWN",
            confidence=0.5,
            reasoning="Unclear classification",
            recommended_action="keep",
        )

        finding = Mock()
        get_identifier = Mock(return_value="uncertain_finding")

        # Should keep uncertain findings conservatively
        assert (
            ValidationDecisionEngine.should_keep_finding(
                result, finding, get_identifier
            )
            is True
        )

    def test_handles_various_action_types(self) -> None:
        """Test handling of different recommended action types."""
        finding = Mock()
        get_identifier = Mock(return_value="test_finding")

        # Test all valid action types
        actions_and_expected = [
            ("keep", True),
            ("discard", False),  # Only FALSE_POSITIVE with discard should be False
            ("flag_for_review", True),
        ]

        for action, expected in actions_and_expected:
            result = LLMValidationResultModel(
                validation_result="TRUE_POSITIVE" if expected else "FALSE_POSITIVE",
                recommended_action=action,
            )

            actual = ValidationDecisionEngine.should_keep_finding(
                result, finding, get_identifier
            )
            assert actual == expected, f"Action '{action}' should result in {expected}"
