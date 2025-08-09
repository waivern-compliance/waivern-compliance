"""Unit tests for ruleset types."""

import pytest

from wct.rulesets.types import Rule, RuleData


class TestRuleClass:
    """Test cases for the Rule class."""

    def test_rule_initialisation_with_required_parameters(self):
        """Test Rule initialisation with all required parameters."""
        rule = Rule(
            name="test_rule",
            description="A test rule",
            patterns=("pattern1", "pattern2"),
            risk_level="medium",
        )

        assert rule.name == "test_rule"
        assert rule.description == "A test rule"
        assert rule.patterns == ("pattern1", "pattern2")
        assert rule.risk_level == "medium"
        assert rule.metadata == {}

    def test_rule_must_contain_at_least_one_pattern(self):
        """Test Rule initialisation with empty patterns list raises ValueError."""
        with pytest.raises(ValueError, match="Rule must contain at least one pattern"):
            Rule(
                name="empty_rule",
                description="Rule with no patterns",
                patterns=(),
                risk_level="low",
            )

    def test_rule_metadata_defaults_to_empty_dict(self):
        """Test that metadata defaults to empty dict when None is provided."""
        rule = Rule(
            name="test_rule",
            description="Test",
            patterns=("test",),
            risk_level="medium",
        )

        assert rule.metadata == {}

    def test_rule_repr_contains_expected_information(self):
        """Test that Rule.__repr__ contains useful debugging information."""
        metadata = {"data_type": "email", "source": "user_input"}
        rule = Rule(
            name="email_rule",
            description="Email detection",
            patterns=("email", "mail", "e_mail"),
            risk_level="medium",
            metadata=metadata,
        )

        repr_str = repr(rule)

        assert "email_rule" in repr_str
        assert "medium" in repr_str
        assert "e_mail" in repr_str
        assert "user_input" in repr_str
        assert str(metadata) in repr_str

    def test_rule_repr_with_empty_metadata(self):
        """Test Rule.__repr__ with empty metadata."""
        rule = Rule(
            name="simple_rule",
            description="Simple test rule",
            patterns=("test",),
            risk_level="low",
        )

        repr_str = repr(rule)

        assert "simple_rule" in repr_str
        assert "low" in repr_str
        assert "{}" in repr_str  # empty metadata

    def test_rule_attributes_are_immutable(self):
        """Test that Rule attributes cannot be modified after initialisation."""
        rule = Rule(
            name="immutable_rule",
            description="Original description",
            patterns=("original",),
            risk_level="low",
        )

        # Attempt to modify attributes should raise AttributeError
        with pytest.raises(AttributeError):
            setattr(rule, "name", "modified_rule")

        with pytest.raises(AttributeError):
            setattr(rule, "description", "Modified description")

        with pytest.raises(AttributeError):
            setattr(rule, "patterns", ("modified", "pattern"))

        with pytest.raises(AttributeError):
            setattr(rule, "risk_level", "high")

        with pytest.raises(AttributeError):
            setattr(rule, "metadata", {"modified": True})

        # Original values should remain unchanged
        assert rule.name == "immutable_rule"
        assert rule.description == "Original description"
        assert rule.patterns == ("original",)
        assert rule.risk_level == "low"
        assert rule.metadata == {}


class TestRuleDataTypedDict:
    """Test cases for the RuleData TypedDict."""

    def test_rule_data_structure_matches_expected_keys(self):
        """Test that RuleData has the expected structure."""
        # This tests the TypedDict structure by creating a valid instance
        rule_data: RuleData = {
            "description": "Test description",
            "patterns": ["pattern1", "pattern2"],
            "risk_level": "medium",
            "metadata": {"data_type": "test"},
        }

        assert rule_data["description"] == "Test description"
        assert rule_data["patterns"] == ["pattern1", "pattern2"]
        assert rule_data["risk_level"] == "medium"
        assert rule_data["metadata"] == {"data_type": "test"}

    def test_rule_data_metadata_can_contain_various_types(self):
        """Test that RuleData metadata can contain different value types."""
        rule_data: RuleData = {
            "description": "Mixed metadata types",
            "patterns": ["test"],
            "risk_level": "medium",
            "metadata": {
                "string_value": "test",
                "int_value": 42,
                "bool_value": True,
                "list_value": [1, 2, 3],
                "dict_value": {"nested": "value"},
            },
        }

        metadata = rule_data["metadata"]
        assert metadata["string_value"] == "test"
        assert metadata["int_value"] == 42  # noqa: PLR2004
        assert metadata["bool_value"] is True
        assert metadata["list_value"] == [1, 2, 3]
        assert metadata["dict_value"] == {"nested": "value"}
