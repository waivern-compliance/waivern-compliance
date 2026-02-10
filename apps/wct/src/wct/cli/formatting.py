"""Output formatting for WCT CLI commands."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from waivern_artifact_store import ArtifactStore
from waivern_core import Message
from waivern_core.component_factory import ComponentFactory
from waivern_orchestration import ExecutionPlan, ExecutionResult

logger = logging.getLogger(__name__)
console = Console()


class OutputFormatter:
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

    def _print_error_details(
        self, failed_ids: set[str], messages: dict[str, Message]
    ) -> None:
        """Print error panels for failed artifacts.

        Args:
            failed_ids: Set of failed artifact IDs.
            messages: Loaded artifact messages keyed by artifact ID.

        """
        if not failed_ids:
            return
        console.print("\n[bold red]❌ Failed Artifact Details:[/bold red]")
        for artifact_id in failed_ids:
            error_text = messages[artifact_id].execution_error or "Unknown error"
            error_panel = Panel(
                f"[red]{error_text}[/red]",
                title=f"Error in {artifact_id}",
                border_style="red",
            )
            console.print(error_panel)
            logger.error("Artifact %s failed: %s", artifact_id, error_text)

    def _print_verbose_details(
        self,
        completed_ids: set[str],
        messages: dict[str, Message],
        plan: ExecutionPlan,
    ) -> None:
        """Print verbose details for successful artifacts.

        Args:
            completed_ids: Set of completed artifact IDs.
            messages: Loaded artifact messages keyed by artifact ID.
            plan: ExecutionPlan with artifact definitions.

        """
        if not completed_ids:
            return
        console.print("\n[bold green]✅ Successful Artifact Details:[/bold green]")
        for artifact_id in completed_ids:
            message = messages[artifact_id]
            definition = plan.runbook.artifacts.get(artifact_id)
            tree = Tree(f"[bold green]{artifact_id}[/bold green]")
            if definition and definition.name:
                tree.add(f"Name: [white]{definition.name}[/white]")
            if definition and definition.description:
                tree.add(f"Description: [white]{definition.description}[/white]")
            duration = message.execution_duration or 0.0
            tree.add(f"Duration: [blue]{duration:.2f}s[/blue]")
            console.print(tree)

    async def format_execution_result(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
        store: ArtifactStore,
        verbose: bool = False,
    ) -> None:
        """Format and print execution results.

        Loads artifact data from store to display duration and error details.

        Args:
            result: ExecutionResult from DAGExecutor.
            plan: ExecutionPlan with artifact definitions.
            store: Artifact store to load artifact data from.
            verbose: Show detailed information.

        """
        # Load artifact messages for completed and failed artifacts
        messages: dict[str, Message] = {}
        for artifact_id in result.completed | result.failed:
            messages[artifact_id] = await store.get_artifact(result.run_id, artifact_id)

        # Build summary table
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

        # Add rows for each category
        for artifact_id in result.completed:
            duration = messages[artifact_id].execution_duration or 0.0
            row = [artifact_id, self.STATUS_SUCCESS, f"{duration:.2f}s"]
            if verbose:
                row.append(self._get_schema_text(plan, artifact_id))
            table.add_row(*row)

        for artifact_id in result.failed:
            duration = messages[artifact_id].execution_duration or 0.0
            row = [artifact_id, self.STATUS_FAILED, f"{duration:.2f}s"]
            if verbose:
                row.append(self._get_schema_text(plan, artifact_id))
            table.add_row(*row)

        for artifact_id in result.skipped:
            row = [artifact_id, self.STATUS_SKIPPED, "-"]
            if verbose:
                row.append("-")
            table.add_row(*row)

        console.print(table)

        # Print details
        self._print_error_details(result.failed, messages)
        if verbose:
            self._print_verbose_details(result.completed, messages, plan)

    def format_component_list[T](
        self, components: Mapping[str, ComponentFactory[T]], component_type: str
    ) -> None:
        """Format and print component list.

        Args:
            components: Dictionary of component names to factories
            component_type: Type name for display (e.g., "connectors", "processors")

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

            for name, factory in components.items():
                # Get component class docstring for description
                component_class = factory.component_class
                doc = component_class.__doc__ or "No description available"
                # Take first line of docstring
                description = doc.split("\n")[0].strip()
                class_name = f"{component_class.__module__}.{component_class.__name__}"

                table.add_row(name, description, class_name)
                logger.debug(
                    "%s %s: %s",
                    component_type.rstrip("s").title(),
                    name,
                    component_class.__name__,
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
                    if definition.process:
                        artifact_branch.add(
                            f"Process: [yellow]{definition.process.type}[/yellow]"
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
        succeeded = len(result.completed)
        failed = len(result.failed)
        skipped = len(result.skipped)
        total = succeeded + failed + skipped

        completion_panel = Panel(
            f"[bold green]✅ Execution Complete[/bold green]\n\n"
            f"[bold]Total Artifacts:[/bold] {total}\n"
            f"[bold]Succeeded:[/bold] {succeeded}\n"
            f"[bold]Failed:[/bold] {failed}\n"
            f"[bold]Skipped:[/bold] {skipped}\n"
            f"[bold]Duration:[/bold] {result.total_duration_seconds:.2f}s\n"
            f"[bold]JSON Output:[/bold] {output_path}",
            title="🎉 Completion Summary",
            border_style="green",
        )
        console.print(completion_panel)
