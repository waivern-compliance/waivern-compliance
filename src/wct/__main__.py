from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from wct.logging import get_cli_logger, setup_logging
from wct.orchestrator import Orchestrator

app = typer.Typer(name="waivern-compliance-tool")


@app.command()
def run_analyses(
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
            help="Enable verbose output (sets log level to DEBUG)",
        ),
    ] = False,
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            help="Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
            case_sensitive=False,
        ),
    ] = "INFO",
):
    """Run compliance analysis using a runbook configuration."""
    # Set up logging
    effective_log_level = "DEBUG" if verbose else log_level
    setup_logging(level=effective_log_level)
    logger = get_cli_logger()

    logger.info("Starting WCT analysis")
    logger.debug("Creating orchestrator instance")
    analyser = Orchestrator()

    logger.debug("Loading runbook: %s", runbook)

    try:
        results = analyser.run_runbook_file(runbook)
        logger.info("Analysis completed with %d results", len(results))

        # Display results
        for result in results:
            status = "✓" if result.success else "✗"
            print(f"{status} {result.plugin_name}")

            if verbose or not result.success:
                print(f"  Input Schema: {result.input_schema}")
                print(f"  Output Schema: {result.output_schema}")

                if result.error_message and not result.success:
                    print(f"  Error: {result.error_message}")
                    logger.error(
                        "Plugin %s failed: %s", result.plugin_name, result.error_message
                    )
                elif result.success:
                    logger.debug(
                        "Plugin %s succeeded with data: %s",
                        result.plugin_name,
                        result.data,
                    )

                if result.metadata:
                    print(f"  Metadata: {result.metadata}")
                    logger.debug(
                        "Plugin %s metadata: %s", result.plugin_name, result.metadata
                    )
                print()

    except Exception as e:
        logger.error("Analysis failed: %s", e)
        print(f"Analysis failed: {e}")
        raise typer.Exit(1) from e


@app.command(name="list-connectors")
def list_connectors(
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            help="Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
            case_sensitive=False,
        ),
    ] = "INFO",
):
    """List available connectors."""
    setup_logging(level=log_level)
    logger = get_cli_logger()

    logger.debug("Creating orchestrator instance")
    analyser = Orchestrator()
    connectors = analyser.list_connectors()

    logger.info("Found %d registered connectors", len(connectors))

    if connectors:
        print("Available connectors:")
        for name, connector_class in connectors.items():
            doc = connector_class.__doc__ or "No description available"
            # Take first line of docstring
            description = doc.split("\n")[0].strip()
            print(f"  - {name}: {description}")
            logger.debug("Connector %s: %s", name, connector_class)
    else:
        print("No connectors available. Register connectors to see them here.")
        logger.warning("No connectors registered in orchestrator")


@app.command(name="list-plugins")
def list_plugins(
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            help="Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
            case_sensitive=False,
        ),
    ] = "INFO",
):
    """List available plugins."""
    setup_logging(level=log_level)
    logger = get_cli_logger()

    logger.debug("Creating orchestrator instance")
    analyser = Orchestrator()
    plugins = analyser.list_plugins()

    logger.info("Found %d registered plugins", len(plugins))

    if plugins:
        print("Available plugins:")
        for name, plugin_class in plugins.items():
            doc = plugin_class.__doc__ or "No description available"
            # Take first line of docstring
            description = doc.split("\n")[0].strip()
            print(f"  - {name}: {description}")
            logger.debug("Plugin %s: %s", name, plugin_class)
    else:
        print("No plugins available. Register plugins to see them here.")
        logger.warning("No plugins registered in orchestrator")


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
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            help="Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
            case_sensitive=False,
        ),
    ] = "INFO",
):
    """Validate a runbook configuration file."""
    setup_logging(level=log_level)
    logger = get_cli_logger()

    logger.debug("Creating orchestrator instance")
    analyser = Orchestrator()
    logger.debug("Validating runbook: %s", runbook)

    try:
        runbook_config = analyser.load_runbook(runbook)
        logger.info("Runbook validation successful: %s", runbook_config.name)

        print(f"✓ Runbook '{runbook_config.name}' is valid")
        print(f"  Description: {runbook_config.description}")
        print(f"  Connectors: {len(runbook_config.connectors)}")
        print(f"  Plugins: {len(runbook_config.plugins)}")
        print(f"  Execution order: {', '.join(runbook_config.execution_order)}")

        logger.debug(
            "Runbook details: connectors=%d, plugins=%d",
            len(runbook_config.connectors),
            len(runbook_config.plugins),
        )

    except Exception as e:
        logger.error("Runbook validation failed: %s", e)
        print(f"✗ Runbook validation failed: {e}")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
