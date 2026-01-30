"""Shared fixtures for exporter tests."""

from typing import Any
from unittest.mock import Mock

import pytest
from waivern_artifact_store.in_memory import AsyncInMemoryStore
from waivern_core import ExecutionContext, Message, MessageExtensions, Schema
from waivern_orchestration import (
    ArtifactDefinition,
    ExecutionPlan,
    ExecutionResult,
    Runbook,
    SourceConfig,
)

# =============================================================================
# Message Helpers
# =============================================================================


def create_success_message(
    content: dict[str, Any] | None = None,
    duration: float = 1.0,
    schema: Schema | None = None,
) -> Message:
    """Create a successful Message with execution context for testing."""
    return Message(
        id="test_msg",
        content=content or {},
        schema=schema or Schema("test_schema", "1.0.0"),
        extensions=MessageExtensions(
            execution=ExecutionContext(
                status="success",
                duration_seconds=duration,
            )
        ),
    )


def create_error_message(
    error: str,
    duration: float = 1.0,
    schema: Schema | None = None,
) -> Message:
    """Create a failed Message with execution context for testing."""
    return Message(
        id="test_msg",
        content={},
        schema=schema or Schema("test_schema", "1.0.0"),
        extensions=MessageExtensions(
            execution=ExecutionContext(
                status="error",
                error=error,
                duration_seconds=duration,
            )
        ),
    )


# =============================================================================
# Runbook Fixtures
# =============================================================================


@pytest.fixture
def empty_runbook() -> Runbook:
    """Create an empty runbook for testing."""
    return Runbook(name="Test", description="Test", artifacts={})


@pytest.fixture
def minimal_runbook() -> Runbook:
    """Create a minimal valid runbook with one artifact."""
    return Runbook(
        name="Test Runbook",
        description="Test description",
        artifacts={
            "art1": ArtifactDefinition(source=SourceConfig(type="test", properties={}))
        },
    )


# =============================================================================
# Execution Plan Fixtures
# =============================================================================


@pytest.fixture
def empty_plan(empty_runbook: Runbook) -> ExecutionPlan:
    """Create an empty execution plan for testing."""
    return ExecutionPlan(runbook=empty_runbook, dag=Mock(), artifact_schemas={})


@pytest.fixture
def minimal_plan(minimal_runbook: Runbook) -> ExecutionPlan:
    """Create a minimal valid execution plan for testing."""
    return ExecutionPlan(
        runbook=minimal_runbook,
        dag=Mock(),
        artifact_schemas={},
    )


# =============================================================================
# Execution Result Fixtures
# =============================================================================


@pytest.fixture
def empty_result() -> ExecutionResult:
    """Create an empty execution result for testing."""
    return ExecutionResult(
        run_id="123e4567-e89b-12d3-a456-426614174000",
        start_timestamp="2024-01-15T10:30:00+00:00",
        completed=set(),
        failed=set(),
        skipped=set(),
        total_duration_seconds=0.0,
    )


@pytest.fixture
def minimal_result() -> ExecutionResult:
    """Create a minimal valid execution result with one successful artifact."""
    return ExecutionResult(
        run_id="test-id",
        start_timestamp="2025-01-01T00:00:00+00:00",
        completed={"art1"},
        failed=set(),
        skipped=set(),
        total_duration_seconds=1.0,
    )


# =============================================================================
# Store Fixtures
# =============================================================================


@pytest.fixture
def empty_store() -> AsyncInMemoryStore:
    """Create an empty in-memory store for testing."""
    return AsyncInMemoryStore()


@pytest.fixture
def minimal_store(minimal_result: ExecutionResult) -> AsyncInMemoryStore:
    """Create a store with a minimal artifact for testing."""
    import asyncio

    store = AsyncInMemoryStore()
    message = create_success_message()
    asyncio.run(store.save(minimal_result.run_id, "art1", message))
    return store
