"""CLI command implementations for WCT."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn

from wct.analysis import AnalysisResult
from wct.connectors import BUILTIN_CONNECTORS
from wct.logging import setup_logging, get_cli_logger
from wct.executor import Executor
from wct.plugins import BUILTIN_PLUGINS
from wct.runbook import Runbook, load_runbook, RunbookValidator

logger = get_cli_logger()
console = Console()


def create_executor() -> Executor:
    """Create and configure an executor with built-in components.

    Returns:
        Configured executor with all built-in connectors and plugins registered
    """
    executor = Executor()

    # Register built-in connectors
    for connector_class in BUILTIN_CONNECTORS:
        executor.register_connector(connector_class)
        logger.debug("Registered connector: %s", connector_class.get_name())

    # Register built-in plugins
    for plugin_class in BUILTIN_PLUGINS:
        executor.register_plugin(plugin_class)
        logger.debug("Registered plugin: %s", plugin_class.get_name())

    logger.info(
        "Executor initialized with %d connectors and %d plugins",
        len(BUILTIN_CONNECTORS),
        len(BUILTIN_PLUGINS),
    )

    return executor


class CLIError(Exception):
    """Base exception for CLI-related errors."""

    pass


class AnalysisRunner:
    """Handles running compliance analysis from CLI."""

    def __init__(self):
        self.executor = create_executor()

    def run_analysis(
        self, runbook_path: Path, output_dir: Path, verbose: bool = False
    ) -> list[AnalysisResult]:
        """Run analysis using a runbook.

        Args:
            runbook_path: Path to the runbook YAML file
            output_dir: Directory for output files (currently unused)
            verbose: Enable verbose output

        Returns:
            List of analysis results

        Raises:
            CLIError: If analysis fails
        """
        logger.debug("Loading runbook: %s", runbook_path)

        try:
            results = self.executor.execute_runbook(runbook_path)
            logger.info("Analysis completed with %d results", len(results))
            return results

        except Exception as e:
            logger.error("Analysis failed: %s", e)
            raise CLIError(f"Analysis failed: {e}") from e


class ComponentLister:
    """Handles listing available connectors and plugins."""

    def __init__(self):
        self.executor = create_executor()

    def list_connectors(self) -> dict[str, type]:
        """List all available connectors.

        Returns:
            Dictionary mapping connector names to classes
        """
        logger.debug("Getting registered connectors")
        connectors = self.executor.list_connectors()
        logger.info("Found %d registered connectors", len(connectors))
        return connectors

    def list_plugins(self) -> dict[str, type]:
        """List all available plugins.

        Returns:
            Dictionary mapping plugin names to classes
        """
        logger.debug("Getting registered plugins")
        plugins = self.executor.list_plugins()
        logger.info("Found %d registered plugins", len(plugins))
        return plugins


class OutputFormatter:
    """Handles formatting CLI output for different commands."""

    def format_analysis_results(
        self, results: list[AnalysisResult], verbose: bool = False
    ) -> None:
        """Format and print analysis results.

        Args:
            results: List of analysis results to format
            verbose: Show detailed information
        """
        # Create summary table
        table = Table(
            title="📊 Analysis Results Summary",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Plugin", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("Input Schema", style="blue")
        table.add_column("Output Schema", style="blue")

        if verbose:
            table.add_column("Metadata", style="yellow")

        for result in results:
            status_icon = "✅" if result.success else "❌"
            status_text = f"{status_icon} {'Success' if result.success else 'Failed'}"

            row = [
                result.plugin_name,
                status_text,
                result.input_schema,
                result.output_schema,
            ]

            if verbose:
                metadata_str = str(result.metadata) if result.metadata else "None"
                row.append(metadata_str)

            table.add_row(*row)

        console.print(table)

        # Show detailed error information for failed results
        failed_results = [r for r in results if not r.success]
        if failed_results:
            console.print("\n[bold red]❌ Failed Analysis Details:[/bold red]")
            for result in failed_results:
                error_panel = Panel(
                    f"[red]{result.error_message}[/red]",
                    title=f"Error in {result.plugin_name}",
                    border_style="red",
                )
                console.print(error_panel)
                logger.error(
                    "Plugin %s failed: %s", result.plugin_name, result.error_message
                )

        # Show successful results in verbose mode
        if verbose:
            successful_results = [r for r in results if r.success]
            if successful_results:
                console.print(
                    "\n[bold green]✅ Successful Analysis Details:[/bold green]"
                )
                for result in successful_results:
                    # Create a tree structure for the data
                    tree = Tree(f"[bold green]{result.plugin_name}[/bold green]")
                    tree.add(f"Input Schema: [blue]{result.input_schema}[/blue]")
                    tree.add(f"Output Schema: [blue]{result.output_schema}[/blue]")

                    if result.metadata:
                        metadata_branch = tree.add("[yellow]Metadata[/yellow]")
                        for key, value in result.metadata.items():
                            metadata_branch.add(f"{key}: {value}")

                    console.print(tree)
                    logger.debug(
                        "Plugin %s succeeded with data: %s",
                        result.plugin_name,
                        result.data,
                    )

    def format_component_list(
        self, components: dict[str, type], component_type: str
    ) -> None:
        """Format and print component list.

        Args:
            components: Dictionary of component names to classes
            component_type: Type name for display (e.g., "connectors", "plugins")
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
            table.add_column("Class", style="dim")

            for name, component_class in components.items():
                doc = component_class.__doc__ or "No description available"
                # Take first line of docstring
                description = doc.split("\n")[0].strip()
                class_name = f"{component_class.__module__}.{component_class.__name__}"

                table.add_row(name, description, class_name)
                logger.debug(
                    "%s %s: %s",
                    component_type.rstrip("s").title(),
                    name,
                    component_class,
                )

            console.print(table)
        else:
            warning_panel = Panel(
                f"[yellow]No {component_type} available. Register {component_type} to see them here.[/yellow]",
                title="⚠️  Warning",
                border_style="yellow",
            )
            console.print(warning_panel)
            logger.warning("No %s registered in executor", component_type)

    def format_runbook_validation(self, runbook: Runbook) -> None:
        """Format and print runbook validation results.

        Args:
            runbook: Validated runbook YAML file
        """
        # Create success panel
        success_content = f"""
[green]✅ Runbook validation successful![/green]

[bold]Name:[/bold] {runbook.name}
[bold]Description:[/bold] {runbook.description}
[bold]Connectors:[/bold] {len(runbook.connectors)}
[bold]Plugins:[/bold] {len(runbook.plugins)}
[bold]Execution Steps:[/bold] {len(runbook.execution)}
        """.strip()

        panel = Panel(
            success_content, title="📋 Runbook Validation Results", border_style="green"
        )
        console.print(panel)

        # Show execution order as a tree
        if runbook.execution:
            execution_tree = Tree("[bold blue]🔄 Execution Order[/bold blue]")
            for i, step in enumerate(runbook.execution, 1):
                step_branch = execution_tree.add(
                    f"[cyan]Step {i}: {step.plugin}[/cyan]"
                )
                step_branch.add(f"Connector: [yellow]{step.connector}[/yellow]")
                step_branch.add(f"Input Schema: [blue]{step.input_schema_name}[/blue]")
                if hasattr(step, "output_schema_name") and step.output_schema_name:
                    step_branch.add(
                        f"Output Schema: [blue]{step.output_schema_name}[/blue]"
                    )

            console.print(execution_tree)

        logger.debug(
            "Runbook details: connectors=%d, plugins=%d",
            len(runbook.connectors),
            len(runbook.plugins),
        )


