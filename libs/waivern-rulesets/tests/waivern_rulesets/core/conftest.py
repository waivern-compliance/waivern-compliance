"""Shared test fixtures for core module tests."""

from typing import ClassVar, override

from waivern_rulesets.core.base import AbstractRuleset
from waivern_rulesets.processing_purposes import ProcessingPurposeRule


class ConcreteRuleset(AbstractRuleset[ProcessingPurposeRule]):
    """Concrete implementation of Ruleset for testing using ClassVars."""

    ruleset_name: ClassVar[str] = "test_ruleset"
    ruleset_version: ClassVar[str] = "1.0.0"

    @property
    @override
    def name(self) -> str:
        """Return test name."""
        return self.ruleset_name

    @property
    @override
    def version(self) -> str:
        """Return test version."""
        return self.ruleset_version

    @override
    def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
        """Return a test rule."""
        return (
            ProcessingPurposeRule(
                name="test_rule",
                description="Test rule for unit tests",
                patterns=("test_pattern", "test_pattern_2"),
                purpose_category="OPERATIONAL",
            ),
        )


class ConcreteRulesetV2(AbstractRuleset[ProcessingPurposeRule]):
    """Version 2.0.0 of the test ruleset for multi-version testing."""

    ruleset_name: ClassVar[str] = "test_ruleset"
    ruleset_version: ClassVar[str] = "2.0.0"

    @property
    @override
    def name(self) -> str:
        """Return test name."""
        return self.ruleset_name

    @property
    @override
    def version(self) -> str:
        """Return test version."""
        return self.ruleset_version

    @override
    def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
        """Return v2 test rules."""
        return (
            ProcessingPurposeRule(
                name="test_rule_v2",
                description="Test rule for v2",
                patterns=("v2_pattern",),
                purpose_category="MARKETING",
            ),
        )


class RulesetMissingName(AbstractRuleset[ProcessingPurposeRule]):
    """Ruleset without ruleset_name ClassVar for testing validation."""

    ruleset_version: ClassVar[str] = "1.0.0"

    @property
    @override
    def name(self) -> str:
        """Return test name."""
        return "missing_name"

    @property
    @override
    def version(self) -> str:
        """Return test version."""
        return self.ruleset_version

    @override
    def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
        """Return empty rules."""
        return ()


class RulesetMissingVersion(AbstractRuleset[ProcessingPurposeRule]):
    """Ruleset without ruleset_version ClassVar for testing validation."""

    ruleset_name: ClassVar[str] = "missing_version"

    @property
    @override
    def name(self) -> str:
        """Return test name."""
        return self.ruleset_name

    @property
    @override
    def version(self) -> str:
        """Return test version."""
        return "1.0.0"

    @override
    def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
        """Return empty rules."""
        return ()
