"""Tests for Executor version matching functionality through public API.

These tests verify that the Executor correctly negotiates and selects schema versions
when connectors and analysers support multiple schema versions. Tests follow best
practices by testing through the public API (execute_runbook) rather than calling
private methods directly.

Mock classes are created per-scenario to respect the classmethod contract of base classes.
"""

import tempfile
from pathlib import Path
from typing import Any, Protocol, override

from waivern_core import Analyser, Connector
from waivern_core.component_factory import ComponentConfig, ComponentFactory
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_core.services.container import ServiceContainer

from wct.executor import Executor


class ComponentClassProtocol[T](Protocol):
    """Protocol for component classes used with MockComponentFactory.

    Defines the required classmethods that component classes must have
    for the factory to instantiate and describe them.
    """

    @classmethod
    def get_name(cls) -> str:
        """Get the component name."""
        ...

    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Get supported output schemas."""
        ...

    def __call__(self) -> T:
        """Instantiate the component."""
        ...


# Connector variants for different version scenarios


class BaseTestConnector(Connector):
    """Base connector for testing with shared extract() implementation."""

    @override
    def extract(self, output_schema: Schema) -> Message:
        """Shared extract implementation for all test connectors."""
        return Message(
            id="connector_message",
            content={"files": [{"path": "test.txt", "content": "test data"}]},
            schema=output_schema,
        )


class ConnectorV1_0_1_1(BaseTestConnector):
    """Connector supporting v1.0.0 and v1.1.0."""

    @classmethod
    @override
    def get_name(cls) -> str:
        return "connector_v1_0_1_1"

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("standard_input", "1.0.0"), Schema("standard_input", "1.1.0")]


class ConnectorV1_0_1_1_2_0(BaseTestConnector):
    """Connector supporting v1.0.0, v1.1.0, and v2.0.0."""

    @classmethod
    @override
    def get_name(cls) -> str:
        return "connector_v1_0_1_1_2_0"

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [
            Schema("standard_input", "1.0.0"),
            Schema("standard_input", "1.1.0"),
            Schema("standard_input", "2.0.0"),
        ]


class ConnectorV2_0(BaseTestConnector):
    """Connector supporting only v2.0.0."""

    @classmethod
    @override
    def get_name(cls) -> str:
        return "connector_v2_0"

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("standard_input", "2.0.0")]


# Analyser variants for different version scenarios


class BaseTestAnalyser(Analyser):
    """Base analyser for testing with shared process() implementation."""

    @override
    def process(
        self, input_schema: Schema, output_schema: Schema, message: Message
    ) -> Message:
        """Shared process implementation that records which versions were used."""
        return Message(
            id="analyser_result",
            content={
                "findings": [],
                "used_input_version": input_schema.version,
                "used_output_version": output_schema.version,
            },
            schema=output_schema,
        )


class AnalyserInputV1_0_1_1_OutputV1_0(BaseTestAnalyser):
    """Analyser supporting input v1.0.0, v1.1.0 and output v1.0.0."""

    @classmethod
    @override
    def get_name(cls) -> str:
        return "analyser_in_v1_0_1_1_out_v1_0"

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[Schema]:
        return [Schema("standard_input", "1.0.0"), Schema("standard_input", "1.1.0")]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("personal_data_finding", "1.0.0")]


class AnalyserInputV1_0_1_1_OutputV1_0_1_1(BaseTestAnalyser):
    """Analyser supporting input v1.0.0, v1.1.0 and output v1.0.0, v1.1.0."""

    @classmethod
    @override
    def get_name(cls) -> str:
        return "analyser_in_v1_0_1_1_out_v1_0_1_1"

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[Schema]:
        return [Schema("standard_input", "1.0.0"), Schema("standard_input", "1.1.0")]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [
            Schema("personal_data_finding", "1.0.0"),
            Schema("personal_data_finding", "1.1.0"),
        ]


class AnalyserInputV1_0_OutputV1_0(BaseTestAnalyser):
    """Analyser supporting only input v1.0.0 and output v1.0.0."""

    @classmethod
    @override
    def get_name(cls) -> str:
        return "analyser_in_v1_0_out_v1_0"

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[Schema]:
        return [Schema("standard_input", "1.0.0")]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("personal_data_finding", "1.0.0")]


# Factories for each mock type


class MockComponentFactory[T](ComponentFactory[T]):
    """Generic factory for mock components with no configuration needed."""

    def __init__(self, component_class: ComponentClassProtocol[T]):
        """Initialise factory with component class.

        Args:
            component_class: The component class to instantiate (must implement ComponentClassProtocol)

        """
        self._component_class = component_class

    @override
    def create(self, config: ComponentConfig) -> T:
        """Create component instance (ignores config for test components)."""
        return self._component_class()

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Test components can always be created."""
        return True

    @override
    def get_component_name(self) -> str:
        """Get component name from class."""
        return self._component_class.get_name()

    @override
    def get_input_schemas(self) -> list[Schema]:
        """Get input schemas from class if available (analysers only)."""
        # Check if this is an analyser class (has input schemas)
        # Use getattr with default to avoid type checker issues with optional attributes
        get_input = getattr(self._component_class, "get_supported_input_schemas", None)
        if get_input is not None:
            return get_input()
        return []

    @override
    def get_output_schemas(self) -> list[Schema]:
        """Get output schemas from class."""
        return self._component_class.get_supported_output_schemas()

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Test components have no service dependencies."""
        return {}


class TestExecutorVersionMatching:
    """Tests for executor schema version matching through public API."""

    def _execute_runbook_yaml(self, executor: Executor, yaml_content: str) -> list[Any]:
        """Execute a runbook from YAML string, handling temp file creation/cleanup."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            runbook_path = Path(f.name)

        try:
            return executor.execute_runbook(runbook_path)
        finally:
            runbook_path.unlink()

    def test_auto_selects_latest_compatible_version(self) -> None:
        """Test executor automatically selects latest compatible schema version.

        When no explicit version is specified in the runbook, the executor should
        choose the latest version that both connector and analyser support.
        """
        container = ServiceContainer()
        executor = Executor(container)
        executor.register_connector_factory(MockComponentFactory(ConnectorV1_0_1_1))
        executor.register_analyser_factory(
            MockComponentFactory(AnalyserInputV1_0_1_1_OutputV1_0)
        )

        runbook_content = """
name: Version Matching Test
description: Test auto-selection of latest version
connectors:
  - name: test_connector
    type: connector_v1_0_1_1
    properties: {}
analysers:
  - name: test_analyser
    type: analyser_in_v1_0_1_1_out_v1_0
    properties: {}
execution:
  - id: "auto_version_selection"
    name: "Test auto version selection"
    description: "Should select latest compatible version"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.data["used_input_version"] == "1.1.0"

    def test_respects_explicit_version_request(self) -> None:
        """Test executor uses explicitly requested version even when newer versions exist."""
        container = ServiceContainer()
        executor = Executor(container)
        executor.register_connector_factory(MockComponentFactory(ConnectorV1_0_1_1))
        executor.register_analyser_factory(
            MockComponentFactory(AnalyserInputV1_0_1_1_OutputV1_0_1_1)
        )

        runbook_content = """
