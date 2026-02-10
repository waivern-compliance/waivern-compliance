"""CLI command implementations for runbook validation and schema generation."""

from __future__ import annotations

import logging
from pathlib import Path

from rich.console import Console
from waivern_core.services import ComponentRegistry
from waivern_orchestration import Planner, RunbookSchemaGenerator

from wct.cli.errors import cli_error_handler
from wct.cli.formatting import OutputFormatter
from wct.cli.infrastructure import build_service_container
from wct.logging import setup_logging

logger = logging.getLogger(__name__)
console = Console()


def validate_runbook_command(runbook_path: Path, log_level: str = "INFO") -> None:
    """CLI command implementation for validating runbooks.

    Args:
        runbook_path: Path to the runbook YAML file
        log_level: Logging level

    """
    setup_logging(level=log_level)

    with cli_error_handler("validate-runbook", "Runbook validation failed"):
        container = build_service_container()
        registry = ComponentRegistry(container)

        plan = Planner(registry).plan(runbook_path)
        OutputFormatter().format_plan_validation(plan)


def generate_schema_command(output_path: Path, log_level: str = "INFO") -> None:
    """CLI command implementation for generating runbook JSON schema.

    Args:
        output_path: Path to save the generated schema
        log_level: Logging level

    """
    setup_logging(level=log_level)

    with cli_error_handler("generate-schema", "Schema generation failed"):
        RunbookSchemaGenerator.save_schema(output_path)
        console.print(f"[green]✅ Schema generated successfully: {output_path}[/green]")
        logger.info("Schema saved to %s", output_path)
