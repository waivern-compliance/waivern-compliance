"""Unit tests for ruleset base classes and utilities."""

from typing import ClassVar, override

import pytest

from waivern_rulesets.base import (
    AbstractRuleset,
    RulesetLoader,
    RulesetNotFoundError,
    RulesetRegistry,
    RulesetURI,
    RulesetURIParseError,
    UnsupportedProviderError,
)
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


class TestRulesetClass:
    """Test cases for the Ruleset abstract base class."""

    def test_ruleset_get_rules_is_abstract(self) -> None:
        """Test that Ruleset.get_rules is an abstract method."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            AbstractRuleset()  # type: ignore[abstract]

    def test_ruleset_initialisation_uses_name_property(self) -> None:
        """Test Ruleset initialisation uses name property."""
        ruleset = ConcreteRuleset()

        assert ruleset.name == "test_ruleset"

    def test_concrete_ruleset_get_rules_returns_list(self) -> None:
        """Test that concrete implementation returns list of rules."""
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


# =============================================================================
# RulesetURI Parsing Tests
# =============================================================================


class TestRulesetURIParsing:
    """Test suite for ruleset URI parsing."""

    def test_parse_valid_uri(self) -> None:
        """Test parsing a valid URI format."""
        uri = RulesetURI.parse("local/personal_data/1.0.0")

        assert uri.provider == "local"
        assert uri.name == "personal_data"
        assert uri.version == "1.0.0"

    def test_parse_uri_with_different_versions(self) -> None:
        """Test parsing URIs with various version formats."""
        uri = RulesetURI.parse("local/processing_purposes/2.1.0")

        assert uri.provider == "local"
        assert uri.name == "processing_purposes"
        assert uri.version == "2.1.0"

    def test_parse_uri_rejects_missing_components(self) -> None:
        """Test that URIs with missing components are rejected."""
        with pytest.raises(RulesetURIParseError, match="Invalid ruleset URI format"):
            RulesetURI.parse("personal_data")

        with pytest.raises(RulesetURIParseError, match="Invalid ruleset URI format"):
            RulesetURI.parse("local/personal_data")

    def test_parse_uri_rejects_empty_components(self) -> None:
        """Test that URIs with empty components are rejected."""
        with pytest.raises(RulesetURIParseError, match="Invalid ruleset URI format"):
            RulesetURI.parse("//1.0.0")

        with pytest.raises(RulesetURIParseError, match="Invalid ruleset URI format"):
            RulesetURI.parse("local//1.0.0")

    def test_parse_uri_rejects_extra_components(self) -> None:
        """Test that URIs with extra components are rejected."""
        with pytest.raises(RulesetURIParseError, match="Invalid ruleset URI format"):
            RulesetURI.parse("local/personal_data/1.0.0/extra")

    def test_uri_str_representation(self) -> None:
        """Test string representation of RulesetURI."""
        uri = RulesetURI.parse("local/personal_data/1.0.0")
        assert str(uri) == "local/personal_data/1.0.0"


class TestRulesetLoaderProviderValidation:
    """Test suite for provider validation in RulesetLoader."""

    def test_unsupported_provider_raises_error(self) -> None:
        """Test that unsupported providers raise UnsupportedProviderError."""
        with pytest.raises(UnsupportedProviderError, match="remote"):
            RulesetLoader.load_ruleset(
                "remote/personal_data/1.0.0", ProcessingPurposeRule
            )


class TestRulesetRegistry:
    """Test cases for the RulesetRegistry singleton."""

    def test_registry_is_singleton(self) -> None:
        """Test that RulesetRegistry implements singleton pattern."""
        registry1 = RulesetRegistry()
        registry2 = RulesetRegistry()

        assert registry1 is registry2

    def test_registry_can_be_cleared_to_empty(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that registry can be cleared to empty state."""
        # Clear registry for this specific test that needs empty state
        isolated_registry.clear()

        assert isolated_registry.is_empty()

    def test_register_extracts_name_version_from_class(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that register() auto-extracts name and version from ClassVars."""
        # New API: register(ruleset_class, rule_type) - no name argument
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        # Should be retrievable using ClassVar values (name + version)
        retrieved = isolated_registry.get_ruleset_class(
            "test_ruleset", "1.0.0", ProcessingPurposeRule
        )
        assert retrieved is ConcreteRuleset

    def test_register_makes_ruleset_retrievable(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test registering a ruleset makes it retrievable."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        retrieved = isolated_registry.get_ruleset_class(
            "test_ruleset", "1.0.0", ProcessingPurposeRule
        )

        assert retrieved is ConcreteRuleset

    def test_register_rejects_ruleset_missing_name(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that register() rejects rulesets without ruleset_name ClassVar."""
        with pytest.raises(ValueError, match="must define 'ruleset_name' ClassVar"):
            isolated_registry.register(RulesetMissingName, ProcessingPurposeRule)

    def test_register_rejects_ruleset_missing_version(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that register() rejects rulesets without ruleset_version ClassVar."""
        with pytest.raises(ValueError, match="must define 'ruleset_version' ClassVar"):
            isolated_registry.register(RulesetMissingVersion, ProcessingPurposeRule)

    def test_get_ruleset_class_requires_version(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that get_ruleset_class() requires version parameter."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        # Should work with correct version
        result = isolated_registry.get_ruleset_class(
            "test_ruleset", "1.0.0", ProcessingPurposeRule
        )
        assert result is ConcreteRuleset

        # Should fail with wrong version
        with pytest.raises(
            RulesetNotFoundError, match="version '9.9.9' not registered"
        ):
            isolated_registry.get_ruleset_class(
                "test_ruleset", "9.9.9", ProcessingPurposeRule
            )

    def test_get_unregistered_ruleset_raises_error(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that getting an unregistered ruleset raises RulesetNotFoundError."""
        isolated_registry.clear()

        with pytest.raises(RulesetNotFoundError, match="not registered"):
            isolated_registry.get_ruleset_class(
                "nonexistent", "1.0.0", ProcessingPurposeRule
            )

    def test_same_name_different_versions_both_registered(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that same ruleset name with different versions can coexist."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)
        isolated_registry.register(ConcreteRulesetV2, ProcessingPurposeRule)

        # Both versions should be retrievable
        v1 = isolated_registry.get_ruleset_class(
            "test_ruleset", "1.0.0", ProcessingPurposeRule
        )
        v2 = isolated_registry.get_ruleset_class(
            "test_ruleset", "2.0.0", ProcessingPurposeRule
        )

        assert v1 is ConcreteRuleset
        assert v2 is ConcreteRulesetV2
        assert v1 is not v2

    def test_registry_is_idempotent_for_duplicate_registration(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that registering same name+version is idempotent (no error)."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        # Second registration should silently succeed (idempotent)
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        # Should still be retrievable
        retrieved = isolated_registry.get_ruleset_class(
            "test_ruleset", "1.0.0", ProcessingPurposeRule
        )
        assert retrieved is ConcreteRuleset

    def test_is_registered_requires_version(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that is_registered() checks name+version combination."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        # Correct name+version
        assert isolated_registry.is_registered("test_ruleset", "1.0.0") is True

        # Wrong version
        assert isolated_registry.is_registered("test_ruleset", "9.9.9") is False

        # Wrong name
        assert isolated_registry.is_registered("nonexistent", "1.0.0") is False

    def test_get_available_versions_returns_all_versions(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that get_available_versions() lists all versions for a name."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)
        isolated_registry.register(ConcreteRulesetV2, ProcessingPurposeRule)

        versions = isolated_registry.get_available_versions("test_ruleset")

        assert set(versions) == {"1.0.0", "2.0.0"}

    def test_get_available_versions_returns_empty_for_unknown(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that get_available_versions() returns empty tuple for unknown name."""
        isolated_registry.clear()

        versions = isolated_registry.get_available_versions("nonexistent")

        assert versions == ()


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
        assert rules[0].purpose_category == "OPERATIONAL"

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
