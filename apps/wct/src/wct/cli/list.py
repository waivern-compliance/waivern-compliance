"""CLI command implementations for listing available components."""

from __future__ import annotations

import asyncio
import logging

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from waivern_artifact_store import ArtifactStoreFactory
from waivern_core.services import ComponentRegistry
from waivern_orchestration.run_metadata import RunMetadata
from waivern_orchestration.state import ExecutionState
from waivern_rulesets.core.registry import RulesetRegistry

from wct.cli.errors import CLIError, cli_error_handler
from wct.cli.formatting import OutputFormatter
from wct.cli.infrastructure import build_service_container, initialise_exporters
from wct.exporters.registry import ExporterRegistry
from wct.logging import setup_logging

logger = logging.getLogger(__name__)
console = Console()


def _list_registry_components(component_type: str) -> None:
    """List components from the registry by type.

    Args:
        component_type: Either "connectors" or "processors".

    """
    container = build_service_container()
    registry = ComponentRegistry(container)

    match component_type:
        case "connectors":
            factories = dict(registry.connector_factories)
        case "processors":
            factories = dict(registry.processor_factories)
        case _:
            msg = f"Unknown component type: {component_type}"
            raise ValueError(msg)

    logger.info("Found %d available %s", len(factories), component_type)
    OutputFormatter().format_component_list(factories, component_type)


def list_connectors_command(log_level: str = "INFO") -> None:
    """CLI command implementation for listing connectors.

    Args:
        log_level: Logging level

    """
    setup_logging(level=log_level)
    with cli_error_handler("connectors", "Failed to list connectors"):
        _list_registry_components("connectors")


def list_processors_command(log_level: str = "INFO") -> None:
    """CLI command implementation for listing processors.

    Args:
        log_level: Logging level

    """
    setup_logging(level=log_level)
    with cli_error_handler("processors", "Failed to list processors"):
        _list_registry_components("processors")


def list_rulesets_command(log_level: str = "INFO") -> None:
    """CLI command implementation for listing rulesets.

    Args:
        log_level: Logging level

    """
    setup_logging(level=log_level)

    with cli_error_handler("rulesets", "Failed to list rulesets"):
        registry = RulesetRegistry()
        rulesets = registry.list_registered()

        logger.debug("Getting available rulesets from registry")
        logger.info("Found %d available rulesets", len(rulesets))

        if rulesets:
            table = Table(
                title="🔧 Available Rulesets",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Version", style="white")
            table.add_column("Rule Type", style="dim")

            for name, version, rule_type in rulesets:
                table.add_row(name, version, rule_type.__name__)
                logger.debug("Ruleset %s/%s: %s", name, version, rule_type.__name__)

            console.print(table)
        else:
            warning_panel = Panel(
                "[yellow]No rulesets available. "
                "Register rulesets to see them here.[/yellow]",
                title="⚠️  Warning",
                border_style="yellow",
            )
            console.print(warning_panel)
            logger.warning("No rulesets registered in registry")


def list_exporters_command(log_level: str = "INFO") -> None:
    """CLI command implementation for listing exporters.

    Args:
        log_level: Logging level

    """
    setup_logging(level=log_level)

    with cli_error_handler("exporters", "Failed to list exporters"):
        # Initialise exporters to ensure they're registered
        initialise_exporters()

        exporter_names = ExporterRegistry.list_exporters()
        logger.info("Found %d available exporters", len(exporter_names))

        if exporter_names:
            # Create a rich table for exporters
            table = Table(
                title="🔧 Available Exporters",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Frameworks", style="white")

            for name in exporter_names:
                exporter = ExporterRegistry.get(name)
                frameworks = exporter.supported_frameworks
                frameworks_str = (
                    ", ".join(frameworks) if frameworks else "Any (generic)"
                )
                table.add_row(name, frameworks_str)
                logger.debug("Exporter %s: %s", name, frameworks_str)

            console.print(table)
        else:
            warning_panel = Panel(
                "[yellow]No exporters available. "
                "Register exporters to see them here.[/yellow]",
                title="⚠️  Warning",
                border_style="yellow",
            )
            console.print(warning_panel)
            logger.warning("No exporters registered in registry")


def list_runs_command(
    log_level: str = "INFO", status_filter: str | None = None
) -> None:
    """CLI command implementation for listing runs.

    Args:
        log_level: Logging level
        status_filter: Optional status to filter by (running, completed, failed, interrupted)

    """
    setup_logging(level=log_level)

    with cli_error_handler("runs", "Failed to list runs"):
        # Get artifact store
        store = ArtifactStoreFactory().create()
        if store is None:
            raise CLIError(
                "Artifact store not configured. Check WAIVERN_STORE_TYPE environment variable.",
                command="runs",
            )

        # Get all run IDs
        run_ids = asyncio.run(store.list_runs())

        if not run_ids:
            info_panel = Panel(
                "[yellow]No runs recorded.[/yellow]\n\n"
                "Execute a runbook with 'wct run <runbook.yaml>' to create a run.",
                title="📋 Runs",
                border_style="yellow",
            )
            console.print(info_panel)
            return

        # Load metadata for each run and collect data
        runs_data: list[dict[str, str | int]] = []
        for run_id in run_ids:
            try:
                metadata = asyncio.run(RunMetadata.load(store, run_id))
                state = asyncio.run(ExecutionState.load(store, run_id))

                # Apply status filter
                if status_filter and metadata.status != status_filter:
                    continue

                runs_data.append(
                    {
                        "run_id": run_id[:8] + "...",  # Truncate UUID for display
                        "full_run_id": run_id,
                        "status": metadata.status,
                        "runbook": metadata.runbook_path,
                        "started_at": metadata.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "completed": len(state.completed),
                        "failed": len(state.failed),
                        "skipped": len(state.skipped),
                    }
                )
            except Exception:
                # Skip runs with corrupt/missing metadata
                logger.debug("Skipping run %s - metadata not found", run_id)
                continue

        # Sort by started_at descending (most recent first)
        runs_data.sort(key=lambda x: x["started_at"], reverse=True)

        if not runs_data:
            if status_filter:
                console.print(
                    f"[yellow]No runs with status '{status_filter}' found.[/yellow]"
                )
            else:
                console.print("[yellow]No runs found.[/yellow]")
            return

        # Build table
        table = Table(
            title="📋 Recorded Runs",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Run ID", style="cyan", no_wrap=True)
        table.add_column("Status", style="white")
        table.add_column("Runbook", style="dim")
        table.add_column("Started", style="blue")
        table.add_column("✓", style="green", justify="right")
        table.add_column("✗", style="red", justify="right")
        table.add_column("⊘", style="yellow", justify="right")

        status_styles = {
            "running": "[blue]running[/blue]",
            "completed": "[green]completed[/green]",
            "failed": "[red]failed[/red]",
            "interrupted": "[yellow]interrupted[/yellow]",
        }

        for run in runs_data:
            status_text = status_styles.get(str(run["status"]), str(run["status"]))
            table.add_row(
                str(run["run_id"]),
                status_text,
                str(run["runbook"]),
                str(run["started_at"]),
                str(run["completed"]),
                str(run["failed"]),
                str(run["skipped"]),
            )

        console.print(table)
        console.print(
            f"\n[dim]Showing {len(runs_data)} run(s). "
            "Use the full run ID with --resume to continue a run.[/dim]"
        )
