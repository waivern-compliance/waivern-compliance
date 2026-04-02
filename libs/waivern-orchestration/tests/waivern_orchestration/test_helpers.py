"""Shared test helpers for waivern-orchestration tests."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal
from unittest.mock import AsyncMock, MagicMock

import yaml
from pydantic import BaseModel
from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.configuration import ArtifactStoreConfiguration
from waivern_artifact_store.factory import ArtifactStoreFactory
from waivern_core import ExecutionContext, Message, MessageExtensions
from waivern_core.dispatch import DispatchResult, PrepareResult
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


def create_mock_processor_factory(
    name: str,
    input_schemas: list[Schema],
    output_schemas: list[Schema],
    process_result: Message | None = None,
    input_requirements: list[list[Schema]] | None = None,
) -> MagicMock:
    """Create a mock processor factory.

    Args:
        name: Component name.
        input_schemas: List of input schemas the processor accepts.
            Each schema becomes a separate single-item alternative.
        output_schemas: List of output schemas the processor produces.
        process_result: Optional message to return from process().
            If provided, creates a mock processor that returns this message.
        input_requirements: Optional explicit input requirement combinations.
            Each inner list is one valid combination of schema types.
            If provided, overrides the default conversion from input_schemas.

    Returns:
        Mock ComponentFactory for a processor.

    """
    factory = MagicMock()

    # Mock component_class with its class methods
    mock_class = MagicMock()
    mock_class.get_name.return_value = name
    mock_class.get_supported_output_schemas.return_value = output_schemas

    if input_requirements is not None:
        # Explicit combinations: each inner list becomes one combination
        mock_class.get_input_requirements.return_value = [
            [MagicMock(schema_name=s.name, version=s.version) for s in combo]
            for combo in input_requirements
        ]
    else:
        # Default: each schema becomes a single-item combination
        mock_class.get_input_requirements.return_value = [
            [MagicMock(schema_name=s.name, version=s.version)] for s in input_schemas
        ]
    factory.component_class = mock_class

    if process_result is not None:
        # Use spec to limit mock to only 'process' — prevents matching
        # DistributedProcessor's runtime_checkable isinstance check
        mock_processor = MagicMock(spec=["process"])
        mock_processor.process.return_value = process_result
        factory.create.return_value = mock_processor

    return factory


def create_container_with_store() -> ServiceContainer:
    """Create a ServiceContainer with singleton ArtifactStore.

    Uses singleton lifetime so the same store instance is shared between
    executor and tests, allowing verification of stored artifacts.

    Returns:
        ServiceContainer configured with AsyncInMemoryStore.

    """
    config = ArtifactStoreConfiguration.model_validate({"type": "memory"})
    factory = ArtifactStoreFactory(config)

    container = ServiceContainer()
    container.register(ServiceDescriptor(ArtifactStore, factory, "singleton"))

    return container


def create_mock_registry(
    connector_factories: dict[str, Any] | None = None,
    processor_factories: dict[str, Any] | None = None,
    with_container: bool = False,
) -> MagicMock:
    """Create a mock ComponentRegistry.

    Args:
        connector_factories: Dict of connector type to factory mock.
        processor_factories: Dict of processor type to factory mock.
        with_container: If True, includes a real ServiceContainer with ArtifactStore.
            Required for executor tests that actually store artifacts.

    Returns:
        Mock ComponentRegistry.

    """
    registry = MagicMock(spec=ComponentRegistry)
    registry.connector_factories = connector_factories or {}
    registry.processor_factories = processor_factories or {}

    if with_container:
        registry.container = create_container_with_store()

    return registry


def create_test_message(
    content: dict[str, Any],
    schema: Schema | None = None,
) -> Message:
    """Create a Message for testing (without execution context).

    Use this for messages that will have execution context added later
    (e.g., by the executor). For messages with pre-populated execution
    context, use create_message_with_execution().

    Args:
        content: Message content dict.
        schema: Optional schema. Defaults to standard_input/1.0.0.

    Returns:
        Message instance without execution context.

    """
    return Message(
        id="test_message",
        content=content,
        schema=schema or Schema("standard_input", "1.0.0"),
    )


def create_message_with_execution(  # noqa: PLR0913
    content: dict[str, Any] | None = None,
    schema: Schema | None = None,
    status: Literal["success", "error", "pending"] = "success",
    error: str | None = None,
    duration: float = 1.0,
    origin: str = "parent",
    alias: str | None = None,
) -> Message:
    """Create a Message with pre-populated execution context.

    Use this for tests that need messages with execution metadata already
    set (e.g., testing exporters, result processing). For messages that
    will have execution context added by the executor, use create_test_message().

    Args:
        content: Message content dict. Defaults to empty dict.
        schema: Optional schema. Defaults to test_schema/1.0.0.
        status: Execution status. Defaults to "success".
        error: Error message (typically used with status="error").
        duration: Execution duration in seconds. Defaults to 1.0.
        origin: Execution origin. Defaults to "parent".
        alias: Alias for child runbook artifacts. Defaults to None.

    Returns:
        Message instance with execution context.

    """
    return Message(
        id="test_message",
        content=content or {},
        schema=schema or Schema("test_schema", "1.0.0"),
        extensions=MessageExtensions(
            execution=ExecutionContext(
                status=status,
                error=error,
                duration_seconds=duration,
                origin=origin,
                alias=alias,
            )
        ),
    )


def create_simple_plan(
    artifacts: dict[str, ArtifactDefinition],
    artifact_schemas: dict[str, tuple[list[Schema] | None, Schema]] | None = None,
    runbook_config: RunbookConfig | None = None,
    aliases: dict[str, str] | None = None,
    runbook_name: str = "Test Runbook",
) -> ExecutionPlan:
    """Create a simple ExecutionPlan for testing.

    Args:
        artifacts: Dict of artifact ID to definition.
        artifact_schemas: Optional pre-resolved schemas. If not provided,
            defaults to (None, test_schema/1.0.0) for each artifact.
        runbook_config: Optional RunbookConfig for execution settings.
        aliases: Optional aliases mapping parent artifact names to namespaced
            child artifact IDs.
        runbook_name: Name for the runbook.

    Returns:
        ExecutionPlan ready for execution.

    """
    runbook_kwargs: dict[str, object] = {
        "name": runbook_name,
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

    # Compute reversed aliases for O(1) lookup
    resolved_aliases = aliases or {}
    reversed_aliases = {v: k for k, v in resolved_aliases.items()}

    return ExecutionPlan(
        runbook=runbook,
        dag=dag,
        artifact_schemas=artifact_schemas,
        aliases=resolved_aliases,
        reversed_aliases=reversed_aliases,
    )


def write_runbook(path: Path, runbook: dict[str, object]) -> None:
    """Write a runbook dictionary to a YAML file.

    Args:
        path: Path to write the runbook file.
        runbook: Dictionary representing the runbook structure.

    """
    path.write_text(yaml.dump(runbook))


# =============================================================================
# Distributed Processor Helpers
# =============================================================================


class StubState(BaseModel):
    """Minimal Pydantic state model for distributed processor tests."""

    value: str = "test_state"


class StubDistributedProcessor:
    """Stub implementing DistributedProcessor for tests.

    Uses concrete methods instead of MagicMock to correctly satisfy
    the ``@runtime_checkable`` isinstance check for DistributedProcessor.
    Call tracking is done via ``call_log`` list.

    Args:
        prepare_result: The PrepareResult to return from prepare().
        finalise_results: Sequence of results to return from successive
            finalise() calls. If a single item, it's returned every time.

    """

    def __init__(
        self,
        prepare_result: PrepareResult[StubState],
        finalise_results: Sequence[Message | PrepareResult[StubState]],
    ) -> None:
        self.prepare_result = prepare_result
        self.finalise_results = list(finalise_results)
        self._finalise_call_count = 0
        self.call_log: list[str] = []

    def prepare(
        self, inputs: list[Message], output_schema: Schema
    ) -> PrepareResult[StubState]:
        self.call_log.append("prepare")
        return self.prepare_result

    def deserialise_prepare_result(
        self, raw: dict[str, Any]
    ) -> PrepareResult[StubState]:
        self.call_log.append("deserialise_prepare_result")
        return PrepareResult[StubState].model_validate(raw)

    def finalise(
        self,
        state: StubState,
        results: Sequence[DispatchResult],
        output_schema: Schema,
    ) -> Message | PrepareResult[StubState]:
        self.call_log.append("finalise")
        idx = min(self._finalise_call_count, len(self.finalise_results) - 1)
        self._finalise_call_count += 1
        return self.finalise_results[idx]


def create_distributed_processor_factory(
    name: str,
    processor: StubDistributedProcessor,
) -> MagicMock:
    """Create a mock factory that returns a StubDistributedProcessor.

    The factory mock has a component_class with the expected class methods,
    and create() returns the real StubDistributedProcessor instance.

    Args:
        name: Component name (e.g., "distributed_analyser").
        processor: The StubDistributedProcessor instance to return.

    Returns:
        Mock ComponentFactory whose create() returns the given processor.

    """
    factory = MagicMock()
    mock_class = MagicMock()
    mock_class.get_name.return_value = name
    factory.component_class = mock_class
    factory.create.return_value = processor
    return factory


def create_mock_dispatcher(
    results: Sequence[DispatchResult],
    *,
    side_effect: BaseException | None = None,
) -> MagicMock:
    """Create a mock RequestDispatcher.

    Args:
        results: Results to return from dispatch(). Ignored if side_effect is set.
        side_effect: If set, dispatch() raises this exception.

    Returns:
        Mock dispatcher with an async dispatch() method.

    """
    dispatcher = MagicMock()
    if side_effect is not None:
        dispatcher.dispatch = AsyncMock(side_effect=side_effect)
    else:
        dispatcher.dispatch = AsyncMock(return_value=results)
    return dispatcher
