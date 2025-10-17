"""Unit tests for ruleset types."""

import pytest
from pydantic import ValidationError

from waivern_community.rulesets.types import (
    BaseRule,
)


class TestBaseRule:
    """Test cases for the BaseRule class."""

    def test_base_rule_initialisation_with_required_parameters(self):
        """Test BaseRule initialisation with all required parameters."""
        rule = BaseRule(
            name="test_rule",
            description="A test rule",
            patterns=("pattern1", "pattern2"),
            risk_level="low",
        )

        assert rule.name == "test_rule"
        assert rule.description == "A test rule"
        assert rule.patterns == ("pattern1", "pattern2")

    def test_base_rule_must_contain_at_least_one_pattern(self):
        """Test BaseRule initialisation with empty patterns raises ValidationError."""
        with pytest.raises(
            ValidationError, match="Tuple should have at least 1 item after validation"
        ):
            BaseRule(
                name="empty_rule",
                description="Rule with no patterns",
                patterns=(),
                risk_level="low",
            )

    def test_base_rule_patterns_cannot_be_empty_strings(self):
        """Test BaseRule patterns cannot contain empty strings."""
        with pytest.raises(
            ValidationError, match="All patterns must be non-empty strings"
        ):
            BaseRule(
                name="empty_pattern_rule",
                description="Rule with empty pattern",
                patterns=("valid_pattern", ""),
                risk_level="low",
            )

    def test_base_rule_attributes_are_immutable(self):
        """Test that BaseRule attributes cannot be modified after initialisation."""
        rule = BaseRule(
            name="immutable_rule",
            description="Original description",
            patterns=("original",),
            risk_level="low",
        )

        # Attempt to modify attributes should raise ValidationError (Pydantic frozen)
        with pytest.raises(ValidationError, match="Instance is frozen"):
            rule.name = "modified_rule"

        with pytest.raises(ValidationError, match="Instance is frozen"):
            rule.description = "Modified description"

        with pytest.raises(ValidationError, match="Instance is frozen"):
            rule.patterns = ("modified", "pattern")

        # Original values should remain unchanged
        assert rule.name == "immutable_rule"
        assert rule.description == "Original description"
        assert rule.patterns == ("original",)
