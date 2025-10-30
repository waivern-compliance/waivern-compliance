"""Tests for WCT Executor.

These tests focus on the public interface of the Executor class, testing
various scenarios and error conditions without testing internal methods.
The tests use real connectors and analysers to ensure proper integration.
"""

import tempfile
from pathlib import Path
from typing import Any, override
from unittest.mock import MagicMock

import pytest
from waivern_community.analysers import Analyser, AnalyserError
from waivern_community.connectors import (
    Connector,
    ConnectorError,
)
from waivern_core.component_factory import ComponentConfig, ComponentFactory
from waivern_core.message import Message
from waivern_core.services.container import ServiceContainer

from wct.executor import Executor, ExecutorError
from wct.schemas import PersonalDataFindingSchema, Schema, StandardInputSchema


class MockConnector(Connector):
    """Mock connector for testing purposes."""

    def __init__(self, extract_result: Any = None, should_fail: bool = False) -> None:
        super().__init__()
        self.extract_result = extract_result
        self.should_fail = should_fail

    @classmethod
    @override
    def get_name(cls) -> str:
        return "mock_connector"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> "MockConnector":
        return cls()

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [StandardInputSchema()]

    @override
    def extract(self, output_schema: Schema):
        if self.should_fail:
            raise ConnectorError("Mock connector failure")

        return Message(
            id="mock_connector_message",
            content=self.extract_result
            or {"files": [{"path": "test.txt", "content": "test data"}]},
            schema=output_schema,
        )


class MockAnalyser(Analyser):
    """Mock analyser for testing purposes."""

    def __init__(self, process_result: Any = None, should_fail: bool = False) -> None:
        super().__init__()
        self.process_result = process_result
        self.should_fail = should_fail

    @classmethod
    @override
    def get_name(cls) -> str:
        return "mock_analyser"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> "MockAnalyser":
        return cls()

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[Schema]:
        return [StandardInputSchema()]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [PersonalDataFindingSchema()]

    @override
    def process(self, input_schema: Schema, output_schema: Schema, message: Any):
        if self.should_fail:
            raise AnalyserError("Mock analyser failure")

        return Message(
            id="mock_analyser_result",
            content=self.process_result or {"findings": []},
            schema=output_schema,
        )


class MockConnectorFactory(ComponentFactory[MockConnector]):
    """Factory for creating MockConnector instances."""

    @override
    def create(self, config: ComponentConfig) -> MockConnector:
        return MockConnector()

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        return True

    @override
    def get_component_name(self) -> str:
        return "mock_connector"

    @override
    def get_input_schemas(self) -> list[Schema]:
        return []

    @override
    def get_output_schemas(self) -> list[Schema]:
        return [StandardInputSchema()]

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        return {}


class MockAnalyserFactory(ComponentFactory[MockAnalyser]):
    """Factory for creating MockAnalyser instances."""

    @override
    def create(self, config: ComponentConfig) -> MockAnalyser:
        return MockAnalyser()

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        return True

    @override
    def get_component_name(self) -> str:
        return "mock_analyser"

    @override
    def get_input_schemas(self) -> list[Schema]:
        return [StandardInputSchema()]

    @override
    def get_output_schemas(self) -> list[Schema]:
        return [PersonalDataFindingSchema()]

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        return {}


