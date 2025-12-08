"""Testing utilities for Waivern Compliance Framework.

This module provides shared testing utilities that can be used across all
framework packages for consistent test patterns and contract validation.
"""

import pytest

from waivern_core import (
    ComponentConfig,
    ComponentFactory,
)
from waivern_core.base_analyser import Analyser


class ComponentFactoryContractTests[T]:
    """Abstract contract tests that all ComponentFactory implementations must pass.

    This class defines behavioural requirements for ComponentFactory implementations.
    Concrete factory test classes should inherit from this to automatically verify
    contract compliance.

    Required Fixtures:
        factory: ComponentFactory instance to test
        valid_config: Valid configuration dict for create() method

    Contract Requirements:
        1. create() must return non-None component instance
        2. component_class must return the component type
        3. can_create() must return boolean for valid config
        4. get_service_dependencies() must return dict

    Usage Pattern:
        class TestMyFactory(ComponentFactoryContractTests[MyComponent]):
            @pytest.fixture
            def factory(self) -> ComponentFactory[MyComponent]:
                return MyFactory(dependencies)

            @pytest.fixture
            def valid_config(self) -> ComponentConfig:
                return {"required_field": "value"}

            # All contract tests run automatically

    Design Decision:
        We use abstract fixtures (raise NotImplementedError) instead of pytest.skip
        because we want inheriting classes to be FORCED to provide implementations.
        This makes the contract explicit and prevents accidental test skipping.

    """

    @pytest.fixture
    def factory(self) -> ComponentFactory[T]:
        """Provide ComponentFactory instance to test.

        Subclasses MUST override this fixture to provide their factory instance
        with all necessary dependencies (LLM service, database pools, etc.).

        Raises:
            NotImplementedError: If subclass doesn't override this fixture

        Example:
            @pytest.fixture
            def factory(self) -> ComponentFactory[PersonalDataAnalyser]:
                llm_service = MockLLMService()
                return PersonalDataAnalyserFactory(llm_service=llm_service)

        """
        raise NotImplementedError(
            "Subclass must provide 'factory' fixture with ComponentFactory instance"
        )

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        """Provide valid configuration for factory.create().

        Subclasses MUST override this fixture to provide configuration that:
        - Passes factory.can_create() validation
        - Successfully creates component via factory.create()
        - Represents realistic runbook configuration

        Raises:
            NotImplementedError: If subclass doesn't override this fixture

        Example:
            @pytest.fixture
            def valid_config(self) -> ComponentConfig:
                return {
                    "pattern_matching": {"ruleset": "personal_data"},
                    "llm_validation": {"enable_llm_validation": True}
                }

        """
        raise NotImplementedError(
            "Subclass must provide 'valid_config' fixture with valid ComponentConfig"
        )

    # CONTRACT TEST 1
    def test_create_returns_component_instance(
        self, factory: ComponentFactory[T], valid_config: ComponentConfig
    ) -> None:
        """Verify factory.create() returns non-None component instance.

        Contract Requirement:
            Factory must successfully create component instance from valid config.
            Returned instance must not be None.

        Why This Matters:
            Executor relies on create() to instantiate components. Returning None
            would cause executor to crash with AttributeError.

        """
        component = factory.create(valid_config)
        assert component is not None, (
            "Factory create() must return component instance, not None"
        )

    # CONTRACT TEST 2
    def test_component_class_returns_type(self, factory: ComponentFactory[T]) -> None:
        """Verify factory.component_class returns the component type.

        Contract Requirement:
            Must return a type (class) that the factory creates.

        Why This Matters:
            Executor uses component_class to access class methods like
            get_input_requirements() and get_supported_output_schemas()
            without instantiating the component.

        """
        component_class = factory.component_class
        assert isinstance(component_class, type), "component_class must return a type"

    # CONTRACT TEST 3
    def test_can_create_returns_bool_for_valid_config(
        self, factory: ComponentFactory[T], valid_config: ComponentConfig
    ) -> None:
        """Verify factory.can_create() returns boolean for valid configuration.

        Contract Requirement:
            Must return bool (True/False), never None or other types.
            Should return True for valid_config fixture.

        Why This Matters:
            Executor calls can_create() before create() to enable graceful
            degradation when services unavailable or config invalid.

        """
        result = factory.can_create(valid_config)
        assert isinstance(result, bool), (
            "can_create() must return boolean, not other types"
        )
        assert result is True, (
            "can_create() should return True for valid_config fixture"
        )

    # CONTRACT TEST 4
    def test_get_service_dependencies_returns_dict(
        self, factory: ComponentFactory[T]
    ) -> None:
        """Verify factory.get_service_dependencies() returns dict mapping.

        Contract Requirement:
            Must return dict (can be empty for factories with no dependencies).
            Dict format: {"dependency_name": ServiceType}

        Why This Matters:
            Enables future auto-wiring capabilities and serves as executable
            documentation of factory service requirements.

        """
        deps = factory.get_service_dependencies()
        assert isinstance(deps, dict), "Service dependencies must be dict type"
        # Cannot assert empty/non-empty as different factories have different needs


