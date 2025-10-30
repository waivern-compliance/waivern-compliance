"""CLI command implementations for WCT."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import override

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from waivern_core.component_factory import ComponentFactory

from wct.analysis import AnalysisResult, AnalysisResultsExporter
from wct.executor import Executor
from wct.logging import setup_logging
from wct.runbook import Runbook, RunbookLoader
from wct.schemas.runbook import RunbookSchemaGenerator

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
        table.add_column("Analysis", style="cyan", no_wrap=True)
        table.add_column("Description", style="white", max_width=40)
        table.add_column("Status", style="green")
        table.add_column("Input Schema", style="blue")
        table.add_column("Output Schema", style="blue")

        if verbose:
            table.add_column("Metadata", style="yellow")

        for result in results:
            status_icon = "✅" if result.success else "❌"
            status_text = f"{status_icon} {'Success' if result.success else 'Failed'}"

            row = [
                result.analysis_name,
                result.analysis_description,
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
                    title=f"Error in {result.analysis_name}",
                    border_style="red",
                )
                console.print(error_panel)
                logger.error(
                    "Analysis %s failed: %s", result.analysis_name, result.error_message
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
                    tree = Tree(f"[bold green]{result.analysis_name}[/bold green]")
                    if result.analysis_description:
                        tree.add(
                            f"Description: [white]{result.analysis_description}[/white]"
                        )
                    tree.add(f"Input Schema: [blue]{result.input_schema}[/blue]")
                    tree.add(f"Output Schema: [blue]{result.output_schema}[/blue]")

                    if result.metadata:
                        metadata_branch = tree.add("[yellow]Metadata[/yellow]")
                        for key, value in result.metadata.model_dump().items():
                            metadata_branch.add(f"{key}: {value}")

                    console.print(tree)
                    logger.debug("Analysis %s succeeded.", result.analysis_name)

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
[bold]Analysers:[/bold] {len(runbook.analysers)}
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
                    f"[cyan]Step {i}: {step.analyser}[/cyan]"
                )
                step_branch.add(f"Connector: [yellow]{step.connector}[/yellow]")
                step_branch.add(f"Input Schema: [blue]{step.input_schema}[/blue]")
                if hasattr(step, "output_schema") and step.output_schema:
                    step_branch.add(f"Output Schema: [blue]{step.output_schema}[/blue]")

            console.print(execution_tree)

        logger.debug(
            "Runbook details: connectors=%d, analysers=%d",
            len(runbook.connectors),
            len(runbook.analysers),
        )

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

    def show_analysis_completion(self) -> None:
        """Show analysis completion message."""
        console.print("\n[bold green]✅ Analysis completed![/bold green]")

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
        self, results: list[AnalysisResult], output_path: Path
    ) -> None:
        """Show completion summary banner.

        Args:
            results: Analysis results for summary statistics
            output_path: Final output file path

        """
        completion_panel = Panel(
            f"[bold green]✅ Analysis Complete[/bold green]\n\n"
            f"[bold]Total Results:[/bold] {len(results)}\n"
            f"[bold]Successful:[/bold] {sum(1 for r in results if r.success)}\n"
            f"[bold]Failed:[/bold] {sum(1 for r in results if not r.success)}\n"
            f"[bold]JSON Output:[/bold] {output_path}",
            title="🎉 Completion Summary",
            border_style="green",
        )
        console.print(completion_panel)


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
        output: Path to save results as JSON (now required, defaults to YYYYMMDDHHMMSS_analysis_results.json)
        verbose: Enable verbose output
        log_level: Logging level

    """
    effective_log_level = "DEBUG" if verbose else log_level
    setup_logging(level=effective_log_level)

    formatter = OutputFormatter()
    formatter.show_startup_banner(runbook_path, output_dir, log_level, verbose)

    try:
        # Run analysis
        executor = Executor.create_with_built_ins()

        try:
            results = executor.execute_runbook(runbook_path)
            logger.info("Analysis completed with %d results", len(results))
        except Exception as e:
            logger.error("Analysis failed: %s", e)
            raise CLIError(
                f"Failed to execute runbook analysis: {e}",
                command="run",
                original_error=e,
            ) from e

        formatter.show_analysis_completion()
        formatter.format_analysis_results(results, verbose)

        # Save results to JSON file
        if output.is_absolute():
            final_output_path = output
        else:
            final_output_path = output_dir / output

        try:
            AnalysisResultsExporter.save_to_json(
                results, final_output_path, runbook_path
            )
            formatter.show_file_save_success(final_output_path)
            logger.info("Analysis results saved to JSON file: %s", final_output_path)
        except Exception as e:
            error_msg = f"Failed to save analysis results to {final_output_path}: {e}"
            logger.error(error_msg)
            formatter.show_file_save_error(error_msg)
            raise CLIError(error_msg, command="run", original_error=e) from e

        formatter.show_completion_summary(results, final_output_path)

    except CLIError as e:
        logger.error("Analysis failed: %s", e)
        error_panel = Panel(
            f"[red]{e}[/red]", title="❌ Analysis failed", border_style="red"
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
        executor = Executor.create_with_built_ins()

        logger.debug("Getting available built-in connectors")
        connectors = executor.list_available_connectors()
        logger.info("Found %d available built-in connectors", len(connectors))

        formatter = OutputFormatter()
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
        executor = Executor.create_with_built_ins()

        logger.debug("Getting available built-in analysers")
        analysers = executor.list_available_analysers()
        logger.info("Found %d available built-in analysers", len(analysers))

        formatter = OutputFormatter()
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
        # Load and validate runbook - this performs comprehensive validation including:
        # - YAML syntax validation
        # - Pydantic schema validation (required fields, types, constraints)
        # - Business logic validation (unique names, cross-references)
        # If validation fails, exceptions are raised and caught below
        runbook = RunbookLoader.load(runbook_path)

        formatter = OutputFormatter()
        formatter.format_runbook_validation(runbook)

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


def generate_schema_command(output: Path, log_level: str = "INFO") -> None:
    """CLI command implementation for generating JSON schema.

    Args:
        output: Output file path for generated schema
        log_level: Logging level

    """
    setup_logging(level=log_level)

    try:
        RunbookSchemaGenerator.save_schema(output)
        console.print(f"✅ Generated JSON schema: {output}")
        logger.info("JSON schema generated successfully at %s", output)

    except Exception as e:
        logger.error("Schema generation failed: %s", e)
        cli_error = CLIError(
            f"Failed to generate schema: {e}",
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