class TestExecutor:
    """Tests for Executor class."""

    def _create_executor_with_mocks(self) -> Executor:
        """Create executor with mock factories registered."""
        # Create minimal container (mocks don't need services)
        container = ServiceContainer()
        executor = Executor(container)

        # Register mock factories
        executor.register_connector_factory(MockConnectorFactory())
        executor.register_analyser_factory(MockAnalyserFactory())

        return executor

    def _execute_runbook_yaml(self, executor: Executor, yaml_content: str) -> list[Any]:
        """Execute a runbook from YAML string, handling temp file creation/cleanup."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            runbook_path = Path(f.name)

        try:
            return executor.execute_runbook(runbook_path)
        finally:
            runbook_path.unlink()

    def test_executor_initialisation(self) -> None:
        """Test executor initialises correctly with empty factory registries."""
        container = ServiceContainer()
        executor = Executor(container)

        assert executor.connector_factories == {}
        assert executor.analyser_factories == {}

    def test_register_available_connector(self) -> None:
        """Test registering a connector factory."""
        container = ServiceContainer()
        executor = Executor(container)

        mock_factory = MockConnectorFactory()
        executor.register_connector_factory(mock_factory)

        assert "mock_connector" in executor.connector_factories
        assert executor.connector_factories["mock_connector"] == mock_factory

    def test_register_available_analyser(self) -> None:
        """Test registering an analyser factory."""
        container = ServiceContainer()
        executor = Executor(container)

        mock_factory = MockAnalyserFactory()
        executor.register_analyser_factory(mock_factory)

        assert "mock_analyser" in executor.analyser_factories
        assert executor.analyser_factories["mock_analyser"] == mock_factory

    def test_list_available_connectors(self) -> None:
        """Test listing available connector factories."""
        container = ServiceContainer()
        executor = Executor(container)
        mock_factory = MockConnectorFactory()
        executor.register_connector_factory(mock_factory)

        connectors = executor.list_available_connectors()

        assert "mock_connector" in connectors
        assert connectors["mock_connector"] == mock_factory

        # Ensure returned dict is a copy
        connectors.clear()
        assert "mock_connector" in executor.connector_factories

    def test_list_available_analysers(self) -> None:
        """Test listing available analyser factories."""
        container = ServiceContainer()
        executor = Executor(container)
        mock_factory = MockAnalyserFactory()
        executor.register_analyser_factory(mock_factory)

        analysers = executor.list_available_analysers()

        assert "mock_analyser" in analysers
        assert analysers["mock_analyser"] == mock_factory

        # Ensure returned dict is a copy
        analysers.clear()
        assert "mock_analyser" in executor.analyser_factories

    def test_execute_runbook_file_not_found(self) -> None:
        """Test executing a non-existent runbook file."""
        executor = self._create_executor_with_mocks()
        non_existent_path = Path("/path/that/does/not/exist.yaml")

        with pytest.raises(ExecutorError, match="Failed to load runbook"):
            executor.execute_runbook(non_existent_path)

    def test_execute_runbook_invalid_yaml(self) -> None:
        """Test executing a runbook with invalid YAML."""
        executor = self._create_executor_with_mocks()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content:")
            invalid_yaml_path = Path(f.name)

        try:
            with pytest.raises(ExecutorError, match="Failed to load runbook"):
                executor.execute_runbook(invalid_yaml_path)
        finally:
            invalid_yaml_path.unlink()

    def test_execute_runbook_unknown_analyser_type(self) -> None:
        """Test execution fails gracefully with unknown analyser type."""
        container = ServiceContainer()
        executor = Executor(container)
        executor.register_connector_factory(MockConnectorFactory())

        # Create a valid runbook with unknown analyser type
        runbook_content = """
name: Test Runbook
description: Test with unknown analyser
connectors:
  - name: test_connector
    type: mock_connector
    properties: {}
analysers:
  - name: test_analyser
    type: unknown_analyser_type
    properties: {}
execution:
  - name: "Test execution with unknown analyser"
    description: "Testing error handling for unknown analyser type"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.error_message is not None
        assert "Unknown analyser type: unknown_analyser_type" in result.error_message
        assert result.analysis_name == "Test execution with unknown analyser"

    def test_execute_runbook_unknown_connector_type(self) -> None:
        """Test execution fails gracefully with unknown connector type."""
        container = ServiceContainer()
        executor = Executor(container)
        executor.register_analyser_factory(MockAnalyserFactory())

        # Create a valid runbook with unknown connector type
        runbook_content = """
name: Test Runbook
description: Test with unknown connector
connectors:
  - name: test_connector
    type: unknown_connector_type
    properties: {}
analysers:
  - name: test_analyser
    type: mock_analyser
    properties: {}
execution:
  - name: "Test execution with unknown connector"
    description: "Testing error handling for unknown connector type"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.error_message is not None
        assert "Unknown connector type: unknown_connector_type" in result.error_message
        assert result.analysis_name == "Test execution with unknown connector"

    def test_execute_runbook_unsupported_input_schema(self) -> None:
        """Test execution fails gracefully with unsupported input schema."""
        executor = self._create_executor_with_mocks()

        # Create a valid runbook with unsupported schema
        runbook_content = """
