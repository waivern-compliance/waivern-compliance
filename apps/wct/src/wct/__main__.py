"""Main entry point for the Waivern Compliance Tool (WCT).

This module provides the command-line interface for the Waivern Compliance Tool,
including commands for:
- Running compliance runbooks
- Listing available connectors and analysers
- Validating runbooks
- Testing LLM connectivity
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from wct.cli import (
    execute_runbook_command,
    generate_schema_command,
    list_analysers_command,
    list_connectors_command,
    validate_runbook_command,
)

# Load environment variables from .env file in wct app directory if it exists
# This allows app-specific configuration separate from workspace root
_wct_app_dir = Path(__file__).parent.parent.parent
load_dotenv(_wct_app_dir / ".env")

app = typer.Typer(name="waivern-compliance-tool")


@app.command()
def run(
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
        Path | None,
        typer.Option(
            "--output-dir",
            help="The output directory for analysis results, defaults to './outputs/'",
            file_okay=False,
            dir_okay=True,
            writable=True,
            rich_help_panel="Output",
            show_default="./outputs/",
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Save analysis results to a JSON file (relative to --output-dir). Defaults to YYYYMMDDHHMMSS_analysis_results.json",
            file_okay=True,
            dir_okay=False,
            writable=True,
            rich_help_panel="Output",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable CLI verbose output (sets log level to DEBUG)",
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
) -> None:
    """Execute a runbook with configurable output options and logging.

    Example:
        wct run compliance-runbook.yaml --output-dir ./results --output report.json -v

    """
    # Set default output directory if not provided
    if output_dir is None:
        output_dir = Path.cwd() / "outputs"

    # Generate default output filename if not provided
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output = Path(f"{timestamp}_analysis_results.json")

    execute_runbook_command(runbook, output_dir, output, verbose, log_level)


@app.command(name="ls-connectors")
def list_available_connectors(
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            help="Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
            case_sensitive=False,
        ),
    ] = "INFO",
) -> None:
    """List available (built-in & registered) connectors."""
    list_connectors_command(log_level)


@app.command(name="ls-analysers")
def list_available_analysers(
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            help="Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
            case_sensitive=False,
        ),
    ] = "INFO",
) -> None:
    """List available (built-in & registered) analysers."""
    list_analysers_command(log_level)


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
) -> None:
    """Validate a runbook."""
    validate_runbook_command(runbook, log_level)


@app.command(name="generate-schema")
def generate_schema(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file path for generated schema",
            file_okay=True,
            dir_okay=False,
            writable=True,
        ),
    ] = None,
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            help="Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
            case_sensitive=False,
        ),
    ] = "INFO",
) -> None:
    """Generate JSON schema for WCT runbooks."""
    if output is None:
        output = Path("apps") / "wct" / "runbook.schema.json"

    generate_schema_command(output, log_level)


if __name__ == "__main__":
    app()
