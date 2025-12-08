"""Shared test helpers for waivern-orchestration tests."""

from typing import Any
from unittest.mock import MagicMock

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.configuration import ArtifactStoreConfiguration
from waivern_artifact_store.factory import ArtifactStoreFactory
from waivern_core import Message
from waivern_core.schemas import Schema
from waivern_core.services import ComponentRegistry, ServiceContainer, ServiceDescriptor

from waivern_orchestration.dag import ExecutionDAG
from waivern_orchestration.models import ArtifactDefinition, Runbook, RunbookConfig
from waivern_orchestration.planner import ExecutionPlan


def create_mock_connector_factory(
    name: str,
    output_schemas: list[Schema],
    extract_result: Message | None = None,
) -> MagicMock:
    """Create a mock connector factory.

    Args:
        name: Component name.
        output_schemas: List of output schemas the connector supports.
        extract_result: Optional message to return from extract().
            If provided, creates a mock connector that returns this message.

    Returns:
        Mock ComponentFactory for a connector.

    """
    factory = MagicMock()

    # Mock component_class with its class methods
    mock_class = MagicMock()
    mock_class.get_name.return_value = name
    mock_class.get_supported_output_schemas.return_value = output_schemas
    factory.component_class = mock_class

    if extract_result is not None:
        mock_connector = MagicMock()
        mock_connector.extract.return_value = extract_result
        factory.create.return_value = mock_connector

    return factory


def create_mock_analyser_factory(
    name: str,
    input_schemas: list[Schema],
    output_schemas: list[Schema],
    process_result: Message | None = None,
) -> MagicMock:
    """Create a mock analyser factory.

    Args:
        name: Component name.
        input_schemas: List of input schemas the analyser accepts.
        output_schemas: List of output schemas the analyser produces.
        process_result: Optional message to return from process().
            If provided, creates a mock analyser that returns this message.

    Returns:
        Mock ComponentFactory for an analyser.

    """
    factory = MagicMock()

    # Mock component_class with its class methods
    mock_class = MagicMock()
    mock_class.get_name.return_value = name
    mock_class.get_supported_output_schemas.return_value = output_schemas
    # Convert input_schemas to InputRequirement-style format
    # For simplicity, each schema becomes a single-item combination
    mock_class.get_input_requirements.return_value = [
        [MagicMock(schema_name=s.name, version=s.version)] for s in input_schemas
    ]
    factory.component_class = mock_class

    if process_result is not None:
        mock_analyser = MagicMock()
        mock_analyser.process.return_value = process_result
        factory.create.return_value = mock_analyser

    return factory


def create_container_with_store() -> ServiceContainer:
    """Create a ServiceContainer with transient ArtifactStore.

    Returns:
        ServiceContainer configured with InMemoryArtifactStore.

    """
    config = ArtifactStoreConfiguration(backend="memory")
    factory = ArtifactStoreFactory(config)

    container = ServiceContainer()
    container.register(ServiceDescriptor(ArtifactStore, factory, "transient"))

    return container


def create_mock_registry(
    connector_factories: dict[str, Any] | None = None,
    analyser_factories: dict[str, Any] | None = None,
    with_container: bool = False,
) -> MagicMock:
    """Create a mock ComponentRegistry.

    Args:
        connector_factories: Dict of connector type to factory mock.
        analyser_factories: Dict of analyser type to factory mock.
        with_container: If True, includes a real ServiceContainer with ArtifactStore.
            Required for executor tests that actually store artifacts.

    Returns:
        Mock ComponentRegistry.

    """
    registry = MagicMock(spec=ComponentRegistry)
    registry.connector_factories = connector_factories or {}
    registry.analyser_factories = analyser_factories or {}

    if with_container:
        registry.container = create_container_with_store()

    return registry


def create_test_message(
    content: dict[str, Any],
    schema: Schema | None = None,
) -> Message:
    """Create a Message for testing.

    Args:
        content: Message content dict.
        schema: Optional schema. Defaults to standard_input/1.0.0.

    Returns:
        Message instance.

    """
    return Message(
        id="test_message",
        content=content,
        schema=schema or Schema("standard_input", "1.0.0"),
    )


def create_simple_plan(
    artifacts: dict[str, ArtifactDefinition],
    artifact_schemas: dict[str, tuple[Schema | None, Schema]] | None = None,
    runbook_config: RunbookConfig | None = None,
) -> ExecutionPlan:
    """Create a simple ExecutionPlan for testing.

    Args:
        artifacts: Dict of artifact ID to definition.
        artifact_schemas: Optional pre-resolved schemas. If not provided,
            defaults to (None, test_schema/1.0.0) for each artifact.
        runbook_config: Optional RunbookConfig for execution settings.

    Returns:
        ExecutionPlan ready for execution.

    """
    runbook_kwargs: dict[str, object] = {
        "name": "Test Runbook",
        "description": "Test description",
        "artifacts": artifacts,
    }
    if runbook_config is not None:
        runbook_kwargs["config"] = runbook_config
    runbook = Runbook(**runbook_kwargs)  # pyright: ignore[reportArgumentType]
    dag = ExecutionDAG(artifacts)

    if artifact_schemas is None:
        artifact_schemas = {}
        for aid in artifacts:
            artifact_schemas[aid] = (None, Schema("test_schema", "1.0.0"))

    return ExecutionPlan(
        runbook=runbook,
        dag=dag,
        artifact_schemas=artifact_schemas,
    )