name: Test Runbook
description: Test with unsupported schema
connectors:
  - name: test_connector
    type: mock_connector
    properties: {}
analysers:
  - name: test_analyser
    type: mock_analyser
    properties: {}
execution:
  - name: "Test execution with unsupported input schema"
    description: "Testing error handling for unsupported input schema"
    connector: test_connector
    analyser: test_analyser
    input_schema: unsupported_schema
    output_schema: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.error_message is not None
        assert "Input schema 'unsupported_schema' not found" in result.error_message
        assert result.analysis_name == "Test execution with unsupported input schema"

    def test_execute_runbook_unsupported_output_schema(self) -> None:
        """Test execution fails gracefully with unsupported output schema."""
        executor = self._create_executor_with_mocks()

        # Create a valid runbook with unsupported output schema
        runbook_content = """
name: Test Runbook
description: Test with unsupported output schema
connectors:
  - name: test_connector
    type: mock_connector
    properties: {}
analysers:
  - name: test_analyser
    type: mock_analyser
    properties: {}
execution:
  - name: "Test execution with unsupported output schema"
    description: "Testing error handling for unsupported output schema"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: unsupported_output_schema
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.error_message is not None
        assert (
            "Output schema 'unsupported_output_schema' not found"
            in result.error_message
        )
        assert result.analysis_name == "Test execution with unsupported output schema"

    def test_execute_runbook_connector_failure(self) -> None:
        """Test execution handles connector failures gracefully."""
        container = ServiceContainer()
        executor = Executor(container)

        # Create mock connector that will fail
        failing_connector = type(
            "FailingConnector",
            (MockConnector,),
            {
                "get_name": classmethod(lambda cls: "failing_connector"),
                "__init__": lambda self: MockConnector.__init__(self, should_fail=True),
            },
        )

        # Create factory for failing connector
        failing_connector_factory = type(
            "FailingConnectorFactory",
            (ComponentFactory,),
            {
                "create": lambda self, config: failing_connector(),
                "can_create": lambda self, config: True,
                "get_component_name": lambda self: "failing_connector",
                "get_input_schemas": lambda self: [],
                "get_output_schemas": lambda self: [StandardInputSchema()],
                "get_service_dependencies": lambda self: {},
            },
        )()

        executor.register_connector_factory(failing_connector_factory)
        executor.register_analyser_factory(MockAnalyserFactory())

        # Create a valid runbook
        runbook_content = """
name: Test Runbook
description: Test with failing connector
connectors:
  - name: test_connector
    type: failing_connector
    properties: {}
analysers:
  - name: test_analyser
    type: mock_analyser
    properties: {}
execution:
  - name: "Test execution with failing connector"
    description: "Testing error handling for connector that throws exceptions"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(runbook_content)
            runbook_path = Path(f.name)

        try:
            results = executor.execute_runbook(runbook_path)

            assert len(results) == 1
            result = results[0]
            assert result.success is False
            assert result.error_message is not None
            assert "Mock connector failure" in result.error_message
            assert result.analysis_name == "Test execution with failing connector"
        finally:
            runbook_path.unlink()

    def test_execute_runbook_analyser_failure(self) -> None:
        """Test execution handles analyser failures gracefully."""
        container = ServiceContainer()
        executor = Executor(container)

        # Create mock analyser that will fail
        failing_analyser = type(
            "FailingAnalyser",
            (MockAnalyser,),
            {
                "get_name": classmethod(lambda cls: "failing_analyser"),
                "__init__": lambda self: MockAnalyser.__init__(self, should_fail=True),
            },
        )

        # Create factory for failing analyser
        failing_analyser_factory = type(
            "FailingAnalyserFactory",
            (ComponentFactory,),
            {
                "create": lambda self, config: failing_analyser(),
                "can_create": lambda self, config: True,
                "get_component_name": lambda self: "failing_analyser",
                "get_input_schemas": lambda self: [StandardInputSchema()],
                "get_output_schemas": lambda self: [PersonalDataFindingSchema()],
                "get_service_dependencies": lambda self: {},
            },
        )()

        executor.register_connector_factory(MockConnectorFactory())
        executor.register_analyser_factory(failing_analyser_factory)

        # Create a valid runbook
        runbook_content = """
name: Test Runbook
description: Test with failing analyser
connectors:
  - name: test_connector
    type: mock_connector
    properties: {}
analysers:
  - name: test_analyser
    type: failing_analyser
    properties: {}
execution:
  - name: "Test execution with failing analyser"
    description: "Testing error handling for analyser that throws exceptions"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(runbook_content)
            runbook_path = Path(f.name)

        try:
            results = executor.execute_runbook(runbook_path)

            assert len(results) == 1
            result = results[0]
            assert result.success is False
            assert result.error_message is not None
            assert "Mock analyser failure" in result.error_message
            assert result.analysis_name == "Test execution with failing analyser"
        finally:
            runbook_path.unlink()

    def test_execute_runbook_successful_execution(self) -> None:
        """Test successful runbook execution."""
        executor = self._create_executor_with_mocks()

        # Create a valid runbook
        runbook_content = """