class AnalyserContractTests[T: Analyser]:
    """Abstract contract tests that all Analyser implementations must pass.

    This class defines behavioural requirements for Analyser implementations.
    Concrete analyser test classes should inherit from this to automatically
    verify contract compliance.

    Required Fixtures:
        analyser_class: The Analyser class (not instance) to test

    Contract Requirements:
        1. get_input_requirements() must return at least one combination
        2. Each input requirement combination must be unique
        3. Each combination must have at least one requirement

    Usage Pattern:
        class TestPersonalDataAnalyserContract(AnalyserContractTests[PersonalDataAnalyser]):
            @pytest.fixture
            def analyser_class(self) -> type[PersonalDataAnalyser]:
                return PersonalDataAnalyser

            # All contract tests run automatically

    Design Decision:
        We test the class directly (not factory) because input requirements
        are class-level declarations, not instance-level behaviour.

    """

    @pytest.fixture
    def analyser_class(self) -> type[T]:
        """Provide Analyser class to test.

        Subclasses MUST override this fixture to provide their analyser class.

        Raises:
            NotImplementedError: If subclass doesn't override this fixture

        Example:
            @pytest.fixture
            def analyser_class(self) -> type[PersonalDataAnalyser]:
                return PersonalDataAnalyser

        """
        raise NotImplementedError(
            "Subclass must provide 'analyser_class' fixture with Analyser class"
        )

    # CONTRACT TEST 1
    def test_input_requirements_not_empty(self, analyser_class: type[T]) -> None:
        """Verify analyser declares at least one input requirement combination.

        Contract Requirement:
            get_input_requirements() must return at least one combination.

        Why This Matters:
            Planner uses input requirements to match schemas. An analyser with
            no requirements cannot be used in any pipeline.

        """
        requirements = analyser_class.get_input_requirements()
        assert len(requirements) > 0, (
            "get_input_requirements() must return at least one combination"
        )

    # CONTRACT TEST 2
    def test_no_duplicate_combinations(self, analyser_class: type[T]) -> None:
        """Verify each input requirement combination is unique.

        Contract Requirement:
            No two combinations should contain the same set of schemas.

        Why This Matters:
            Duplicate combinations create ambiguity in schema matching.
            Planner cannot determine which combination to use.

        """
        requirements = analyser_class.get_input_requirements()
        seen: set[frozenset[tuple[str, str]]] = set()

        for combo in requirements:
            combo_set = frozenset((r.schema_name, r.version) for r in combo)
            assert combo_set not in seen, f"Duplicate combination: {combo_set}"
            seen.add(combo_set)

    # CONTRACT TEST 3
    def test_no_empty_combinations(self, analyser_class: type[T]) -> None:
        """Verify each combination has at least one requirement.

        Contract Requirement:
            Each combination list must contain at least one InputRequirement.

        Why This Matters:
            Empty combinations are meaningless - an analyser must declare
            what schemas it accepts.

        """
        requirements = analyser_class.get_input_requirements()

        for i, combo in enumerate(requirements):
            assert len(combo) > 0, f"Combination {i} is empty"


__all__ = ["AnalyserContractTests", "ComponentFactoryContractTests"]
