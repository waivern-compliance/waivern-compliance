"""Testing utilities for Waivern Compliance Framework.

This module provides shared testing utilities that can be used across all
framework packages for consistent test patterns and contract validation.
"""

import pytest

from waivern_core import (
    ComponentConfig,
    ComponentFactory,
    Schema,
)


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
        2. get_component_name() must return non-empty string
        3. get_input_schemas() must return list of Schema objects
        4. get_output_schemas() must return list of Schema objects
        5. can_create() must return boolean for valid config
        6. get_service_dependencies() must return dict

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
    def test_get_component_name_returns_non_empty_string(
        self, factory: ComponentFactory[T]
    ) -> None:
        """Verify factory.get_component_name() returns non-empty string identifier.

        Contract Requirement:
            Must return string matching runbook YAML 'type:' field.
            String must not be empty (executor needs identifier for registration).

        Why This Matters:
            Executor uses component name to map runbook type declarations
            (e.g., type: "personal_data_analyser") to factory instances.

        """
        name = factory.get_component_name()
        assert isinstance(name, str), "Component name must be string type"
        assert len(name) > 0, "Component name must not be empty string"

    # CONTRACT TEST 3
    def test_get_input_schemas_returns_list_of_schemas(
        self, factory: ComponentFactory[T]
    ) -> None:
        """Verify factory.get_input_schemas() returns list of Schema objects.

        Contract Requirement:
            Must return list (can be empty for connectors).
            All elements must be Schema instances.

        Why This Matters:
            Executor uses input schemas for automatic connector-to-analyser
            matching based on compatible data formats.

        """
        schemas = factory.get_input_schemas()
        assert isinstance(schemas, list), "Input schemas must be list type"
        assert all(isinstance(s, Schema) for s in schemas), (
            "All input schema elements must be Schema instances"
        )

    # CONTRACT TEST 4
    def test_get_output_schemas_returns_list_of_schemas(
        self, factory: ComponentFactory[T]
    ) -> None:
        """Verify factory.get_output_schemas() returns list of Schema objects.

        Contract Requirement:
            Must return list (can be empty for analysers).
            All elements must be Schema instances.

        Why This Matters:
            Executor uses output schemas to validate analyser findings match
            expected formats and enable component chaining.

        """
        schemas = factory.get_output_schemas()
        assert isinstance(schemas, list), "Output schemas must be list type"
        assert all(isinstance(s, Schema) for s in schemas), (
            "All output schema elements must be Schema instances"
        )

    # CONTRACT TEST 5
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

    # CONTRACT TEST 6
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


__all__ = ["ComponentFactoryContractTests"]