name: Test Runbook
description: Successful test execution
connectors:
  - name: test_connector
    type: mock_connector
    properties: {}
analysers:
  - name: test_analyser
    type: mock_analyser
    properties: {}
    metadata:
      purpose: "testing"
execution:
  - name: "Successful test execution"
    description: "Testing successful execution with valid components"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.error_message is None
        assert result.analysis_name == "Successful test execution"
        assert result.input_schema == "standard_input"
        assert result.output_schema == "personal_data_finding"
        assert result.data == {"findings": []}
        assert result.metadata.purpose == "testing"

    def test_execute_runbook_multiple_steps(self) -> None:
        """Test execution of runbook with multiple steps."""
        executor = self._create_executor_with_mocks()

        # Create a runbook with multiple execution steps
        runbook_content = """
name: Multi-step Test Runbook
description: Test with multiple execution steps
connectors:
  - name: connector1
    type: mock_connector
    properties: {}
  - name: connector2
    type: mock_connector
    properties: {}
analysers:
  - name: analyser1
    type: mock_analyser
    properties: {}
  - name: analyser2
    type: mock_analyser
    properties: {}
execution:
  - name: "First execution step"
    description: "Testing first step in multi-step execution"
    connector: connector1
    analyser: analyser1
    input_schema: standard_input
    output_schema: personal_data_finding
  - name: "Second execution step"
    description: "Testing second step in multi-step execution"
    connector: connector2
    analyser: analyser2
    input_schema: standard_input
    output_schema: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 2

        # Check first result
        result1 = results[0]
        assert result1.success is True
        assert result1.analysis_name == "First execution step"

        # Check second result
        result2 = results[1]
        assert result2.success is True
        assert result2.analysis_name == "Second execution step"

    def test_execute_runbook_mixed_success_failure(self) -> None:
        """Test execution continues even when some steps fail."""
        container = ServiceContainer()
        executor = Executor(container)

        # Register one working and one failing analyser
        executor.register_connector_factory(MockConnectorFactory())
        executor.register_analyser_factory(MockAnalyserFactory())

        failing_analyser = type(
            "FailingAnalyser",
            (MockAnalyser,),
            {
                "get_name": classmethod(lambda cls: "failing_analyser"),
                "__init__": lambda self: MockAnalyser.__init__(self, should_fail=True),
            },
        )

        # Create factory for failing analyser
        failing_analyser_factory = type(
            "FailingAnalyserFactory",
            (ComponentFactory,),
            {
                "create": lambda self, config: failing_analyser(),
                "can_create": lambda self, config: True,
                "get_component_name": lambda self: "failing_analyser",
                "get_input_schemas": lambda self: [StandardInputSchema()],
                "get_output_schemas": lambda self: [PersonalDataFindingSchema()],
                "get_service_dependencies": lambda self: {},
            },
        )()

        executor.register_analyser_factory(failing_analyser_factory)

        # Create a runbook with mixed success/failure
        runbook_content = """
name: Mixed Results Test Runbook
description: Test with some successful and some failing steps
connectors:
  - name: connector1
    type: mock_connector
    properties: {}
  - name: connector2
    type: mock_connector
    properties: {}
