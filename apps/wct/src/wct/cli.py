"""CLI command implementations for WCT."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from waivern_artifact_store import ArtifactStore, ArtifactStoreFactory
from waivern_core.component_factory import ComponentFactory
from waivern_core.services import ComponentRegistry, ServiceContainer, ServiceDescriptor
from waivern_llm import BaseLLMService
from waivern_llm.di import LLMServiceFactory
from waivern_orchestration import (
    DAGExecutor,
    ExecutionPlan,
    ExecutionResult,
    OrchestrationError,
    Planner,
    RunbookSchemaGenerator,
)

from wct.logging import setup_logging

logger = logging.getLogger(__name__)
console = Console()

# Export format version
FORMAT_VERSION = "2.0.0"


class CLIError(Exception):
    """Exception for CLI-related errors with enhanced context.

    This exception serves as the CLI layer's unified error handling mechanism,
    providing meaningful context about what CLI operation failed and why.
    """

    def __init__(
        self,
        message: str,
        command: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialise CLI error with context.

        Args:
            message: Human-readable error message describing what went wrong
            command: Name of the CLI command that failed (e.g., "run", "validate")
            original_error: The underlying exception that caused this CLI error

        """
        super().__init__(message)
        self.command = command
        self.original_error = original_error

    @override
    def __str__(self) -> str:
        """Return formatted error message with CLI context."""
        base_message = super().__str__()
        if self.command:
            return f"CLI command '{self.command}' failed: {base_message}"
        return base_message


def _build_service_container() -> ServiceContainer:
    """Build a ServiceContainer with required services.

    Creates and configures a ServiceContainer with:
    - LLMService (singleton) - for LLM-based analysis
    - ArtifactStore (transient) - fresh store per execution

    Returns:
        Configured ServiceContainer.

    """
    container = ServiceContainer()

    # Register LLM service as singleton (shared across components)
    container.register(
        ServiceDescriptor(BaseLLMService, LLMServiceFactory(), "singleton")
    )

    # Register ArtifactStore as transient (fresh store per execution)
    container.register(
        ServiceDescriptor(ArtifactStore, ArtifactStoreFactory(), "transient")
    )

    logger.debug("ServiceContainer configured with LLM and ArtifactStore services")
    return container