def setup_cli_logging(log_level: str, verbose: bool = False) -> None:
    """Set up logging for CLI commands.

    Args:
        log_level: Logging level string
        verbose: Override with DEBUG level if True
    """
    effective_log_level = "DEBUG" if verbose else log_level
    setup_logging(level=effective_log_level)


def handle_cli_error(error: Exception, message: str) -> None:
    """Handle CLI errors with consistent formatting.

    Args:
        error: The exception that occurred
        message: User-friendly error message
    """
    logger.error("%s: %s", message, error)

    error_panel = Panel(
        f"[red]{error}[/red]", title=f"❌ {message}", border_style="red"
    )
    console.print(error_panel)
    raise typer.Exit(1) from error


def execute_runbook_command(
    runbook_path: Path, output_dir: Path, verbose: bool = False, log_level: str = "INFO"
) -> None:
    """CLI command implementation for running analyses.

    Args:
        runbook_path: Path to the runbook YAML file
        output_dir: Output directory (currently unused)
        verbose: Enable verbose output
        log_level: Logging level
    """
    setup_cli_logging(log_level, verbose)

    # Show startup banner
    startup_panel = Panel(
        f"[bold cyan]🚀 Starting WCT Analysis[/bold cyan]\n\n"
        f"[bold]Runbook:[/bold] {runbook_path}\n"
        f"[bold]Output Dir:[/bold] {output_dir}\n"
        f"[bold]Log Level:[/bold] {log_level}{'(verbose)' if verbose else ''}",
        title="🛡️  Waivern Compliance Tool",
        border_style="cyan",
    )
    console.print(startup_panel)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Initializing analysis...", total=None)

            runner = AnalysisRunner()

            progress.update(task, description="Running analysis...")
            results = runner.run_analysis(runbook_path, output_dir, verbose)

            progress.update(task, description="Formatting results...", completed=True)

        formatter = OutputFormatter()
        formatter.format_analysis_results(results, verbose)

        # Show completion banner
        completion_panel = Panel(
            f"[bold green]✅ Analysis Complete[/bold green]\n\n"
            f"[bold]Total Results:[/bold] {len(results)}\n"
            f"[bold]Successful:[/bold] {sum(1 for r in results if r.success)}\n"
            f"[bold]Failed:[/bold] {sum(1 for r in results if not r.success)}",
            title="🎉 Completion Summary",
            border_style="green",
        )
        console.print(completion_panel)

    except CLIError as e:
        handle_cli_error(e, "Analysis failed")


def list_connectors_command(log_level: str = "INFO") -> None:
    """CLI command implementation for listing connectors.

    Args:
        log_level: Logging level
    """
    setup_cli_logging(log_level)

    try:
        lister = ComponentLister()
        connectors = lister.list_connectors()

        formatter = OutputFormatter()
        formatter.format_component_list(connectors, "connectors")

    except Exception as e:
        handle_cli_error(e, "Failed to list connectors")


def list_plugins_command(log_level: str = "INFO") -> None:
    """CLI command implementation for listing plugins.

    Args:
        log_level: Logging level
    """
    setup_cli_logging(log_level)

    try:
        lister = ComponentLister()
        plugins = lister.list_plugins()

        formatter = OutputFormatter()
        formatter.format_component_list(plugins, "plugins")

    except Exception as e:
        handle_cli_error(e, "Failed to list plugins")


def validate_runbook_command(runbook_path: Path, log_level: str = "INFO") -> None:
    """CLI command implementation for validating runbooks.

    Args:
        runbook_path: Path to the runbook YAML file
        log_level: Logging level
    """
    setup_cli_logging(log_level)

    try:
        runbook = load_runbook(runbook_path)
        validator = RunbookValidator()
        validator.validate(runbook)

        formatter = OutputFormatter()
        formatter.format_runbook_validation(runbook)

    except CLIError as e:
        handle_cli_error(e, "Runbook validation failed")
