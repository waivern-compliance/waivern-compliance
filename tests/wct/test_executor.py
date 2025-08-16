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
    def get_output_schema(cls):
        return StandardInputSchema()

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
    def get_supported_input_schemas(cls) -> list[Schema]:
        return [StandardInputSchema()]

    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [PersonalDataFindingSchema()]

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
  - connector: test_connector
    analyser: test_analyser
    input_schema_name: standard_input
    output_schema_name: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.error_message is not None
        assert "Unknown analyser type: unknown_analyser_type" in result.error_message
        assert result.analyser_name == "test_analyser"

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
  - connector: test_connector
    analyser: test_analyser
    input_schema_name: standard_input
    output_schema_name: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.error_message is not None
        assert "Unknown connector type: unknown_connector_type" in result.error_message
        assert result.analyser_name == "test_analyser"

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
  - connector: test_connector
    analyser: test_analyser
    input_schema_name: unsupported_schema
    output_schema_name: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.error_message is not None
        assert "Schema 'unsupported_schema' not supported" in result.error_message
        assert result.analyser_name == "test_analyser"

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
  - connector: test_connector
    analyser: test_analyser
    input_schema_name: standard_input
    output_schema_name: unsupported_output_schema
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.error_message is not None
        assert (
            "Schema 'unsupported_output_schema' not supported" in result.error_message
        )
        assert result.analyser_name == "test_analyser"

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
  - connector: test_connector
    analyser: test_analyser
    input_schema_name: standard_input
    output_schema_name: personal_data_finding
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
            assert result.analyser_name == "test_analyser"
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
  - connector: test_connector
    analyser: test_analyser
    input_schema_name: standard_input
    output_schema_name: personal_data_finding
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
            assert result.analyser_name == "test_analyser"
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
  - connector: test_connector
    analyser: test_analyser
    input_schema_name: standard_input
    output_schema_name: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.error_message is None
        assert result.analyser_name == "test_analyser"
        assert result.input_schema == "standard_input"
        assert result.output_schema == "personal_data_finding"
        assert result.data == {"findings": []}
        assert result.metadata == {"purpose": "testing"}

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
  - connector: connector1
    analyser: analyser1
    input_schema_name: standard_input
    output_schema_name: personal_data_finding
  - connector: connector2
    analyser: analyser2
    input_schema_name: standard_input
    output_schema_name: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 2

        # Check first result
        result1 = results[0]
        assert result1.success is True
        assert result1.analyser_name == "analyser1"

        # Check second result
        result2 = results[1]
        assert result2.success is True
        assert result2.analyser_name == "analyser2"

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
  - connector: connector1
    analyser: working_analyser
    input_schema_name: standard_input
    output_schema_name: personal_data_finding
  - connector: connector2
    analyser: broken_analyser
    input_schema_name: standard_input
    output_schema_name: personal_data_finding
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
            assert result1.analyser_name == "working_analyser"

            # Second step should fail but still return a result
            result2 = results[1]
            assert result2.success is False
            assert result2.analyser_name == "broken_analyser"
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
  - connector: broken_conn
    analyser: test_analyser
    input_schema_name: standard_input
    output_schema_name: personal_data_finding
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
            assert result.analyser_name == "test_analyser"
        finally:
            runbook_path.unlink()

    def test_execute_runbook_with_context_and_metadata(self) -> None:
        """Test execution with context in execution steps and metadata in analysers."""
        executor = self._create_executor_with_mocks()

        # Create a runbook with context and metadata
        runbook_content = """
name: Context and Metadata Test
description: Test execution with context and metadata
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
  - connector: test_connector
    analyser: test_analyser
    input_schema_name: standard_input
    output_schema_name: personal_data_finding
    context:
      environment: "test"
      priority: "high"
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.metadata == {
            "version": "1.0",
            "author": "test",
            "compliance_standard": "GDPR",
        }
        # Note: ExecutionStep context is not directly included in AnalysisResult
        # but is available during execution

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
