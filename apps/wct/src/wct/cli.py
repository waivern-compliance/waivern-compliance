"""CLI command implementations for WCT."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import override

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

from wct.exporters.json_exporter import JsonExporter
from wct.exporters.registry import ExporterRegistry
from wct.logging import setup_logging

logger = logging.getLogger(__name__)
console = Console()


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


def _initialise_exporters() -> None:
    """Initialise and register all exporters.

    Registers framework-agnostic exporters. Framework-specific exporters
    (e.g., GdprExporter) are registered when their configuration becomes available.
    """
    ExporterRegistry.register(JsonExporter())
    logger.debug("Registered JsonExporter")


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

    # Status text constants
    STATUS_SUCCESS = "[green]Success[/green]"
    STATUS_FAILED = "[red]Failed[/red]"
    STATUS_SKIPPED = "[yellow]Skipped[/yellow]"

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
            status = (
                self.STATUS_SUCCESS if artifact_result.success else self.STATUS_FAILED
            )
            row = [
                artifact_id,
                status,
                f"{artifact_result.duration_seconds:.2f}s",
            ]
            if verbose:
                row.append(self._get_schema_text(plan, artifact_id))
            table.add_row(*row)

        # Show skipped artifacts
        for artifact_id in result.skipped:
            row = [artifact_id, self.STATUS_SKIPPED, "-"]
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


def _setup_infrastructure() -> ComponentRegistry:
    """Set up infrastructure for runbook execution.

    Returns:
        Configured ComponentRegistry with services.

    """
    _initialise_exporters()
    container = _build_service_container()
    registry = ComponentRegistry(container)
    logger.debug("Infrastructure setup complete")
    return registry


def _plan_runbook(runbook_path: Path, registry: ComponentRegistry) -> ExecutionPlan:
    """Plan runbook execution.

    Args:
        runbook_path: Path to the runbook YAML file.
        registry: Component registry for factory lookup.

    Returns:
        Execution plan with artifact definitions.

    Raises:
        CLIError: If planning fails.

    """
    planner = Planner(registry)
    try:
        plan = planner.plan(runbook_path)
        logger.info(
            "Execution plan created with %d artifacts",
            len(plan.runbook.artifacts),
        )
        return plan
    except OrchestrationError as e:
        logger.error("Planning failed: %s", e)
        raise CLIError(
            f"Failed to plan runbook execution: {e}",
            command="run",
            original_error=e,
        ) from e


def _execute_plan(plan: ExecutionPlan, registry: ComponentRegistry) -> ExecutionResult:
    """Execute runbook plan.

    Args:
        plan: Execution plan with artifact definitions.
        registry: Component registry for factory lookup.

    Returns:
        Execution result with artifact outcomes.

    Raises:
        CLIError: If execution fails.

    """
    executor = DAGExecutor(registry)
    try:
        result = asyncio.run(executor.execute(plan))
        logger.info(
            "Execution completed: %d artifacts, %.2fs",
            len(result.artifacts),
            result.total_duration_seconds,
        )
        return result
    except Exception as e:
        logger.error("Execution failed: %s", e)
        raise CLIError(
            f"Failed to execute runbook: {e}",
            command="run",
            original_error=e,
        ) from e


def _export_results(
    result: ExecutionResult,
    plan: ExecutionPlan,
    registry: ComponentRegistry,
    output_path: Path,
    exporter_override: str | None = None,
) -> None:
    """Export execution results to file.

    Args:
        result: Execution result with artifact outcomes.
        plan: Execution plan with runbook metadata.
        registry: Component registry for factory lookup.
        output_path: Path to save JSON output.
        exporter_override: Manual exporter selection (overrides auto-detection).

    Raises:
        CLIError: If export fails.

    """
    # Use manual override if provided, otherwise auto-detect
    if exporter_override:
        exporter_name = exporter_override
        logger.info("Using manually specified exporter: %s", exporter_name)
    else:
        exporter_name = _detect_exporter(result, plan, registry)
        logger.info("Using auto-detected exporter: %s", exporter_name)

    # Get exporter from registry
    try:
        exporter = ExporterRegistry.get(exporter_name)
    except ValueError as e:
        raise CLIError(
            str(e),
            command="run",
            original_error=e,
        ) from e

    # Export to file
    try:
        export_data = exporter.export(result, plan)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)
        logger.info("Results saved to JSON file: %s", output_path)
    except Exception as e:
        error_msg = f"Failed to save results to {output_path}: {e}"
        logger.error(error_msg)
        raise CLIError(error_msg, command="run", original_error=e) from e


def execute_runbook_command(  # noqa: PLR0913 - Matches CLI entry point signature
    runbook_path: Path,
    output_dir: Path,
    output: Path,
    verbose: bool = False,
    log_level: str = "INFO",
    exporter_override: str | None = None,
) -> None:
    """CLI command implementation for running analyses.

    Args:
        runbook_path: Path to the runbook YAML file
        output_dir: Output directory for analysis results
        output: Path to save results as JSON
        verbose: Enable verbose output
        log_level: Logging level
        exporter_override: Manual exporter selection (overrides auto-detection)

    """
    effective_log_level = "DEBUG" if verbose else log_level
    setup_logging(level=effective_log_level)

    formatter = _OutputFormatter()
    formatter.show_startup_banner(runbook_path, output_dir, log_level, verbose)

    try:
        # Setup infrastructure
        registry = _setup_infrastructure()

        # Plan and execute
        plan = _plan_runbook(runbook_path, registry)
        result = _execute_plan(plan, registry)

        # Display results
        formatter.show_execution_completion()
        formatter.format_execution_result(result, plan, verbose)

        # Export results
        final_output_path = output if output.is_absolute() else output_dir / output
        _export_results(result, plan, registry, final_output_path, exporter_override)
        formatter.show_file_save_success(final_output_path)
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


def _framework_to_exporter(framework: str) -> str:
    """Map compliance framework to exporter name.

    Args:
        framework: Compliance framework identifier.

    Returns:
        Exporter name for the framework.

    """
    mapping = {
        "GDPR": "gdpr",
        "UK_GDPR": "gdpr",
        "CCPA": "ccpa",
    }
    return mapping.get(framework, "json")


def _detect_exporter(
    result: ExecutionResult,
    plan: ExecutionPlan,
    registry: ComponentRegistry,
) -> str:
    """Auto-detect exporter based on analyser compliance frameworks.

    Examines analyser factories used in successful artifacts and collects
    their declared compliance frameworks.

    Args:
        result: Execution result with artifact outcomes.
        plan: Execution plan with runbook definitions.
        registry: Component registry for factory lookup.

    Returns:
        Exporter name based on detected frameworks.

    """
    frameworks: set[str] = set()

    for artifact_id, artifact_result in result.artifacts.items():
        if not artifact_result.success:
            continue

        definition = plan.runbook.artifacts.get(artifact_id)
        if definition is None or definition.transform is None:
            continue

        # Get analyser factory and check its compliance frameworks
        analyser_type = definition.transform.type
        if analyser_type in registry.analyser_factories:
            factory = registry.analyser_factories[analyser_type]
            frameworks.update(factory.component_class.get_compliance_frameworks())

    # Map frameworks to exporter
    if len(frameworks) == 1:
        return _framework_to_exporter(frameworks.pop())
    elif len(frameworks) > 1:
        # Multiple frameworks detected - fall back to JSON
        logger.info(
            "Multiple compliance frameworks detected: %s. Using JSON exporter.",
            frameworks,
        )
        return "json"
    else:
        return "json"  # All generic analysers


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