class _OutputFormatter:
    """Handles formatting CLI output for different commands."""

    def _get_status_text(self, success: bool) -> str:
        """Get colour-coded status text.

        Args:
            success: Whether the artifact succeeded.

        Returns:
            Colour-coded status text.

        """
        return "[green]Success[/green]" if success else "[red]Failed[/red]"

    def _get_schema_text(self, plan: ExecutionPlan, artifact_id: str) -> str:
        """Get schema text for verbose output.

        Args:
            plan: ExecutionPlan with artifact definitions.
            artifact_id: The artifact ID.

        Returns:
            Schema text or "N/A".

        """
        _, output_schema = plan.artifact_schemas.get(artifact_id, (None, None))
        return (
            f"{output_schema.name}/{output_schema.version}" if output_schema else "N/A"
        )

    def format_execution_result(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
        verbose: bool = False,
    ) -> None:
        """Format and print execution results.

        Args:
            result: ExecutionResult from DAGExecutor.
            plan: ExecutionPlan with artifact definitions.
            verbose: Show detailed information.

        """
        # Create summary table
        table = Table(
            title="📊 Execution Results Summary",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Artifact", style="cyan", no_wrap=True)
        table.add_column("Status")
        table.add_column("Duration", style="blue")
        if verbose:
            table.add_column("Schema", style="yellow")

        for artifact_id, artifact_result in result.artifacts.items():
            row = [
                artifact_id,
                self._get_status_text(artifact_result.success),
                f"{artifact_result.duration_seconds:.2f}s",
            ]
            if verbose:
                row.append(self._get_schema_text(plan, artifact_id))
            table.add_row(*row)

        # Show skipped artifacts
        for artifact_id in result.skipped:
            row = [artifact_id, "[yellow]Skipped[/yellow]", "-"]
            if verbose:
                row.append("-")
            table.add_row(*row)

        console.print(table)

        # Show detailed error information for failed results
        failed_results = [
            (aid, ar) for aid, ar in result.artifacts.items() if not ar.success
        ]
        if failed_results:
            console.print("\n[bold red]❌ Failed Artifact Details:[/bold red]")
            for artifact_id, artifact_result in failed_results:
                error_panel = Panel(
                    f"[red]{artifact_result.error}[/red]",
                    title=f"Error in {artifact_id}",
                    border_style="red",
                )
                console.print(error_panel)
                logger.error(
                    "Artifact %s failed: %s", artifact_id, artifact_result.error
                )

        # Show successful results in verbose mode
        if verbose:
            successful_results = [
                (aid, ar) for aid, ar in result.artifacts.items() if ar.success
            ]
            if successful_results:
                console.print(
                    "\n[bold green]✅ Successful Artifact Details:[/bold green]"
                )
                for artifact_id, artifact_result in successful_results:
                    definition = plan.runbook.artifacts.get(artifact_id)
                    tree = Tree(f"[bold green]{artifact_id}[/bold green]")
                    if definition and definition.name:
                        tree.add(f"Name: [white]{definition.name}[/white]")
                    if definition and definition.description:
                        tree.add(
                            f"Description: [white]{definition.description}[/white]"
                        )
                    tree.add(
                        f"Duration: [blue]{artifact_result.duration_seconds:.2f}s[/blue]"
                    )
                    console.print(tree)

    def format_component_list[T](
        self, components: dict[str, ComponentFactory[T]], component_type: str
    ) -> None:
        """Format and print component list.

        Args:
            components: Dictionary of component names to factories
            component_type: Type name for display (e.g., "connectors", "analysers")

        """
        if components:
            # Create a rich table for components
            table = Table(
                title=f"🔧 Available {component_type.title()}",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Description", style="white")
            table.add_column("Factory", style="dim")

            for name, factory in components.items():
                # Get factory docstring for description
                doc = factory.__class__.__doc__ or "No description available"
                # Take first line of docstring
                description = doc.split("\n")[0].strip()
                factory_name = (
                    f"{factory.__class__.__module__}.{factory.__class__.__name__}"
                )

                table.add_row(name, description, factory_name)
                logger.debug(
                    "%s %s: %s",
                    component_type.rstrip("s").title(),
                    name,
                    factory.__class__.__name__,
                )

            console.print(table)
        else:
            warning_panel = Panel(
                f"[yellow]No {component_type} available. "
                f"Register {component_type} to see them here.[/yellow]",
                title="⚠️  Warning",
                border_style="yellow",
            )
            console.print(warning_panel)
            logger.warning("No %s registered in registry", component_type)

    def format_plan_validation(self, plan: ExecutionPlan) -> None:
        """Format and print plan validation results.

        Args:
            plan: Validated ExecutionPlan.

        """
        runbook = plan.runbook
        # Create success panel
        success_content = f"""
[green]✅ Runbook validation successful![/green]

[bold]Name:[/bold] {runbook.name}
[bold]Description:[/bold] {runbook.description}
[bold]Artifacts:[/bold] {len(runbook.artifacts)}
[bold]DAG Depth:[/bold] {plan.dag.get_depth()}
        """.strip()

        panel = Panel(
            success_content, title="📋 Runbook Validation Results", border_style="green"
        )
        console.print(panel)

        # Show artifact DAG as a tree
        if runbook.artifacts:
            artifact_tree = Tree("[bold blue]🔄 Artifact Dependencies[/bold blue]")

            # Get topological order
            sorter = plan.dag.create_sorter()
            level = 0
            while sorter.is_active():
                ready = list(sorter.get_ready())
                level_branch = artifact_tree.add(f"[dim]Level {level}[/dim]")
                for artifact_id in ready:
                    definition = runbook.artifacts[artifact_id]
                    artifact_branch = level_branch.add(f"[cyan]{artifact_id}[/cyan]")
                    if definition.source:
                        artifact_branch.add(
                            f"Source: [yellow]{definition.source.type}[/yellow]"
                        )
                    if definition.inputs:
                        inputs = (
                            definition.inputs
                            if isinstance(definition.inputs, list)
                            else [definition.inputs]
                        )
                        artifact_branch.add(f"Inputs: [blue]{', '.join(inputs)}[/blue]")
                    if definition.transform:
                        artifact_branch.add(
                            f"Transform: [yellow]{definition.transform.type}[/yellow]"
                        )
                    if definition.output:
                        artifact_branch.add("[green]📤 Output[/green]")
                    sorter.done(artifact_id)
                level += 1

            console.print(artifact_tree)

        logger.debug("Runbook has %d artifacts", len(runbook.artifacts))

    def show_startup_banner(
        self,
        runbook_path: Path,
        output_dir: Path,
        log_level: str,
        verbose: bool = False,
    ) -> None:
        """Show startup banner for analysis command.

        Args:
            runbook_path: Path to the runbook file
            output_dir: Output directory for results
            log_level: Current log level
            verbose: Whether verbose mode is enabled

        """
        startup_panel = Panel(
            f"[bold cyan]🚀 Starting WCT Analysis[/bold cyan]\n\n"
            f"[bold]Runbook:[/bold] {runbook_path}\n"
            f"[bold]Output Dir:[/bold] {output_dir}\n"
            f"[bold]Log Level:[/bold] {log_level}{'(verbose)' if verbose else ''}",
            title="🛡️  Waivern Compliance Tool",
            border_style="cyan",
        )
        console.print(startup_panel)

    def show_execution_completion(self) -> None:
        """Show execution completion message."""
        console.print("\n[bold green]✅ Execution completed![/bold green]")

    def show_file_save_success(self, file_path: Path) -> None:
        """Show successful file save message.

        Args:
            file_path: Path where file was saved

        """
        console.print(f"\n[green]✅ Results saved to JSON file: {file_path}[/green]")

    def show_file_save_error(self, error_msg: str) -> None:
        """Show file save error message.

        Args:
            error_msg: Error message to display

        """
        console.print(f"\n[red]❌ {error_msg}[/red]")

    def show_completion_summary(
        self, result: ExecutionResult, output_path: Path
    ) -> None:
        """Show completion summary banner.

        Args:
            result: ExecutionResult for summary statistics.
            output_path: Final output file path.

        """
        succeeded = sum(1 for ar in result.artifacts.values() if ar.success)
        failed = sum(1 for ar in result.artifacts.values() if not ar.success)
        skipped = len(result.skipped)

        completion_panel = Panel(
            f"[bold green]✅ Execution Complete[/bold green]\n\n"
            f"[bold]Total Artifacts:[/bold] {len(result.artifacts) + skipped}\n"
            f"[bold]Succeeded:[/bold] {succeeded}\n"
            f"[bold]Failed:[/bold] {failed}\n"
            f"[bold]Skipped:[/bold] {skipped}\n"
            f"[bold]Duration:[/bold] {result.total_duration_seconds:.2f}s\n"
            f"[bold]JSON Output:[/bold] {output_path}",
            title="🎉 Completion Summary",
            border_style="green",
        )
        console.print(completion_panel)


def _determine_execution_status(failed_count: int, skipped_count: int) -> str:
    """Determine execution status based on counts."""
    if failed_count > 0:
        return "failed"
    if skipped_count > 0:
        return "partial"
    return "completed"


def _build_output_entries(
    result: ExecutionResult, plan: ExecutionPlan
) -> list[dict[str, Any]]:
    """Build output entries for successful artifacts with output: true."""
    outputs: list[dict[str, Any]] = []
    runbook = plan.runbook

    for artifact_id, artifact_result in result.artifacts.items():
        if not artifact_result.success:
            continue

        definition = runbook.artifacts.get(artifact_id)
        if not definition or not definition.output:
            continue

        _, output_schema = plan.artifact_schemas.get(artifact_id, (None, None))

        output_entry: dict[str, Any] = {
            "artifact_id": artifact_id,
            "duration_seconds": artifact_result.duration_seconds,
        }

        # Add optional metadata fields
        if definition.name:
            output_entry["name"] = definition.name
        if definition.description:
            output_entry["description"] = definition.description
        if definition.contact:
            output_entry["contact"] = definition.contact
        if output_schema:
            output_entry["schema"] = {
                "name": output_schema.name,
                "version": output_schema.version,
            }
        if artifact_result.message:
            output_entry["content"] = artifact_result.message.content

        outputs.append(output_entry)

    return outputs


def _build_export_output(
    result: ExecutionResult,
    plan: ExecutionPlan,
    runbook_path: Path,
    run_id: str,
    timestamp: str,
) -> dict[str, Any]:
    """Build the export output dictionary.

    Args:
        result: ExecutionResult from DAGExecutor.
        plan: ExecutionPlan with artifact definitions.
        runbook_path: Path to the runbook file.
        run_id: Unique run identifier.
        timestamp: ISO8601 timestamp.

    Returns:
        Export dictionary ready for JSON serialization.

    """
    runbook = plan.runbook
    failed_count = sum(1 for ar in result.artifacts.values() if not ar.success)
    skipped_count = len(result.skipped)

    # Build errors list
    errors = [
        {"artifact_id": aid, "error": ar.error}
        for aid, ar in result.artifacts.items()
        if not ar.success
    ]

    export_data: dict[str, Any] = {
        "format_version": FORMAT_VERSION,
        "run": {
            "id": run_id,
            "timestamp": timestamp,
            "duration_seconds": result.total_duration_seconds,
            "status": _determine_execution_status(failed_count, skipped_count),
        },
        "runbook": {
            "path": str(runbook_path),
            "name": runbook.name,
            "description": runbook.description,
        },
        "summary": {
            "total": len(result.artifacts) + skipped_count,
            "succeeded": len(result.artifacts) - failed_count,
            "failed": failed_count,
            "skipped": skipped_count,
        },
        "outputs": _build_output_entries(result, plan),
        "errors": errors,
        "skipped": list(result.skipped),
    }

    if runbook.contact:
        export_data["runbook"]["contact"] = runbook.contact

    return export_data


def _save_results_to_json(
    result: ExecutionResult,
    plan: ExecutionPlan,
    runbook_path: Path,
    output_path: Path,
) -> None:
    """Save execution results to JSON file.

    Args:
        result: ExecutionResult from DAGExecutor.
        plan: ExecutionPlan with artifact definitions.
        runbook_path: Path to the runbook file.
        output_path: Path to save JSON output.

    """
    run_id = str(uuid.uuid4())
    timestamp = datetime.now(UTC).isoformat()

    export_data = _build_export_output(result, plan, runbook_path, run_id, timestamp)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, default=str)


def execute_runbook_command(
    runbook_path: Path,
    output_dir: Path,
    output: Path,
    verbose: bool = False,
    log_level: str = "INFO",
) -> None:
    """CLI command implementation for running analyses.

    Args:
        runbook_path: Path to the runbook YAML file
        output_dir: Output directory for analysis results
        output: Path to save results as JSON
        verbose: Enable verbose output
        log_level: Logging level

    """
    effective_log_level = "DEBUG" if verbose else log_level
    setup_logging(level=effective_log_level)

    formatter = _OutputFormatter()
    formatter.show_startup_banner(runbook_path, output_dir, log_level, verbose)

    try:
        # Build infrastructure
        container = _build_service_container()
        registry = ComponentRegistry(container)

        # Plan execution
        planner = Planner(registry)
        try:
            plan = planner.plan(runbook_path)
            logger.info(
                "Execution plan created with %d artifacts",
                len(plan.runbook.artifacts),
            )
        except OrchestrationError as e:
            logger.error("Planning failed: %s", e)
            raise CLIError(
                f"Failed to plan runbook execution: {e}",
                command="run",
                original_error=e,
            ) from e

        # Execute plan
        executor = DAGExecutor(registry)
        try:
            result = asyncio.run(executor.execute(plan))
            logger.info(
                "Execution completed: %d artifacts, %.2fs",
                len(result.artifacts),
                result.total_duration_seconds,
            )
        except Exception as e:
            logger.error("Execution failed: %s", e)
            raise CLIError(
                f"Failed to execute runbook: {e}",
                command="run",
                original_error=e,
            ) from e

        formatter.show_execution_completion()
        formatter.format_execution_result(result, plan, verbose)

        # Save results to JSON file
        if output.is_absolute():
            final_output_path = output
        else:
            final_output_path = output_dir / output

        try:
            _save_results_to_json(result, plan, runbook_path, final_output_path)
            formatter.show_file_save_success(final_output_path)
            logger.info("Results saved to JSON file: %s", final_output_path)
        except Exception as e:
            error_msg = f"Failed to save results to {final_output_path}: {e}"
            logger.error(error_msg)
            formatter.show_file_save_error(error_msg)
            raise CLIError(error_msg, command="run", original_error=e) from e

        formatter.show_completion_summary(result, final_output_path)

    except CLIError as e:
        logger.error("Execution failed: %s", e)
        error_panel = Panel(
            f"[red]{e}[/red]", title="❌ Execution failed", border_style="red"
        )
        console.print(error_panel)
        raise typer.Exit(1) from e


def list_connectors_command(log_level: str = "INFO") -> None:
    """CLI command implementation for listing connectors.

    Args:
        log_level: Logging level

    """
    setup_logging(level=log_level)

    try:
        container = _build_service_container()
        registry = ComponentRegistry(container)

        logger.debug("Getting available connectors from registry")
        connectors = dict(registry.connector_factories)
        logger.info("Found %d available connectors", len(connectors))

        formatter = _OutputFormatter()
        formatter.format_component_list(connectors, "connectors")

    except Exception as e:
        logger.error("Failed to list connectors: %s", e)
        cli_error = CLIError(
            f"Unable to retrieve available connectors: {e}",
            command="ls-connectors",
            original_error=e,
        )
        error_panel = Panel(
            f"[red]{cli_error}[/red]",
            title="❌ Failed to list connectors",
            border_style="red",
        )
        console.print(error_panel)
        raise typer.Exit(1) from cli_error


def list_analysers_command(log_level: str = "INFO") -> None:
    """CLI command implementation for listing analysers.

    Args:
        log_level: Logging level

    """
    setup_logging(level=log_level)

    try:
        container = _build_service_container()
        registry = ComponentRegistry(container)

        logger.debug("Getting available analysers from registry")
        analysers = dict(registry.analyser_factories)
        logger.info("Found %d available analysers", len(analysers))

        formatter = _OutputFormatter()
        formatter.format_component_list(analysers, "analysers")

    except Exception as e:
        logger.error("Failed to list analysers: %s", e)
        cli_error = CLIError(
            f"Unable to retrieve available analysers: {e}",
            command="ls-analysers",
            original_error=e,
        )
        error_panel = Panel(
            f"[red]{cli_error}[/red]",
            title="❌ Failed to list analysers",
            border_style="red",
        )
        console.print(error_panel)
        raise typer.Exit(1) from cli_error


def validate_runbook_command(runbook_path: Path, log_level: str = "INFO") -> None:
    """CLI command implementation for validating runbooks.

    Args:
        runbook_path: Path to the runbook YAML file
        log_level: Logging level

    """
    setup_logging(level=log_level)

    try:
        # Build infrastructure
        container = _build_service_container()
        registry = ComponentRegistry(container)

        # Use Planner for validation - validates:
        # - YAML syntax
        # - Pydantic model validation
        # - DAG cycle detection
        # - Component existence
        # - Schema compatibility
        planner = Planner(registry)
        plan = planner.plan(runbook_path)

        formatter = _OutputFormatter()
        formatter.format_plan_validation(plan)

    except OrchestrationError as e:
        logger.error("Runbook validation failed: %s", e)
        cli_error = CLIError(
            f"Runbook validation failed: {e}",
            command="validate-runbook",
            original_error=e,
        )
        error_panel = Panel(
            f"[red]{cli_error}[/red]",
            title="❌ Runbook validation failed",
            border_style="red",
        )
        console.print(error_panel)
        raise typer.Exit(1) from cli_error

    except Exception as e:
        logger.error("Runbook validation failed: %s", e)
        cli_error = CLIError(
            f"Runbook validation failed: {e}",
            command="validate-runbook",
            original_error=e,
        )
        error_panel = Panel(
            f"[red]{cli_error}[/red]",
            title="❌ Runbook validation failed",
            border_style="red",
        )
        console.print(error_panel)
        raise typer.Exit(1) from cli_error


def generate_schema_command(output_path: Path, log_level: str = "INFO") -> None:
    """CLI command implementation for generating runbook JSON schema.

    Args:
        output_path: Path to save the generated schema
        log_level: Logging level

    """
    setup_logging(level=log_level)

    try:
        RunbookSchemaGenerator.save_schema(output_path)
        console.print(f"[green]✅ Schema generated successfully: {output_path}[/green]")
        logger.info("Schema saved to %s", output_path)

    except Exception as e:
        logger.error("Schema generation failed: %s", e)
        cli_error = CLIError(
            f"Schema generation failed: {e}",
            command="generate-schema",
            original_error=e,
        )
        error_panel = Panel(
            f"[red]{cli_error}[/red]",
            title="❌ Schema generation failed",
            border_style="red",
        )
        console.print(error_panel)
        raise typer.Exit(1) from cli_error
