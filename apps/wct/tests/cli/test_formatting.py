"""Tests for CLI output formatting — interrupted run handling."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from rich.console import Console
from waivern_core import Message, Schema
from waivern_core.message import ExecutionContext, MessageExtensions
from waivern_orchestration import ExecutionPlan, ExecutionResult
from waivern_orchestration.models import ArtifactDefinition, Runbook, SourceConfig

from wct.cli.formatting import OutputFormatter


def _make_result(
    *,
    completed: set[str] | None = None,
    failed: set[str] | None = None,
    skipped: set[str] | None = None,
    pending: set[str] | None = None,
) -> ExecutionResult:
    return ExecutionResult(
        run_id="abc-123",
        start_timestamp="2026-04-07T10:00:00+00:00",
        completed=completed or set(),
        failed=failed or set(),
        skipped=skipped or set(),
        pending=pending or set(),
        total_duration_seconds=42.0,
    )


def _make_plan(artifact_ids: list[str]) -> ExecutionPlan:
    """Create a minimal ExecutionPlan with the given artifact IDs."""
    artifacts = {
        aid: ArtifactDefinition(source=SourceConfig(type="test", properties={}))
        for aid in artifact_ids
    }
    runbook = Runbook(name="test", description="test", artifacts=artifacts)
    return ExecutionPlan(
        runbook=runbook,
        dag=Mock(),
        artifact_schemas={},
    )


def _make_store(messages: dict[str, Message] | None = None) -> AsyncMock:
    """Create a mock ArtifactStore that returns messages for given artifact IDs."""
    store = AsyncMock()
    msgs = messages or {}
    store.get_artifact = AsyncMock(side_effect=lambda _run_id, aid: msgs[aid])
    return store


def _make_message(*, duration: float = 1.0) -> Message:
    """Create a minimal Message with execution duration."""
    return Message(
        id="test-msg",
        content={"items": []},
        schema=Schema(name="test_schema", version="1.0.0"),
        extensions=MessageExtensions(
            execution=ExecutionContext(status="success", duration_seconds=duration)
        ),
    )


class TestFormatExecutionResultPending:
    """Verify pending artifacts appear in the results table."""

    @pytest.mark.asyncio
    async def test_pending_artifacts_shown_in_table(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = StringIO()
        monkeypatch.setattr(
            "wct.cli.formatting.console", Console(file=output, force_terminal=True)
        )

        result = _make_result(
            completed={"source_files"},
            pending={"document_context"},
        )
        plan = _make_plan(["source_files", "document_context"])
        store = _make_store({"source_files": _make_message()})

        formatter = OutputFormatter()
        await formatter.format_execution_result(result, plan, store)

        text = output.getvalue()
        assert "document_context" in text
        assert "Pending" in text
        assert "source_files" in text
        assert "Success" in text

    @pytest.mark.asyncio
    async def test_completed_run_has_no_pending_rows(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = StringIO()
        monkeypatch.setattr(
            "wct.cli.formatting.console", Console(file=output, force_terminal=True)
        )

        result = _make_result(completed={"source_files"})
        plan = _make_plan(["source_files"])
        store = _make_store({"source_files": _make_message()})

        formatter = OutputFormatter()
        await formatter.format_execution_result(result, plan, store)

        text = output.getvalue()
        assert "Pending" not in text
        assert "source_files" in text
        assert "Success" in text


class TestShowCompletionSummaryInterrupted:
    """Verify interrupted summary shows run ID and resume hints."""

    def test_interrupted_shows_run_id_and_resume_hint(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = StringIO()
        monkeypatch.setattr(
            "wct.cli.formatting.console", Console(file=output, force_terminal=True)
        )

        result = _make_result(
            completed={"source_files"},
            pending={"document_context"},
        )

        formatter = OutputFormatter()
        formatter.show_completion_summary(result, Path("output.json"))

        text = output.getvalue()
        assert "abc-123" in text
        assert "poll" in text.lower()
        assert "resume" in text.lower()
        assert "Pending" in text