name: Version Matching Test
description: Test explicit version pinning
connectors:
  - name: test_connector
    type: connector_v1_0_1_1
    properties: {}
analysers:
  - name: test_analyser
    type: analyser_in_v1_0_1_1_out_v1_0_1_1
    properties: {}
execution:
  - id: "explicit_version"
    name: "Test explicit version"
    description: "Should use explicitly requested version"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
    input_schema_version: "1.0.0"
    output_schema_version: "1.0.0"
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.data["used_input_version"] == "1.0.0"
        assert result.data["used_output_version"] == "1.0.0"

    def test_handles_partial_version_compatibility(self) -> None:
        """Test executor selects correct version when components have different version ranges."""
        container = ServiceContainer()
        executor = Executor(container)
        executor.register_connector_factory(MockComponentFactory(ConnectorV1_0_1_1_2_0))
        executor.register_analyser_factory(
            MockComponentFactory(AnalyserInputV1_0_1_1_OutputV1_0)
        )

        runbook_content = """
name: Version Matching Test
description: Test partial compatibility
connectors:
  - name: test_connector
    type: connector_v1_0_1_1_2_0
    properties: {}
analysers:
  - name: test_analyser
    type: analyser_in_v1_0_1_1_out_v1_0
    properties: {}
execution:
  - id: "partial_compatibility"
    name: "Test partial compatibility"
    description: "Should select v1.1.0 (latest compatible), not v2.0.0"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.data["used_input_version"] == "1.1.0"

    def test_raises_error_when_no_compatible_versions_found(self) -> None:
        """Test executor fails gracefully when no overlapping versions exist."""
        container = ServiceContainer()
        executor = Executor(container)
        executor.register_connector_factory(MockComponentFactory(ConnectorV2_0))
        executor.register_analyser_factory(
            MockComponentFactory(AnalyserInputV1_0_OutputV1_0)
        )

        runbook_content = """
name: Version Matching Test
description: Test version mismatch
connectors:
  - name: test_connector
    type: connector_v2_0
    properties: {}
analysers:
  - name: test_analyser
    type: analyser_in_v1_0_out_v1_0
    properties: {}
execution:
  - id: "version_mismatch"
    name: "Test version mismatch"
    description: "Should fail with version mismatch error"
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
        assert "No compatible versions" in result.error_message
        assert "2.0.0" in result.error_message
        assert "1.0.0" in result.error_message

    def test_raises_error_when_explicit_version_not_available(self) -> None:
        """Test executor fails when requested version not in compatible set."""
        container = ServiceContainer()
        executor = Executor(container)
        executor.register_connector_factory(MockComponentFactory(ConnectorV1_0_1_1))
        executor.register_analyser_factory(
            MockComponentFactory(AnalyserInputV1_0_1_1_OutputV1_0)
        )

        runbook_content = """
name: Version Matching Test
description: Test explicit version not available
connectors:
  - name: test_connector
    type: connector_v1_0_1_1
    properties: {}
analysers:
  - name: test_analyser
    type: analyser_in_v1_0_1_1_out_v1_0
    properties: {}
execution:
  - id: "explicit_version_unavailable"
    name: "Test explicit version not available"
    description: "Should fail when requesting unavailable version"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
    input_schema_version: "2.0.0"
"""

        results = self._execute_runbook_yaml(executor, runbook_content)

        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.error_message is not None
        assert "Requested version '2.0.0'" in result.error_message
        assert "Compatible versions" in result.error_message
