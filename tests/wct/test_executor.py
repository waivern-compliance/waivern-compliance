"""Tests for WCT Executor.

These tests focus on the public interface of the Executor class, testing
various scenarios and error conditions without testing internal methods.
The tests use real connectors and analysers to ensure proper integration.
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest

from wct.analysers import BUILTIN_ANALYSERS, Analyser, AnalyserError
from wct.connectors import BUILTIN_CONNECTORS, Connector, ConnectorError
from wct.executor import Executor, ExecutorError
from wct.message import Message
from wct.schemas import PersonalDataFindingSchema, Schema, StandardInputSchema


class MockConnector(Connector):
    """Mock connector for testing purposes."""

    def __init__(self, extract_result: Any = None, should_fail: bool = False) -> None:
        super().__init__()
        self.extract_result = extract_result
        self.should_fail = should_fail

    @classmethod
    def get_name(cls) -> str:
        return "mock_connector"

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> "MockConnector":
        return cls()

    @classmethod
    def get_supported_output_schemas(cls) -> tuple[Schema, ...]:
        return (StandardInputSchema(),)

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
    def get_name(cls) -> str:
        return "mock_analyser"

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> "MockAnalyser":
        return cls()

    @classmethod
    def get_supported_input_schemas(cls) -> tuple[Schema, ...]:
        return (StandardInputSchema(),)

    @classmethod
    def get_supported_output_schemas(cls) -> tuple[Schema, ...]:
        return (PersonalDataFindingSchema(),)

    def process(self, input_schema: Schema, output_schema: Schema, message: Any):
        if self.should_fail:
            raise AnalyserError("Mock analyser failure")

        return Message(
            id="mock_analyser_result",
            content=self.process_result or {"findings": []},
            schema=output_schema,
        )


class TestExecutor:
    """Tests for Executor class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.executor = Executor()

        # Register built-in connectors and analysers
        for connector_cls in BUILTIN_CONNECTORS:
            self.executor.register_available_connector(connector_cls)

        for analyser_cls in BUILTIN_ANALYSERS:
            self.executor.register_available_analyser(analyser_cls)

    def _create_executor_with_mocks(self) -> Executor:
        """Create executor with mock components registered."""
        executor = Executor()
        executor.register_available_connector(MockConnector)
        executor.register_available_analyser(MockAnalyser)
        return executor

    def _execute_runbook_yaml(self, executor: Executor, yaml_content: str) -> list:
        """Execute a runbook from YAML string, handling temp file creation/cleanup."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            runbook_path = Path(f.name)

        try:
            return executor.execute_runbook(runbook_path)
        finally:
            runbook_path.unlink()

    def test_executor_initialisation(self) -> None:
        """Test executor initialises correctly."""
        executor = Executor()

        assert executor.connectors == {}
        assert executor.analysers == {}

    def test_register_available_connector(self) -> None:
        """Test registering a connector."""
        executor = Executor()

        executor.register_available_connector(MockConnector)

        assert "mock_connector" in executor.connectors
        assert executor.connectors["mock_connector"] == MockConnector

    def test_register_available_analyser(self) -> None:
        """Test registering an analyser."""
        executor = Executor()

        executor.register_available_analyser(MockAnalyser)

        assert "mock_analyser" in executor.analysers
        assert executor.analysers["mock_analyser"] == MockAnalyser

    def test_list_available_connectors(self) -> None:
        """Test listing available connectors."""
        executor = Executor()
        executor.register_available_connector(MockConnector)

        connectors = executor.list_available_connectors()

        assert "mock_connector" in connectors
        assert connectors["mock_connector"] == MockConnector

        # Ensure returned dict is a copy
        connectors.clear()
        assert "mock_connector" in executor.connectors

    def test_list_available_analysers(self) -> None:
        """Test listing available analysers."""
        executor = Executor()
        executor.register_available_analyser(MockAnalyser)

        analysers = executor.list_available_analysers()

        assert "mock_analyser" in analysers
        assert analysers["mock_analyser"] == MockAnalyser

        # Ensure returned dict is a copy
        analysers.clear()
        assert "mock_analyser" in executor.analysers

    def test_execute_runbook_file_not_found(self) -> None:
        """Test executing a non-existent runbook file."""
        non_existent_path = Path("/path/that/does/not/exist.yaml")

        with pytest.raises(ExecutorError, match="Failed to load runbook"):
            self.executor.execute_runbook(non_existent_path)

    def test_execute_runbook_invalid_yaml(self) -> None:
        """Test executing a runbook with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content:")
            invalid_yaml_path = Path(f.name)

        try:
            with pytest.raises(ExecutorError, match="Failed to load runbook"):
                self.executor.execute_runbook(invalid_yaml_path)
        finally:
            invalid_yaml_path.unlink()

    def test_execute_runbook_unknown_analyser_type(self) -> None:
        """Test execution fails gracefully with unknown analyser type."""
        executor = Executor()
        executor.register_available_connector(MockConnector)

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
        executor = Executor()
        executor.register_available_analyser(MockAnalyser)

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
        executor = Executor()

        # Register mock connector that will fail
        failing_connector = type(
            "FailingConnector",
            (MockConnector,),
            {
                "get_name": classmethod(lambda cls: "failing_connector"),
                "__init__": lambda self: MockConnector.__init__(self, should_fail=True),
            },
        )

        executor.register_available_connector(failing_connector)
        executor.register_available_analyser(MockAnalyser)

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
        executor = Executor()

        # Register mock analyser that will fail
        failing_analyser = type(
            "FailingAnalyser",
            (MockAnalyser,),
            {
                "get_name": classmethod(lambda cls: "failing_analyser"),
                "__init__": lambda self: MockAnalyser.__init__(self, should_fail=True),
            },
        )

        executor.register_available_connector(MockConnector)
        executor.register_available_analyser(failing_analyser)

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
        executor = Executor()

        # Register one working and one failing analyser
        executor.register_available_connector(MockConnector)
        executor.register_available_analyser(MockAnalyser)

        failing_analyser = type(
            "FailingAnalyser",
            (MockAnalyser,),
            {
                "get_name": classmethod(lambda cls: "failing_analyser"),
                "__init__": lambda self: MockAnalyser.__init__(self, should_fail=True),
            },
        )
        executor.register_available_analyser(failing_analyser)

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
        executor = Executor()

        # Create a connector that raises a generic exception
        class BrokenConnector(MockConnector):
            @classmethod
            def get_name(cls) -> str:
                return "broken_connector"

            @classmethod
            def from_properties(cls, properties: dict[str, Any]) -> "BrokenConnector":
                # This will cause a generic exception during instantiation
                raise ValueError("Generic error during instantiation")

        executor.register_available_connector(BrokenConnector)
        executor.register_available_analyser(MockAnalyser)

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
        """Test that registering a connector with the same name overrides the previous one."""
        executor = Executor()

        # Register initial connector
        executor.register_available_connector(MockConnector)
        assert executor.connectors["mock_connector"] == MockConnector

        # Create a different connector with the same name
        class AlternateMockConnector(MockConnector):
            pass

        # Register the alternate connector - should override
        executor.register_available_connector(AlternateMockConnector)
        assert executor.connectors["mock_connector"] == AlternateMockConnector
        assert executor.connectors["mock_connector"] != MockConnector

    def test_register_duplicate_analyser_overrides(self) -> None:
        """Test that registering an analyser with the same name overrides the previous one."""
        executor = Executor()

        # Register initial analyser
        executor.register_available_analyser(MockAnalyser)
        assert executor.analysers["mock_analyser"] == MockAnalyser

        # Create a different analyser with the same name
        class AlternateMockAnalyser(MockAnalyser):
            pass

        # Register the alternate analyser - should override
        executor.register_available_analyser(AlternateMockAnalyser)
        assert executor.analysers["mock_analyser"] == AlternateMockAnalyser
        assert executor.analysers["mock_analyser"] != MockAnalyser


