from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from wct.analyser import ComplianceAnalyser

app = typer.Typer(name="waivern-compliance-tool")


@app.command()
def analyze(
    runbook: Annotated[
        Path,
        typer.Argument(
            help="Path to the runbook YAML file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="The output directory (not implemented yet)",
            file_okay=False,
            dir_okay=True,
            writable=True,
            rich_help_panel="Output",
            show_default="./outputs/",
        ),
    ] = (Path.cwd() / "outputs"),
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output",
        ),
    ] = False,
):
    """Run compliance analysis using a runbook configuration."""
    analyser = ComplianceAnalyser()

    if verbose:
        print(f"Loading runbook: {runbook}")

    try:
        results = analyser.run_runbook_file(runbook)

        if verbose:
            print(f"Analysis completed with {len(results)} results")

        # Display results
        for result in results:
            status = "✓" if result.success else "✗"
            print(f"{status} {result.plugin_name}")

            if verbose or not result.success:
                print(f"  Input Schema: {result.input_schema}")
                print(f"  Output Schema: {result.output_schema}")

                if result.error_message and not result.success:
                    print(f"  Error: {result.error_message}")
                elif result.success and verbose:
                    print(f"  Data: {result.data}")

                if result.metadata:
                    print(f"  Metadata: {result.metadata}")
                print()

    except Exception as e:
        print(f"Analysis failed: {e}")
        raise typer.Exit(1)


@app.command(name="list-connectors")
def list_connectors():
    """List available connectors."""
    analyser = ComplianceAnalyser()
    connectors = analyser.list_connectors()

    if connectors:
        print("Available connectors:")
        for name, connector_class in connectors.items():
            doc = connector_class.__doc__ or "No description available"
            # Take first line of docstring
            description = doc.split("\n")[0].strip()
            print(f"  - {name}: {description}")
    else:
        print("No connectors available. Register connectors to see them here.")


@app.command(name="list-plugins")
def list_plugins():
    """List available plugins."""
    analyser = ComplianceAnalyser()
    plugins = analyser.list_plugins()

    if plugins:
        print("Available plugins:")
        for name, plugin_class in plugins.items():
            doc = plugin_class.__doc__ or "No description available"
            # Take first line of docstring
            description = doc.split("\n")[0].strip()
            print(f"  - {name}: {description}")
    else:
        print("No plugins available. Register plugins to see them here.")


@app.command(name="validate-runbook")
def validate_runbook(
    runbook: Annotated[
        Path,
        typer.Argument(
            help="Path to the runbook YAML file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
):
    """Validate a runbook configuration file."""
    analyser = ComplianceAnalyser()

    try:
        runbook_config = analyser.load_runbook(runbook)
        print(f"✓ Runbook '{runbook_config.name}' is valid")
        print(f"  Description: {runbook_config.description}")
        print(f"  Connectors: {len(runbook_config.connectors)}")
        print(f"  Plugins: {len(runbook_config.plugins)}")
        print(f"  Execution order: {', '.join(runbook_config.execution_order)}")
    except Exception as e:
        print(f"✗ Runbook validation failed: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
