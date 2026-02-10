"""CLI tests for 'wct poll' command.

Tests the poll command's output formatting and error handling.
Core polling logic is tested in waivern-llm's test_batch_poller.py.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
import typer
from waivern_artifact_store.in_memory import AsyncInMemoryStore
from waivern_llm.batch_poller import PollResult
from waivern_llm.providers.protocol import BatchLLMProvider
from waivern_orchestration.run_metadata import RunMetadata, RunStatus

# =============================================================================
# Helpers
# =============================================================================


def _create_run_metadata(
    run_id: str = "run-123",
    runbook_path: str = "analysis.yaml",
    status: RunStatus = "interrupted",
) -> RunMetadata:
    """Create RunMetadata with sensible defaults for testing."""
    return RunMetadata(
        run_id=run_id,
        runbook_path=runbook_path,
        runbook_hash="sha256:abc123",
        started_at=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC),
        completed_at=datetime(2025, 6, 15, 10, 5, 0, tzinfo=UTC),
        status=status,
    )


class _SyncOnlyProvider:
    """Provider that only supports sync operations, not batch.

    Satisfies LLMProvider but NOT BatchLLMProvider — used to test
    the 'provider not batch-capable' error path.
    """

    @property
    def model_name(self) -> str:
        return "test-model"

    @property
    def context_window(self) -> int:
        return 100_000

    async def invoke_structured(self, prompt: str, response_model: type) -> None:
        raise NotImplementedError


def _setup_happy_path_mocks(
    monkeypatch: pytest.MonkeyPatch,
    store: AsyncInMemoryStore,
    poll_result: PollResult,
) -> None:
    """Configure mocks for a successful poll scenario.

    Sets up: store factory, logging, LLM config, batch-capable provider,
    and BatchResultPoller returning the given PollResult.
    """
    # Store factory
    mock_store_factory = Mock()
    mock_store_factory.return_value.create.return_value = store
    monkeypatch.setattr("wct.cli.ArtifactStoreFactory", mock_store_factory)

    # Logging (no-op)
    monkeypatch.setattr("wct.cli.setup_logging", lambda **kwargs: None)

    # LLM configuration
    mock_config = Mock()
    mock_config.provider = "anthropic"
    mock_config.model = "claude-sonnet-4-5-20250929"
    mock_config.get_default_model.return_value = "claude-sonnet-4-5-20250929"
    mock_llm_config_class = Mock()
    mock_llm_config_class.from_properties.return_value = mock_config
    monkeypatch.setattr("wct.cli.LLMServiceConfiguration", mock_llm_config_class)

    # Batch-capable provider (spec= required for isinstance() with Protocol)
    mock_factory_class = Mock()
    mock_factory_class.create_provider.return_value = Mock(spec=BatchLLMProvider)
    monkeypatch.setattr("wct.cli.LLMServiceFactory", mock_factory_class)

    # BatchResultPoller returning controlled result
    mock_poller = Mock()
    mock_poller.poll_run = AsyncMock(return_value=poll_result)
    monkeypatch.setattr("wct.cli.BatchResultPoller", Mock(return_value=mock_poller))


# =============================================================================
# Tests
# =============================================================================


class TestPollRunCommand:
    """Tests for poll_run_command()."""

    def test_all_batches_completed_shows_resume_suggestion(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All completed → exit 0 with resume suggestion including runbook path."""
        # Arrange
        store = AsyncInMemoryStore()
        metadata = _create_run_metadata(runbook_path="compliance.yaml")
        asyncio.run(metadata.save(store))

        _setup_happy_path_mocks(
            monkeypatch,
            store,
            PollResult(completed=2, failed=0, pending=0),
        )

        # Act
        from wct.cli import poll_run_command

        poll_run_command("run-123")

        # Assert — output contains resume suggestion with runbook path
        output = capsys.readouterr().out
        assert "--resume" in output
        assert "compliance.yaml" in output
        assert "run-123" in output

    def test_pending_batches_shows_progress(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Pending batches → exit 0 with progress counts."""
        # Arrange
        store = AsyncInMemoryStore()
        metadata = _create_run_metadata()
        asyncio.run(metadata.save(store))

        _setup_happy_path_mocks(
            monkeypatch,
            store,
            PollResult(completed=1, failed=0, pending=2),
        )

        # Act
        from wct.cli import poll_run_command

        poll_run_command("run-123")

        # Assert — output shows pending count
        output = capsys.readouterr().out
        assert "2" in output  # pending count
        assert "1" in output  # completed count

    def test_poll_errors_displayed_to_user(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PollResult errors → displayed visibly in output."""
        # Arrange
        store = AsyncInMemoryStore()
        metadata = _create_run_metadata()
        asyncio.run(metadata.save(store))

        _setup_happy_path_mocks(
            monkeypatch,
            store,
            PollResult(
                completed=0,
                failed=0,
                pending=0,
                errors=["Batch batch-1: provider/model mismatch"],
            ),
        )

        # Act
        from wct.cli import poll_run_command

        poll_run_command("run-123")

        # Assert — error text visible in output
        output = capsys.readouterr().out
        assert "mismatch" in output

    def test_store_not_configured_exits_with_error(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Store not configured → exit 1 with helpful error."""
        # Arrange — factory returns None (no store configured)
        mock_store_factory = Mock()
        mock_store_factory.return_value.create.return_value = None
        monkeypatch.setattr("wct.cli.ArtifactStoreFactory", mock_store_factory)
        monkeypatch.setattr("wct.cli.setup_logging", lambda **kwargs: None)

        # Act
        from wct.cli import poll_run_command

        with pytest.raises(typer.Exit) as exc_info:
            poll_run_command("run-123")

        # Assert — exit code 1 with store guidance
        assert exc_info.value.exit_code == 1
        output = capsys.readouterr().out
        assert "WAIVERN_STORE_TYPE" in output

    def test_provider_not_batch_capable_exits_with_error(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-batch provider → exit 1 with batch mode guidance."""
        # Arrange — store with metadata, but provider is sync-only
        store = AsyncInMemoryStore()
        metadata = _create_run_metadata()
        asyncio.run(metadata.save(store))

        mock_store_factory = Mock()
        mock_store_factory.return_value.create.return_value = store
        monkeypatch.setattr("wct.cli.ArtifactStoreFactory", mock_store_factory)
        monkeypatch.setattr("wct.cli.setup_logging", lambda **kwargs: None)

        mock_config = Mock()
        mock_config.provider = "anthropic"
        mock_config.model = "claude-sonnet-4-5-20250929"
        mock_llm_config_class = Mock()
        mock_llm_config_class.from_properties.return_value = mock_config
        monkeypatch.setattr("wct.cli.LLMServiceConfiguration", mock_llm_config_class)

        # Provider that does NOT implement BatchLLMProvider
        mock_factory_class = Mock()
        mock_factory_class.create_provider.return_value = _SyncOnlyProvider()
        monkeypatch.setattr("wct.cli.LLMServiceFactory", mock_factory_class)

        # Act
        from wct.cli import poll_run_command

        with pytest.raises(typer.Exit) as exc_info:
            poll_run_command("run-123")

        # Assert — exit code 1 with batch mode guidance
        assert exc_info.value.exit_code == 1
        output = capsys.readouterr().out
        assert "batch mode" in output.lower()
