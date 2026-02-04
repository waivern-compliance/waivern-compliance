"""Tests for shared validation decision engine."""

from waivern_core.schemas import (
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    PatternMatchDetail,
)

from waivern_analysers_shared.llm_validation import (
    LLMValidationResultModel,
    RecommendedActionType,
    ValidationDecisionEngine,
)


def _create_test_finding(
    pattern: str = "test_pattern",
) -> BaseFindingModel[BaseFindingMetadata]:
    """Create a test finding for validation tests."""
    return BaseFindingModel(
        evidence=[BaseFindingEvidence(content="test content")],
        matched_patterns=[PatternMatchDetail(pattern=pattern, match_count=1)],
        metadata=BaseFindingMetadata(source="test_source"),
    )


# =============================================================================
# Individual Finding Decisions
# =============================================================================


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


# =============================================================================
# Group-Level Decisions
# =============================================================================


class TestGroupClassification:
    """Test group-level classification logic."""

    def test_classify_group_returns_keep_all_when_no_validated_samples(self) -> None:
        """Test that groups with no validated samples are kept entirely."""
        assert (
            ValidationDecisionEngine.classify_group(kept_count=0, removed_count=0)
            == "keep_all"
        )

    def test_classify_group_returns_remove_group_when_all_false_positive(self) -> None:
        """Test that groups where all validated samples are FALSE_POSITIVE are removed."""
        assert (
            ValidationDecisionEngine.classify_group(kept_count=0, removed_count=3)
            == "remove_group"
        )
        assert (
            ValidationDecisionEngine.classify_group(kept_count=0, removed_count=1)
            == "remove_group"
        )

    def test_classify_group_returns_keep_partial_when_mixed_results(self) -> None:
        """Test that groups with mixed results keep the group but remove FPs."""
        assert (
            ValidationDecisionEngine.classify_group(kept_count=2, removed_count=1)
            == "keep_partial"
        )
        assert (
            ValidationDecisionEngine.classify_group(kept_count=1, removed_count=2)
            == "keep_partial"
        )

    def test_classify_group_returns_keep_partial_when_all_true_positive(self) -> None:
        """Test that groups with all TRUE_POSITIVE samples keep the group."""
        assert (
            ValidationDecisionEngine.classify_group(kept_count=3, removed_count=0)
            == "keep_partial"
        )
        assert (
            ValidationDecisionEngine.classify_group(kept_count=1, removed_count=0)
            == "keep_partial"
        )
