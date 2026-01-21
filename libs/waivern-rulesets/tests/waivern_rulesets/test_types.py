"""Unit tests for ruleset types."""

import pytest
from pydantic import ValidationError
from waivern_core import DetectionRule


class TestDetectionRule:
    """Test cases for the DetectionRule class."""

    def test_detection_rule_initialisation_with_required_parameters(self) -> None:
        """Test DetectionRule initialisation with all required parameters."""
        rule = DetectionRule(
            name="test_rule",
            description="A test rule",
            patterns=("pattern1", "pattern2"),
        )

        assert rule.name == "test_rule"
        assert rule.description == "A test rule"
        assert rule.patterns == ("pattern1", "pattern2")

    def test_detection_rule_fails_with_neither_pattern_type(self) -> None:
        """Test DetectionRule requires at least one pattern or value_pattern."""
        with pytest.raises(
            ValidationError,
            match="Rule must have at least one pattern or value_pattern",
        ):
            DetectionRule(
                name="empty_rule",
                description="Rule with no patterns",
                patterns=(),
                value_patterns=(),
            )

    def test_detection_rule_initialisation_with_only_value_patterns(self) -> None:
        """Test DetectionRule can be initialised with only value_patterns."""
        rule = DetectionRule(
            name="regex_only_rule",
            description="Rule with only regex patterns",
            value_patterns=(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",),
        )

        assert rule.name == "regex_only_rule"
        assert rule.patterns == ()
        assert rule.value_patterns == (
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        )

    def test_detection_rule_initialisation_with_both_pattern_types(self) -> None:
        """Test DetectionRule can be initialised with both patterns and value_patterns."""
        rule = DetectionRule(
            name="dual_pattern_rule",
            description="Rule with both pattern types",
            patterns=("email", "e_mail"),
            value_patterns=(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",),
        )

        assert rule.name == "dual_pattern_rule"
        assert rule.patterns == ("email", "e_mail")
        assert rule.value_patterns == (
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        )

    def test_detection_rule_value_patterns_cannot_be_empty_strings(self) -> None:
        """Test DetectionRule value_patterns cannot contain empty strings."""
        with pytest.raises(
            ValidationError, match="All patterns must be non-empty strings"
        ):
            DetectionRule(
                name="empty_value_pattern_rule",
                description="Rule with empty value pattern",
                value_patterns=(r"valid_pattern", ""),
            )

    def test_detection_rule_patterns_cannot_be_empty_strings(self) -> None:
        """Test DetectionRule patterns cannot contain empty strings."""
        with pytest.raises(
            ValidationError, match="All patterns must be non-empty strings"
        ):
            DetectionRule(
                name="empty_pattern_rule",
                description="Rule with empty pattern",
                patterns=("valid_pattern", ""),
            )

    def test_detection_rule_attributes_are_immutable(self) -> None:
        """Test that DetectionRule attributes cannot be modified after initialisation."""
        rule = DetectionRule(
            name="immutable_rule",
            description="Original description",
            patterns=("original",),
            value_patterns=("original_regex",),
        )

        # Attempt to modify attributes should raise ValidationError (Pydantic frozen)
        with pytest.raises(ValidationError, match="Instance is frozen"):
            rule.name = "modified_rule"

        with pytest.raises(ValidationError, match="Instance is frozen"):
            rule.description = "Modified description"

        with pytest.raises(ValidationError, match="Instance is frozen"):
            rule.patterns = ("modified", "pattern")

        with pytest.raises(ValidationError, match="Instance is frozen"):
            rule.value_patterns = ("modified_regex",)

        # Original values should remain unchanged
        assert rule.name == "immutable_rule"
        assert rule.description == "Original description"
        assert rule.patterns == ("original",)
        assert rule.value_patterns == ("original_regex",)