class TestExecutorCreateWithBuiltIns:
    """Tests for Executor.create_with_built_ins() class method ✔️."""

    def test_creates_executor_with_all_built_in_connectors(self) -> None:
        """Test that create_with_built_ins registers all built-in connectors."""
        executor = Executor.create_with_built_ins()

        # Verify all built-in connectors are registered
        registered_connectors = executor.list_available_connectors()

        # Check that all built-in connector names are present
        built_in_names = {
            connector_cls.get_name() for connector_cls in BUILTIN_CONNECTORS
        }
        registered_names = set(registered_connectors.keys())

        assert built_in_names == registered_names
        assert len(registered_connectors) == len(BUILTIN_CONNECTORS)

    def test_creates_executor_with_all_built_in_analysers(self) -> None:
        """Test that create_with_built_ins registers all built-in analysers."""
        executor = Executor.create_with_built_ins()

        # Verify all built-in analysers are registered
        registered_analysers = executor.list_available_analysers()

        # Check that all built-in analyser names are present
        built_in_names = {analyser_cls.get_name() for analyser_cls in BUILTIN_ANALYSERS}
        registered_names = set(registered_analysers.keys())

        assert built_in_names == registered_names
        assert len(registered_analysers) == len(BUILTIN_ANALYSERS)

    def test_creates_independent_executor_instances(self) -> None:
        """Test that multiple calls create independent executor instances."""
        executor1 = Executor.create_with_built_ins()
        executor2 = Executor.create_with_built_ins()

        # Verify they are different instances
        assert executor1 is not executor2

        # Verify they have the same registrations initially
        assert (
            executor1.list_available_connectors()
            == executor2.list_available_connectors()
        )
        assert (
            executor1.list_available_analysers() == executor2.list_available_analysers()
        )

        # Verify changes to one don't affect the other
        executor1.register_available_connector(MockConnector)

        # executor1 should have the mock connector, executor2 should not
        assert "mock_connector" in executor1.list_available_connectors()
        assert "mock_connector" not in executor2.list_available_connectors()

    def test_returns_executor_instance(self) -> None:
        """Test that create_with_built_ins returns an Executor instance."""
        executor = Executor.create_with_built_ins()

        assert isinstance(executor, Executor)
        assert type(executor) is Executor
