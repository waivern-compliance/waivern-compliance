"""Testing utilities for waivern-rulesets.

This module provides shared testing utilities for ruleset implementations,
following the same pattern as waivern_core.testing.
"""

import pytest
from waivern_core import Rule

from waivern_rulesets.base import AbstractRuleset, RulesetLoader, RulesetRegistry


class RulesetContractTests[RuleType: Rule]:
    """Abstract contract tests that all AbstractRuleset implementations must pass.

    This class defines behavioural requirements for ruleset implementations.
    Concrete ruleset test classes should inherit from this to automatically
    verify contract compliance.

    Required Fixtures:
        ruleset_class: The AbstractRuleset subclass (not instance) to test
        rule_class: The Rule subclass that the ruleset uses
        expected_name: The expected canonical name of the ruleset

    Contract Requirements:
        1. name property must return the expected canonical name
        2. version property must return valid semantic version
        3. get_rules() must return tuple with at least one rule
        4. get_rules() must return consistent count on repeated calls
        5. get_rules() must return same tuple instance (caching)
        6. Rules must be immutable (tuple, not list)
        7. Rule names must be unique
        8. Ruleset must work with RulesetRegistry
        9. Ruleset must work with RulesetLoader

    Usage Pattern:
        class TestMyRulesetContract(RulesetContractTests[MyRule]):
            @pytest.fixture
            def ruleset_class(self) -> type[AbstractRuleset[MyRule]]:
                return MyRuleset

            @pytest.fixture
            def rule_class(self) -> type[MyRule]:
                return MyRule

            @pytest.fixture
            def expected_name(self) -> str:
                return "my_ruleset"

            # All contract tests run automatically

    Design Decision:
        We use abstract fixtures (raise NotImplementedError) instead of pytest.skip
        because we want inheriting classes to be FORCED to provide implementations.
        This makes the contract explicit and prevents accidental test skipping.

    """

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[RuleType]]:
        """Provide AbstractRuleset subclass to test.

        Subclasses MUST override this fixture to provide their ruleset class.

        Raises:
            NotImplementedError: If subclass doesn't override this fixture

        Example:
            @pytest.fixture
            def ruleset_class(self) -> type[AbstractRuleset[PersonalDataRule]]:
                return PersonalDataRuleset

        """
        raise NotImplementedError(
            "Subclass must provide 'ruleset_class' fixture with AbstractRuleset subclass"
        )

    @pytest.fixture
    def rule_class(self) -> type[RuleType]:
        """Provide Rule subclass that the ruleset uses.

        Subclasses MUST override this fixture to provide their rule class.

        Raises:
            NotImplementedError: If subclass doesn't override this fixture

        Example:
            @pytest.fixture
            def rule_class(self) -> type[PersonalDataRule]:
                return PersonalDataRule

        """
        raise NotImplementedError(
            "Subclass must provide 'rule_class' fixture with Rule subclass"
        )

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset.

        Subclasses MUST override this fixture to provide the expected name.

        Raises:
            NotImplementedError: If subclass doesn't override this fixture

        Example:
            @pytest.fixture
            def expected_name(self) -> str:
                return "personal_data"

        """
        raise NotImplementedError(
            "Subclass must provide 'expected_name' fixture with string"
        )

    @pytest.fixture
    def ruleset_instance(
        self, ruleset_class: type[AbstractRuleset[RuleType]]
    ) -> AbstractRuleset[RuleType]:
        """Create a ruleset instance for testing.

        This fixture is automatically provided based on ruleset_class.

        """
        return ruleset_class()

    # =========================================================================
    # CONTRACT TEST: Name property
    # =========================================================================

    def test_name_property_returns_canonical_name(
        self,
        ruleset_instance: AbstractRuleset[RuleType],
        expected_name: str,
    ) -> None:
        """Verify ruleset.name returns the expected canonical name.

        Contract Requirement:
            The name property must return a consistent, canonical name
            that matches the expected value.

        Why This Matters:
            Rulesets are registered by name in the RulesetRegistry.
            Incorrect names would cause lookup failures.

        """
        assert ruleset_instance.name == expected_name

    # =========================================================================
    # CONTRACT TEST: Version property
    # =========================================================================

    def test_version_property_returns_valid_semantic_version(
        self, ruleset_instance: AbstractRuleset[RuleType]
    ) -> None:
        """Verify ruleset.version returns valid semantic version format.

        Contract Requirement:
            Version must be a non-empty string following semantic versioning
            pattern (x.y.z where x, y, z are digits).

        Why This Matters:
            Ruleset URIs include version (e.g., "local/personal_data/1.0.0").
            Invalid versions would break URI parsing.

        """
        version = ruleset_instance.version

        assert isinstance(version, str), "version must be string"
        assert len(version) > 0, "version must not be empty"

        # Version should follow semantic versioning pattern (x.y.z)
        parts = version.split(".")
        assert len(parts) == 3, f"version must have 3 parts (x.y.z), got: {version}"
        assert all(part.isdigit() for part in parts), (
            f"version parts must be digits, got: {version}"
        )

    # =========================================================================
    # CONTRACT TEST: get_rules() returns tuple with rules
    # =========================================================================

    def test_get_rules_returns_tuple_with_at_least_one_rule(
        self,
        ruleset_instance: AbstractRuleset[RuleType],
        rule_class: type[RuleType],
    ) -> None:
        """Verify get_rules() returns tuple with at least one rule.

        Contract Requirement:
            get_rules() must return a tuple (not list) containing at least
            one rule instance of the correct type.

        Why This Matters:
            Empty rulesets are meaningless - they would match nothing.
            Lists would allow mutation, breaking immutability guarantees.

        """
        rules = ruleset_instance.get_rules()

        assert isinstance(rules, tuple), "get_rules() must return tuple, not list"
        assert len(rules) > 0, "get_rules() must return at least one rule"
        assert all(isinstance(rule, rule_class) for rule in rules), (
            f"All rules must be {rule_class.__name__} instances"
        )

    # =========================================================================
    # CONTRACT TEST: get_rules() returns consistent count
    # =========================================================================

    def test_get_rules_returns_consistent_count(
        self, ruleset_instance: AbstractRuleset[RuleType]
    ) -> None:
        """Verify get_rules() returns same count on repeated calls.

        Contract Requirement:
            Multiple calls to get_rules() must return the same number of rules.

        Why This Matters:
            Pattern matching relies on stable rule count. Inconsistent counts
            would cause non-deterministic matching behaviour.

        """
        rules1 = ruleset_instance.get_rules()
        rules2 = ruleset_instance.get_rules()

        assert len(rules1) == len(rules2)

    # =========================================================================
    # CONTRACT TEST: get_rules() returns same tuple instance (caching)
    # =========================================================================

    def test_get_rules_returns_same_tuple_each_time(
        self, ruleset_instance: AbstractRuleset[RuleType]
    ) -> None:
        """Verify get_rules() returns same tuple instance on repeated calls.

        Contract Requirement:
            get_rules() should cache and return the same tuple instance
            on repeated calls, not create new tuples each time.

        Why This Matters:
            Immutability guarantee. Creating new tuples would waste memory
            and break identity comparisons.

        """
        rules1 = ruleset_instance.get_rules()
        rules2 = ruleset_instance.get_rules()

        assert rules1 is rules2, "get_rules() should return same tuple instance"
        assert rules1 == rules2, "get_rules() content should be identical"

    # =========================================================================
    # CONTRACT TEST: Rules are immutable
    # =========================================================================

    def test_rules_are_immutable(
        self, ruleset_instance: AbstractRuleset[RuleType]
    ) -> None:
        """Verify returned rules tuple cannot be modified.

        Contract Requirement:
            The rules tuple must be immutable - no append, clear, or assignment.

        Why This Matters:
            Rulesets are shared across multiple pattern matching operations.
            Mutation would cause thread-safety issues and unpredictable behaviour.

        """
        rules = ruleset_instance.get_rules()

        # Verify it's a tuple (not list)
        assert isinstance(rules, tuple)

        # Attempting to modify should raise AttributeError (tuple has no append/clear)
        with pytest.raises(AttributeError):
            rules.append(None)  # type: ignore[attr-defined]

        with pytest.raises(AttributeError):
            rules.clear()  # type: ignore[attr-defined]

        # Cannot assign to tuple elements
        with pytest.raises(TypeError):
            rules[0] = None  # type: ignore[index]

    # =========================================================================
    # CONTRACT TEST: Rule names are unique
    # =========================================================================

    def test_rule_names_are_unique(
        self, ruleset_instance: AbstractRuleset[RuleType]
    ) -> None:
        """Verify all rule names in the ruleset are unique.

        Contract Requirement:
            No two rules can have the same name.

        Why This Matters:
            Rules are often referenced by name in findings and reports.
            Duplicate names would create ambiguity in rule attribution.

        """
        rules = ruleset_instance.get_rules()
        rule_names = [rule.name for rule in rules]

        assert len(rule_names) == len(set(rule_names)), (
            f"Duplicate rule names found: {[n for n in rule_names if rule_names.count(n) > 1]}"
        )

    # =========================================================================
    # INTEGRATION TEST: Registry compatibility
    # =========================================================================

    def test_ruleset_can_be_used_with_registry(
        self,
        ruleset_class: type[AbstractRuleset[RuleType]],
        rule_class: type[RuleType],
        expected_name: str,
        isolated_registry: RulesetRegistry,
    ) -> None:
        """Verify ruleset works with RulesetRegistry pattern.

        Contract Requirement:
            Ruleset must be registerable and retrievable via RulesetRegistry.

        Why This Matters:
            All rulesets are discovered and loaded via the registry.
            Registry incompatibility would prevent ruleset usage.

        """
        test_registration_name = f"test_{expected_name}"
        isolated_registry.register(test_registration_name, ruleset_class, rule_class)

        # Should be able to retrieve and instantiate
        retrieved_class = isolated_registry.get_ruleset_class(
            test_registration_name, rule_class
        )
        assert retrieved_class is ruleset_class

        instance = retrieved_class()
        assert isinstance(instance, ruleset_class)
        assert instance.name == expected_name

    # =========================================================================
    # INTEGRATION TEST: RulesetLoader compatibility
    # =========================================================================

    def test_ruleset_loader_integration(
        self,
        ruleset_class: type[AbstractRuleset[RuleType]],
        rule_class: type[RuleType],
        expected_name: str,
        isolated_registry: RulesetRegistry,
    ) -> None:
        """Verify ruleset works with RulesetLoader.

        Contract Requirement:
            Ruleset must be loadable via RulesetLoader using URI format.

        Why This Matters:
            Runbooks reference rulesets by URI (e.g., "local/personal_data/1.0.0").
            RulesetLoader is the primary loading mechanism.

        """
        test_registration_name = f"loader_test_{expected_name}"
        isolated_registry.register(test_registration_name, ruleset_class, rule_class)

        # Load via RulesetLoader using URI format
        rules = RulesetLoader.load_ruleset(
            f"local/{test_registration_name}/1.0.0", rule_class
        )

        assert isinstance(rules, tuple)
        assert len(rules) > 0
        assert all(isinstance(rule, rule_class) for rule in rules)

        # Should have the same rules as direct instantiation
        direct_rules = ruleset_class().get_rules()
        assert len(rules) == len(direct_rules)


__all__ = ["RulesetContractTests"]
