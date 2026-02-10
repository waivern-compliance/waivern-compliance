"""CLI command implementation for polling batch run status."""

from __future__ import annotations

import asyncio
import logging

from rich.console import Console
from rich.panel import Panel
from waivern_artifact_store import ArtifactStoreFactory
from waivern_llm import BatchResultPoller, LLMServiceFactory, PollResult
from waivern_llm.di.configuration import LLMServiceConfiguration
from waivern_llm.providers.protocol import BatchLLMProvider
from waivern_orchestration.run_metadata import RunMetadata

from wct.cli.errors import CLIError, cli_error_handler
from wct.logging import setup_logging

logger = logging.getLogger(__name__)
console = Console()


def poll_run_command(run_id: str, log_level: str = "INFO") -> None:
    """CLI command implementation for polling batch run status.

    Orchestrates the polling flow:
    1. Resolve artifact store and validate run exists
    2. Create LLM provider and validate batch capability
    3. Poll all pending batch jobs for the run
    4. Display results with actionable next steps

    Args:
        run_id: UUID of the run to poll.
        log_level: Logging level.

    """
    setup_logging(level=log_level)

    with cli_error_handler("poll", "Poll failed"):
        # 1. Resolve artifact store
        store = ArtifactStoreFactory().create()
        if store is None:
            raise CLIError(
                "Artifact store not configured. "
                "Check WAIVERN_STORE_TYPE environment variable.",
                command="poll",
            )

        # 2. Load run metadata (validates run exists)
        try:
            metadata = asyncio.run(RunMetadata.load(store, run_id))
        except Exception as e:
            raise CLIError(
                f"Run '{run_id}' not found: {e}",
                command="poll",
                original_error=e,
            ) from e

        # 3. Create LLM provider
        try:
            config = LLMServiceConfiguration.from_properties({})
        except Exception as e:
            raise CLIError(
                f"LLM not configured: {e}",
                command="poll",
                original_error=e,
            ) from e

        provider = LLMServiceFactory.create_provider(config)

        if not isinstance(provider, BatchLLMProvider):
            raise CLIError(
                f"Provider '{config.provider}' does not support batch mode. "
                "Batch mode requires a provider that implements "
                "the BatchLLMProvider protocol.",
                command="poll",
            )

        # 4. Create poller and poll
        model_name = config.model or config.get_default_model()
        poller = BatchResultPoller(
            store=store,
            provider=provider,
            provider_name=config.provider,
            model_name=model_name,
        )

        result = asyncio.run(poller.poll_run(run_id))

        # 5. Display results
        _format_poll_result(result, run_id, metadata)


def _format_poll_result(result: PollResult, run_id: str, metadata: RunMetadata) -> None:
    """Format and display poll results.

    Args:
        result: Poll result with batch counts and errors.
        run_id: The polled run identifier.
        metadata: Run metadata for runbook path display.

    """
    # Show errors if any
    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for error in result.errors:
            console.print(f"  [red]{error}[/red]")

    # Determine overall status and display summary
    match (result.pending, result.completed, result.failed):
        case (0, completed, 0) if completed > 0:
            # All completed successfully
            console.print(
                Panel(
                    f"[bold green]All batches completed[/bold green]\n\n"
                    f"[bold]Completed:[/bold] {result.completed}\n\n"
                    f"Resume with:\n"
                    f"  wct run {metadata.runbook_path} --resume {run_id}",
                    title="Poll Results",
                    border_style="green",
                )
            )
        case (pending, _, _) if pending > 0:
            # Still in progress
            console.print(
                Panel(
                    f"[bold yellow]Batches still in progress[/bold yellow]\n\n"
                    f"[bold]Completed:[/bold] {result.completed}\n"
                    f"[bold]Failed:[/bold] {result.failed}\n"
                    f"[bold]Pending:[/bold] {result.pending}\n\n"
                    f"Run 'wct poll {run_id}' again to check progress.",
                    title="Poll Results",
                    border_style="yellow",
                )
            )
        case (_, _, failed) if failed > 0:
            # Failures
            console.print(
                Panel(
                    f"[bold red]Batches failed[/bold red]\n\n"
                    f"[bold]Completed:[/bold] {result.completed}\n"
                    f"[bold]Failed:[/bold] {result.failed}",
                    title="Poll Results",
                    border_style="red",
                )
            )
        case _:
            # No batch jobs found (all zeroes)
            console.print(
                Panel(
                    f"[yellow]No pending batch jobs found for run {run_id}.[/yellow]\n\n"
                    f"The run may already be complete. Try:\n"
                    f"  wct run {metadata.runbook_path} --resume {run_id}",
                    title="Poll Results",
                    border_style="yellow",
                )
            )