analysers:
  - name: working_analyser
    type: mock_analyser
    properties: {}
  - name: broken_analyser
    type: failing_analyser
    properties: {}
execution:
  - name: "Working execution step"
    description: "Testing successful step in mixed scenario"
    connector: connector1
    analyser: working_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
  - name: "Failing execution step"
    description: "Testing failing step in mixed scenario"
    connector: connector2
    analyser: broken_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(runbook_content)
            runbook_path = Path(f.name)

        try:
            results = executor.execute_runbook(runbook_path)

            assert len(results) == 2

            # First step should succeed
            result1 = results[0]
            assert result1.success is True
            assert result1.analysis_name == "Working execution step"

            # Second step should fail but still return a result
            result2 = results[1]
            assert result2.success is False
            assert result2.analysis_name == "Failing execution step"
            assert result2.error_message is not None
            assert "Mock analyser failure" in result2.error_message
        finally:
            runbook_path.unlink()

    def test_execute_runbook_empty_execution_steps(self) -> None:
        """Test execution of runbook with no execution steps fails validation."""
        executor = self._create_executor_with_mocks()

        # Create a runbook with no execution steps (should fail schema validation)
        runbook_content = """
name: Empty Test Runbook
description: Test with no execution steps
connectors:
  - name: test_connector
    type: mock_connector
    properties: {}
analysers:
  - name: test_analyser
    type: mock_analyser
    properties: {}
execution: []
"""

        # Should raise ExecutorError due to schema validation failure
        with pytest.raises(ExecutorError, match="List should have at least 1 item"):
            self._execute_runbook_yaml(executor, runbook_content)

    def test_execute_runbook_generic_exception_handling(self) -> None:
        """Test that generic exceptions are handled gracefully."""
        container = ServiceContainer()
        executor = Executor(container)

        # Create a factory that raises a generic exception during create()
        class BrokenConnectorFactory(ComponentFactory[MockConnector]):
            @override
            def create(self, config: ComponentConfig) -> MockConnector:
                # This will cause a generic exception during instantiation
                raise ValueError("Generic error during instantiation")

            @override
            def can_create(self, config: ComponentConfig) -> bool:
                return True

            @override
            def get_component_name(self) -> str:
                return "broken_connector"

            @override
            def get_input_schemas(self) -> list[Schema]:
                return []

            @override
            def get_output_schemas(self) -> list[Schema]:
                return [StandardInputSchema()]

            @override
            def get_service_dependencies(self) -> dict[str, type]:
                return {}

        executor.register_connector_factory(BrokenConnectorFactory())
        executor.register_analyser_factory(MockAnalyserFactory())

        # Create a runbook that uses the broken connector
        runbook_content = """
name: Broken Connector Test
description: Test with connector that raises generic exception
connectors:
  - name: broken_conn
    type: broken_connector
    properties: {}
analysers:
  - name: test_analyser
    type: mock_analyser
    properties: {}
execution:
  - name: "Test execution with broken connector"
    description: "Testing error handling for connector with generic exception"
    connector: broken_conn
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(runbook_content)
            runbook_path = Path(f.name)

        try:
            results = executor.execute_runbook(runbook_path)

            assert len(results) == 1
            result = results[0]
            assert result.success is False
            assert result.error_message is not None
            assert "Generic error during instantiation" in result.error_message
            assert result.analysis_name == "Test execution with broken connector"
        finally:
            runbook_path.unlink()

    def test_execute_runbook_with_metadata(self) -> None:
        """Test execution with metadata in analysers."""
        executor = self._create_executor_with_mocks()

        # Create a runbook with metadata
        runbook_content = """
name: Metadata Test
description: Test execution with metadata
connectors:
  - name: test_connector
    type: mock_connector
    properties: {}
analysers:
  - name: test_analyser
    type: mock_analyser
    properties: {}
    metadata:
      version: "1.0"
      author: "test"
      compliance_standard: "GDPR"
