"""Contract tests for ComponentFactory abstract base class.

This module uses the CONTRACT TESTING PATTERN to define behavioural requirements
that all ComponentFactory implementations must satisfy. Contract tests ensure
that PersonalDataAnalyserFactory, MySQLConnectorFactory, and future factories
behave consistently and correctly.

## Contract Testing Pattern

Contract testing is a strategy for testing abstract interfaces where:
1. Base test class defines the "contract" (expected behaviour)
2. Concrete test classes inherit the contract tests
3. Each implementation must pass all inherited contract tests

This pattern is superior to mock-based testing because:
- Tests REAL implementations, not mock behaviour
- Catches implementation bugs in actual factories
- Ensures consistent behaviour across all factory types
- Documents expected behaviour as executable specifications

## When Contract Tests Run

**Phase 2 (Current):** Only TestComponentFactoryDefaults runs (tests default method)
**Phase 4-5 (Future):** Real factory tests inherit ComponentFactoryContractTests

Example:
    >>> # Phase 4 - PersonalDataAnalyser factory tests
    >>> class TestPersonalDataAnalyserFactory(
    ...     ComponentFactoryContractTests[PersonalDataAnalyser]
    ... ):
    ...     @pytest.fixture
    ...     def factory(self) -> ComponentFactory[PersonalDataAnalyser]:
    ...         llm_service = create_mock_llm()
    ...         return PersonalDataAnalyserFactory(llm_service=llm_service)
    ...
    ...     @pytest.fixture
    ...     def valid_config(self) -> ComponentConfig:
    ...         return {"pattern_matching": {"ruleset": "personal_data"}}
    ...
    ...     # All 7 contract tests inherited automatically!
    ...     # Plus factory-specific tests here...

## Why Not Test Mocks?

Testing mock implementations (ConcreteTestFactory) is an anti-pattern because:
- Mock passes but real implementation might fail
- Tests mock behaviour, not framework behaviour
- Provides false confidence in untested code
- Wastes time maintaining tests that don't catch real bugs

See: docs/architecture/di-factory-patterns.md for DI architecture details.

References:
    - Contract Testing: https://martinfowler.com/bliki/ContractTest.html
    - Gist Example: https://gist.github.com/abele/ee049b1fdf7e4a1af71a

"""

from typing import override

import pytest

from waivern_core import (
    BaseComponentConfiguration,
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
        6. can_create() must return boolean for invalid config
        7. get_service_dependencies() must return dict

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
    ):
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
    ):
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
    ):
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
    ):
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
    ):
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
    def test_can_create_returns_bool_for_invalid_config(
        self, factory: ComponentFactory[T]
    ):
        """Verify factory.can_create() returns boolean for invalid configuration.

        Contract Requirement:
            Must return bool (True/False), even for invalid config.
            Must not raise exceptions (validation errors returned as False).

        Why This Matters:
            Executor needs to check multiple factories to find compatible ones.
            Exceptions would break discovery process; False enables graceful skip.

        """
        # Empty config should be invalid for most factories
        invalid_config = BaseComponentConfiguration()
        result = factory.can_create(invalid_config)
        assert isinstance(result, bool), (
            "can_create() must return boolean even for invalid config, "
            "not raise exception"
        )

    # CONTRACT TEST 7
    def test_get_service_dependencies_returns_dict(self, factory: ComponentFactory[T]):
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


class TestComponentFactoryDefaults:
    """Test default implementations in ComponentFactory ABC.

    Unlike ComponentFactoryContractTests (which runs via inheritance in Phase 4-5),
    these tests run NOW in Phase 2 to verify the default method implementation.

    Design Note:
        Only test methods with CONCRETE implementations in the ABC.
        - get_service_dependencies() has default: return {}
        - All other methods are @abstractmethod with no implementation to test

    """

    def test_get_service_dependencies_default_returns_empty_dict(self):
        """Verify get_service_dependencies() default implementation returns empty dict.

        Tests the default implementation provided by ComponentFactory ABC.
        Factories can override this to declare their dependencies.

        Why This Test Exists:
            This is the ONLY method with a concrete implementation in the ABC.
            We must verify the default behaviour works correctly.

        """

        # Create minimal concrete implementation to test default
        class MinimalFactory(ComponentFactory[object]):
            """Minimal factory with only abstract methods implemented."""

            @override
            def create(self, config: ComponentConfig) -> object:
                """Create dummy component."""
                return object()  # Dummy return

            @override
            def get_component_name(self) -> str:
                """Return component name."""
                return "minimal"

            @override
            def get_input_schemas(self) -> list[Schema]:
                """Return empty input schemas."""
                return []

            @override
            def get_output_schemas(self) -> list[Schema]:
                """Return empty output schemas."""
                return []

            @override
            def can_create(self, config: ComponentConfig) -> bool:
                """Always returns True."""
                return True

            # get_service_dependencies() NOT overridden - uses default

        factory = MinimalFactory()
        deps = factory.get_service_dependencies()

        assert deps == {}, (
            "Default get_service_dependencies() implementation must return empty dict"
        )
        assert isinstance(deps, dict), "Must return dict type, not None or other types"
