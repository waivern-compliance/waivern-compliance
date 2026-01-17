"""Unit tests for DataSubjectConfidenceScorer.

This test module focuses on testing the confidence scoring algorithm
for data subject classification.
"""

from waivern_rulesets.data_subject_indicator import DataSubjectRule

from waivern_data_subject_analyser.confidence_scorer import (
    DataSubjectConfidenceScorer,
)


class TestDataSubjectConfidenceScorer:
    """Test suite for DataSubjectConfidenceScorer."""

    def test_confidence_algorithm_correctness(self) -> None:
        """Test confidence algorithm produces correct scores."""
        # Arrange
        scorer = DataSubjectConfidenceScorer()

        # Create test rules with known weights
        test_rules = [
            DataSubjectRule(
                name="primary_rule",
                description="Primary indicator",
                patterns=("employee",),
                subject_category="employee",
                indicator_type="primary",
                confidence_weight=45,
                applicable_contexts=["database"],
            ),
            DataSubjectRule(
                name="secondary_rule",
                description="Secondary indicator",
                patterns=("staff",),
                subject_category="employee",
                indicator_type="secondary",
                confidence_weight=25,
                applicable_contexts=["database"],
            ),
            DataSubjectRule(
                name="contextual_rule",
                description="Contextual indicator",
                patterns=("personnel",),
                subject_category="employee",
                indicator_type="contextual",
                confidence_weight=15,
                applicable_contexts=["database"],
            ),
        ]

        # Act & Assert - Test algorithm: sum of weights, capped at 100
        score = scorer.calculate_confidence(test_rules)
        assert isinstance(score, int)
        assert 0 <= score <= 100

        # Test score calculation algorithm
        expected_score = min(sum(rule.confidence_weight for rule in test_rules), 100)
        assert score == expected_score  # 45 + 25 + 15 = 85

        # Test partial rules
        partial_score = scorer.calculate_confidence(test_rules[:2])
        assert partial_score == 70  # 45 + 25

        single_score = scorer.calculate_confidence(test_rules[:1])
        assert single_score == 45

        # Test edge case: empty rules
        zero_score = scorer.calculate_confidence([])
        assert zero_score == 0
