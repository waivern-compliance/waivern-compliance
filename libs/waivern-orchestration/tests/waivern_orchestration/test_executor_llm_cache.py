"""Tests for LLM cache cleanup at the end of a run.

The executor clears the run's LLM cache once every artifact has completed
successfully. Runbooks can opt out via ``config.keep_llm_cache`` to retain
the responses for debugging.
"""

from dataclasses import dataclass
from typing import cast
from unittest.mock import MagicMock

import pytest
from waivern_artifact_store import ArtifactStore, LLMCache
from waivern_core.schemas import Schema

from waivern_orchestration.executor import DAGExecutor
from waivern_orchestration.models import (
    ArtifactDefinition,
    ExecutionResult,
    RunbookConfig,
    SourceConfig,
)

from .test_executor_state import create_failing_connector_factory
from .test_helpers import (
    create_mock_connector_factory,
    create_mock_registry,
    create_simple_plan,
    create_test_message,
)

SOURCE_SCHEMA = Schema("standard_input", "1.0.0")
CONNECTOR_TYPE = "src"
ARTIFACT_ID = "data"


def record_cache_clear(
    store: ArtifactStore, monkeypatch: pytest.MonkeyPatch
) -> list[str]:
    """Record run IDs passed to the store's cache_clear.

    The recorder delegates to the real implementation, so the store still
    behaves normally — only the fact of the call is captured.

    Args:
        store: The singleton store the executor will use.
        monkeypatch: Fixture used to install the recorder.

    Returns:
        A list that accumulates the run ID of each cache_clear call.

    """
    cleared: list[str] = []
    original = cast("LLMCache", store).cache_clear

    async def recording_cache_clear(run_id: str) -> None:
        cleared.append(run_id)
        await original(run_id)

    monkeypatch.setattr(store, "cache_clear", recording_cache_clear)
    return cleared


@dataclass(frozen=True)
class CacheClearRun:
    """Outcome of a run executed with cache_clear recording installed."""

    result: ExecutionResult
    """The executor's result for the run."""

    cleared: list[str]
    """Run IDs passed to cache_clear, in call order."""


async def run_with_recorded_cache_clear(
    connector_factory: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    runbook_config: RunbookConfig | None = None,
) -> CacheClearRun:
    """Execute a single-source-artifact runbook, recording cache_clear calls.

    Args:
        connector_factory: Factory registered for ``CONNECTOR_TYPE``. Its
            behaviour (succeeding or raising) decides the run's outcome.
        monkeypatch: Fixture used to install the cache_clear recorder.
        runbook_config: Optional runbook configuration; the model defaults
            apply when omitted.

    Returns:
        The execution result alongside the recorded cache_clear calls.

    """
    artifacts = {
        ARTIFACT_ID: ArtifactDefinition(
            source=SourceConfig(type=CONNECTOR_TYPE, properties={})
        )
    }
    plan = create_simple_plan(
        artifacts,
        {ARTIFACT_ID: (None, SOURCE_SCHEMA)},
        runbook_config=runbook_config,
    )
    registry = create_mock_registry(
        with_container=True,
        connector_factories={CONNECTOR_TYPE: connector_factory},
    )
    store = registry.container.get_service(ArtifactStore)
    cleared = record_cache_clear(store, monkeypatch)

    result = await DAGExecutor(registry).execute(plan)
    return CacheClearRun(result=result, cleared=cleared)


class TestLLMCacheCleanupOnCompletion:
    """Tests for LLM cache cleanup gated on runbook configuration."""

    async def test_successful_run_clears_llm_cache(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A successful run clears its LLM cache by default."""
        factory = create_mock_connector_factory(
            CONNECTOR_TYPE, [SOURCE_SCHEMA], create_test_message({"files": []})
        )

        run = await run_with_recorded_cache_clear(factory, monkeypatch)

        assert ARTIFACT_ID in run.result.completed
        assert run.cleared == [run.result.run_id]

    async def test_keep_llm_cache_retains_cache_after_successful_run(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """keep_llm_cache leaves the cache in place after a successful run."""
        factory = create_mock_connector_factory(
            CONNECTOR_TYPE, [SOURCE_SCHEMA], create_test_message({"files": []})
        )

        run = await run_with_recorded_cache_clear(
            factory, monkeypatch, runbook_config=RunbookConfig(keep_llm_cache=True)
        )

        assert ARTIFACT_ID in run.result.completed
        assert run.cleared == []

    async def test_failed_run_retains_llm_cache_when_flag_is_off(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failed run retains its cache even with the default configuration.

        The cache is what a resume replays, so cleanup is reserved for runs
        that completed. ``keep_llm_cache`` is irrelevant here.
        """
        factory = create_failing_connector_factory(
            CONNECTOR_TYPE, [SOURCE_SCHEMA], RuntimeError("extract failed")
        )

        run = await run_with_recorded_cache_clear(factory, monkeypatch)

        assert ARTIFACT_ID in run.result.failed
        assert run.cleared == []
