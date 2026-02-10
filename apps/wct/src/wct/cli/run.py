"""CLI command implementation for running analyses."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from waivern_artifact_store import ArtifactStore
from waivern_core.services import ComponentRegistry
from waivern_orchestration import (
    DAGExecutor,
    ExecutionPlan,
    ExecutionResult,
    OrchestrationError,
    Planner,
)

from wct.cli.errors import CLIError, cli_error_handler
from wct.cli.formatting import OutputFormatter
from wct.cli.infrastructure import setup_infrastructure
from wct.exporters.registry import ExporterRegistry
from wct.logging import setup_logging

logger = logging.getLogger(__name__)


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


def _execute_plan(
    plan: ExecutionPlan,
    registry: ComponentRegistry,
    runbook_path: Path,
    resume_run_id: str | None = None,
) -> ExecutionResult:
    """Execute runbook plan.

    Args:
        plan: Execution plan with artifact definitions.
        registry: Component registry for factory lookup.
        runbook_path: Path to the runbook file (required for resume validation).
        resume_run_id: If provided, resume from this existing run.

    Returns:
        Execution result with artifact outcomes.

    Raises:
        CLIError: If execution fails.

    """
    executor = DAGExecutor(registry)
    try:
        result = asyncio.run(
            executor.execute(
                plan,
                runbook_path=runbook_path,
                resume_run_id=resume_run_id,
            )
        )
        total = len(result.completed) + len(result.failed) + len(result.skipped)
        logger.info(
            "Execution completed: %d artifacts, %.2fs",
            total,
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


def _detect_exporter(plan: ExecutionPlan) -> str:
    """Select exporter based on runbook framework declaration.

    Args:
        plan: Execution plan with runbook definitions.

    Returns:
        Exporter name based on runbook framework.

    """
    framework = plan.runbook.framework
    if framework is None:
        return "json"

    return _framework_to_exporter(framework)


def _export_results(
    result: ExecutionResult,
    plan: ExecutionPlan,
    output_path: Path,
    store: ArtifactStore,
    exporter_override: str | None = None,
) -> None:
    """Export execution results to file.

    Args:
        result: Execution result with artifact outcomes.
        plan: Execution plan with runbook metadata.
        output_path: Path to save JSON output.
        store: Artifact store to load artifact data from.
        exporter_override: Manual exporter selection (overrides auto-detection).

    Raises:
        CLIError: If export fails.

    """
    # Use manual override if provided, otherwise select based on runbook framework
    if exporter_override:
        exporter_name = exporter_override
        logger.info("Using manually specified exporter: %s", exporter_name)
    else:
        exporter_name = _detect_exporter(plan)
        logger.info("Using exporter: %s", exporter_name)

    # Get exporter from registry
    try:
        exporter = ExporterRegistry.get(exporter_name)
    except ValueError as e:
        raise CLIError(
            str(e),
            command="run",
            original_error=e,
        ) from e

    # Export to file (exporter.export is async)
    try:
        export_data = asyncio.run(exporter.export(result, plan, store))
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
    resume_run_id: str | None = None,
) -> None:
    """CLI command implementation for running analyses.

    Args:
        runbook_path: Path to the runbook YAML file
        output_dir: Output directory for analysis results
        output: Path to save results as JSON
        verbose: Enable verbose output
        log_level: Logging level
        exporter_override: Manual exporter selection (overrides auto-detection)
        resume_run_id: If provided, resume from this existing run

    """
    effective_log_level = "DEBUG" if verbose else log_level
    setup_logging(level=effective_log_level)

    formatter = OutputFormatter()
    formatter.show_startup_banner(runbook_path, output_dir, log_level, verbose)

    with cli_error_handler("run", "Execution failed"):
        # Setup infrastructure
        registry = setup_infrastructure()

        # Plan and execute
        plan = _plan_runbook(runbook_path, registry)
        result = _execute_plan(plan, registry, runbook_path, resume_run_id)

        # Display results (load artifact data from store for duration/errors)
        store = registry.container.get_service(ArtifactStore)
        formatter.show_execution_completion()
        asyncio.run(formatter.format_execution_result(result, plan, store, verbose))

        # Export results
        final_output_path = output if output.is_absolute() else output_dir / output
        _export_results(result, plan, final_output_path, store, exporter_override)
        formatter.show_file_save_success(final_output_path)
        formatter.show_completion_summary(result, final_output_path)
