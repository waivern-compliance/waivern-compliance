"""CLI command implementations for WCT."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from wct.analysis import AnalysisResult
from wct.connectors import BUILTIN_CONNECTORS
from wct.logging import setup_logging
from wct.orchestrator import Orchestrator
from wct.plugins import BUILTIN_PLUGINS
from wct.runbook import Runbook, load_runbook

logger = logging.getLogger(__name__)


def create_orchestrator() -> Orchestrator:
    """Create and configure an orchestrator with built-in components.

    Returns:
        Configured orchestrator with all built-in connectors and plugins registered
    """
    orchestrator = Orchestrator()

    # Register built-in connectors
    for connector_class in BUILTIN_CONNECTORS:
        orchestrator.register_connector(connector_class)
        logger.debug("Registered connector: %s", connector_class.get_name())

    # Register built-in plugins
    for plugin_class in BUILTIN_PLUGINS:
        orchestrator.register_plugin(plugin_class)
        logger.debug("Registered plugin: %s", plugin_class.get_name())

    logger.info(
        "Orchestrator initialized with %d connectors and %d plugins",
        len(BUILTIN_CONNECTORS),
        len(BUILTIN_PLUGINS),
    )

    return orchestrator


class CLIError(Exception):
    """Base exception for CLI-related errors."""

    pass


class AnalysisRunner:
    """Handles running compliance analysis from CLI."""

    def __init__(self):
        self.orchestrator = create_orchestrator()

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
            results = self.orchestrator.execute_runbook(runbook_path)
            logger.info("Analysis completed with %d results", len(results))
            return results

        except Exception as e:
            logger.error("Analysis failed: %s", e)
            raise CLIError(f"Analysis failed: {e}") from e


class ComponentLister:
    """Handles listing available connectors and plugins."""

    def __init__(self):
        self.orchestrator = create_orchestrator()

    def list_connectors(self) -> dict[str, type]:
        """List all available connectors.

        Returns:
            Dictionary mapping connector names to classes
        """
        logger.debug("Getting registered connectors")
        connectors = self.orchestrator.list_connectors()
        logger.info("Found %d registered connectors", len(connectors))
        return connectors

    def list_plugins(self) -> dict[str, type]:
        """List all available plugins.

        Returns:
            Dictionary mapping plugin names to classes
        """
        logger.debug("Getting registered plugins")
        plugins = self.orchestrator.list_plugins()
        logger.info("Found %d registered plugins", len(plugins))
        return plugins


class RunbookValidator:
    """Handles runbook validation from CLI."""

    def validate_runbook(self, runbook_path: Path) -> Runbook:
        """Validate a runbook YAML file.

        Args:
            runbook_path: Path to the runbook YAML file

        Returns:
            Validated runbook YAML

        Raises:
            CLIError: If validation fails
        """
        logger.debug("Validating runbook: %s", runbook_path)

        try:
            runbook_config = load_runbook(runbook_path)
            logger.info("Runbook validation successful: %s", runbook_config.name)
            return runbook_config

        except Exception as e:
            logger.error("Runbook validation failed: %s", e)
            raise CLIError(f"Runbook validation failed: {e}") from e


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

    def format_component_list(
        self, components: dict[str, type], component_type: str
    ) -> None:
        """Format and print component list.

        Args:
            components: Dictionary of component names to classes
            component_type: Type name for display (e.g., "connectors", "plugins")
        """
        if components:
            print(f"Available {component_type}:")
            for name, component_class in components.items():
                doc = component_class.__doc__ or "No description available"
                # Take first line of docstring
                description = doc.split("\n")[0].strip()
                print(f"  - {name}: {description}")
                logger.debug(
                    "%s %s: %s",
                    component_type.rstrip("s").title(),
                    name,
                    component_class,
                )
        else:
            print(
                f"No {component_type} available. Register {component_type} to see them here."
            )
            logger.warning("No %s registered in orchestrator", component_type)

    def format_runbook_validation(self, runbook: Runbook) -> None:
        """Format and print runbook validation results.

        Args:
            runbook: Validated runbook YAML file
        """
        print(f"✓ Runbook '{runbook.name}' is valid")
        print(f"  Description: {runbook.description}")
        print(f"  Connectors: {len(runbook.connectors)}")
        print(f"  Plugins: {len(runbook.plugins)}")
        print(f"  Execution order: {', '.join(runbook.execution_order)}")

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
    print(f"✗ {message}: {error}")
    raise typer.Exit(1) from error


def run_analyses_command(
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

    logging.info("Starting WCT analysis")

    try:
        runner = AnalysisRunner()
        results = runner.run_analysis(runbook_path, output_dir, verbose)

        formatter = OutputFormatter()
        formatter.format_analysis_results(results, verbose)

    except CLIError as e:
        handle_cli_error(e, "Analysis failed")


def list_connectors_command(log_level: str = "INFO") -> None:
    """CLI command implementation for listing connectors.

    Args:
        log_level: Logging level
    """

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
        validator = RunbookValidator()
        runbook_config = validator.validate_runbook(runbook_path)

        formatter = OutputFormatter()
        formatter.format_runbook_validation(runbook_config)

    except CLIError as e:
        handle_cli_error(e, "Runbook validation failed")
