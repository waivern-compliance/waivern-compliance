"""Unit tests for RulesetLoader."""

import pytest

from waivern_rulesets.core.exceptions import (
    RulesetNotFoundError,
    UnsupportedProviderError,
)
from waivern_rulesets.core.loader import RulesetLoader
from waivern_rulesets.core.registry import RulesetRegistry
from waivern_rulesets.processing_purposes import ProcessingPurposeRule

from .conftest import ConcreteRuleset, ConcreteRulesetV2


class TestRulesetLoaderProviderValidation:
    """Test suite for provider validation in RulesetLoader."""

    def test_unsupported_provider_raises_error(self) -> None:
        """Test that unsupported providers raise UnsupportedProviderError."""
        with pytest.raises(UnsupportedProviderError, match="remote"):
            RulesetLoader.load_ruleset(
                "remote/personal_data/1.0.0", ProcessingPurposeRule
            )


class TestRulesetLoader:
    """Test cases for the RulesetLoader."""

    def test_load_ruleset_uses_registry(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that load_ruleset uses the singleton registry."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        rules = RulesetLoader.load_ruleset(
            "local/test_ruleset/1.0.0", ProcessingPurposeRule
        )

        assert len(rules) == 1
        assert rules[0].name == "test_rule"

    def test_load_nonexistent_ruleset_raises_error(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that loading a nonexistent ruleset raises RulesetNotFoundError."""
        isolated_registry.clear()

        with pytest.raises(RulesetNotFoundError, match="not registered"):
            RulesetLoader.load_ruleset("local/nonexistent/1.0.0", ProcessingPurposeRule)

    def test_load_specific_version_when_multiple_exist(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test loading correct version when multiple versions registered."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)
        isolated_registry.register(ConcreteRulesetV2, ProcessingPurposeRule)

        # Load v1
        rules_v1 = RulesetLoader.load_ruleset(
            "local/test_ruleset/1.0.0", ProcessingPurposeRule
        )
        assert rules_v1[0].name == "test_rule"

        # Load v2
        rules_v2 = RulesetLoader.load_ruleset(
            "local/test_ruleset/2.0.0", ProcessingPurposeRule
        )
        assert rules_v2[0].name == "test_rule_v2"

    def test_nonexistent_version_error_shows_available_versions(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that error for wrong version shows available versions."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)
        isolated_registry.register(ConcreteRulesetV2, ProcessingPurposeRule)

        with pytest.raises(RulesetNotFoundError, match="Available versions:"):
            RulesetLoader.load_ruleset(
                "local/test_ruleset/9.9.9", ProcessingPurposeRule
            )

    def test_load_ruleset_creates_instance_with_correct_name(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that load_ruleset creates ruleset instance with correct name."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        # load_ruleset_instance returns the instance, not just rules
        instance = RulesetLoader.load_ruleset_instance(
            "local/test_ruleset/1.0.0", ProcessingPurposeRule
        )

        assert instance.name == "test_ruleset"
        assert instance.version == "1.0.0"


class TestRulesetIntegration:
    """Integration tests for ruleset components working together."""

    def test_end_to_end_ruleset_workflow(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test the complete workflow from registration to loading."""
        # 1. Register ruleset
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        # 2. Verify it's registered
        assert isolated_registry.is_registered("test_ruleset", "1.0.0")

        # 3. Load via URI
        rules = RulesetLoader.load_ruleset(
            "local/test_ruleset/1.0.0", ProcessingPurposeRule
        )

        # 4. Verify rules are correct
        assert len(rules) == 1
        assert rules[0].name == "test_rule"

    def test_ruleset_version_accessible_through_loader(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that ruleset version is accessible after loading."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)
        isolated_registry.register(ConcreteRulesetV2, ProcessingPurposeRule)

        # Load v1 instance and check version
        instance_v1 = RulesetLoader.load_ruleset_instance(
            "local/test_ruleset/1.0.0", ProcessingPurposeRule
        )
        assert instance_v1.version == "1.0.0"

        # Load v2 instance and check version
        instance_v2 = RulesetLoader.load_ruleset_instance(
            "local/test_ruleset/2.0.0", ProcessingPurposeRule
        )
        assert instance_v2.version == "2.0.0"