execution:
  - name: "Test execution with metadata"
    description: "Testing execution with analyser metadata"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.metadata.version == "1.0"
        assert result.metadata.author == "test"
        assert result.metadata.compliance_standard == "GDPR"
        # Analyser metadata is included in AnalysisResult

    def test_register_duplicate_connector_overrides(self) -> None:
        """Test that registering a factory with the same name overrides the previous one."""
        container = ServiceContainer()
        executor = Executor(container)

        # Register initial connector factory
        initial_factory = MockConnectorFactory()
        executor.register_connector_factory(initial_factory)
        assert executor.connector_factories["mock_connector"] == initial_factory

        # Create a different factory with the same component name
        alternate_factory = MockConnectorFactory()  # Same name, different instance

        # Register the alternate factory - should override
        executor.register_connector_factory(alternate_factory)
        assert executor.connector_factories["mock_connector"] == alternate_factory
        assert executor.connector_factories["mock_connector"] != initial_factory

    def test_register_duplicate_analyser_overrides(self) -> None:
        """Test that registering a factory with the same name overrides the previous one."""
        container = ServiceContainer()
        executor = Executor(container)

        # Register initial analyser factory
        initial_factory = MockAnalyserFactory()
        executor.register_analyser_factory(initial_factory)
        assert executor.analyser_factories["mock_analyser"] == initial_factory

        # Create a different factory with the same component name
        alternate_factory = MockAnalyserFactory()  # Same name, different instance

        # Register the alternate factory - should override
        executor.register_analyser_factory(alternate_factory)
        assert executor.analyser_factories["mock_analyser"] == alternate_factory
        assert executor.analyser_factories["mock_analyser"] != initial_factory


class TestExecutorCreateWithBuiltIns:
    """Tests for Executor.create_with_built_ins() class method ✔️."""

    @pytest.fixture(autouse=True)
    def _mock_llm_service(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Mock LLM service factory to avoid requiring API keys in tests."""
        # Create a mock LLM service
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True

        # Patch LLMServiceFactory.create() to return our mock
        def mock_create(self):
            return mock_llm

        monkeypatch.setattr(
            "waivern_llm.di.factory.LLMServiceFactory.create", mock_create
        )

    def test_creates_executor_with_all_built_in_connectors(self) -> None:
        """Test that create_with_built_ins registers all built-in connectors."""
        executor = Executor.create_with_built_ins()

        # Verify all built-in connector factories are registered
        registered_connectors = executor.list_available_connectors()

        # Check that all expected connector factories are present
        expected_connectors = {
            "filesystem_connector",
            "source_code_connector",
            "sqlite_connector",
            "mysql_connector",
        }
        registered_names = set(registered_connectors.keys())

        assert expected_connectors == registered_names
        assert len(registered_connectors) == 4

    def test_creates_executor_with_all_built_in_analysers(self) -> None:
        """Test that create_with_built_ins registers all built-in analysers."""
        executor = Executor.create_with_built_ins()

        # Verify all built-in analyser factories are registered
        registered_analysers = executor.list_available_analysers()

        # Check that all expected analyser factories are present
        expected_analysers = {
            "personal_data_analyser",
            "processing_purpose_analyser",
            "data_subject_analyser",
        }
        registered_names = set(registered_analysers.keys())

        assert expected_analysers == registered_names
        assert len(registered_analysers) == 3

    def test_creates_independent_executor_instances(self) -> None:
        """Test that multiple calls create independent executor instances."""
        executor1 = Executor.create_with_built_ins()
        executor2 = Executor.create_with_built_ins()

        # Verify they are different instances
        assert executor1 is not executor2

        # Verify they have the same factory types registered initially
        # (Each executor gets new factory instances, so we compare keys not objects)
        assert (
            executor1.list_available_connectors().keys()
            == executor2.list_available_connectors().keys()
        )
        assert (
            executor1.list_available_analysers().keys()
            == executor2.list_available_analysers().keys()
        )

        # Verify changes to one don't affect the other
        executor1.register_connector_factory(MockConnectorFactory())

        # executor1 should have the mock connector, executor2 should not
        assert "mock_connector" in executor1.list_available_connectors()
        assert "mock_connector" not in executor2.list_available_connectors()

    def test_returns_executor_instance(self) -> None:
        """Test that create_with_built_ins returns an Executor instance."""
        executor = Executor.create_with_built_ins()

        assert isinstance(executor, Executor)
        assert type(executor) is Executor
