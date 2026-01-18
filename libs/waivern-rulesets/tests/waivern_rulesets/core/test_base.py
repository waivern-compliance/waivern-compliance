"""Unit tests for AbstractRuleset base class."""

import pytest

from waivern_rulesets.core.base import AbstractRuleset
from waivern_rulesets.processing_purposes import ProcessingPurposeRule

from .conftest import ConcreteRuleset


class TestAbstractRuleset:
    """Test cases for the AbstractRuleset abstract base class."""

    def test_ruleset_get_rules_is_abstract(self) -> None:
        """Test that AbstractRuleset.get_rules is an abstract method."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            AbstractRuleset()  # type: ignore[abstract]

    def test_ruleset_initialisation_uses_name_property(self) -> None:
        """Test AbstractRuleset initialisation uses name property."""
        ruleset = ConcreteRuleset()

        assert ruleset.name == "test_ruleset"

    def test_concrete_ruleset_get_rules_returns_list(self) -> None:
        """Test that concrete implementation returns tuple of rules."""
        ruleset = ConcreteRuleset()
        rules = ruleset.get_rules()

        assert isinstance(rules, tuple)
        assert len(rules) == 1
        assert isinstance(rules[0], ProcessingPurposeRule)
        assert rules[0].name == "test_rule"

    def test_concrete_ruleset_has_version(self) -> None:
        """Test that concrete implementation returns version."""
        ruleset = ConcreteRuleset()
        version = ruleset.version

        assert isinstance(version, str)
        assert version == "1.0.0"
