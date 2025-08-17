"""Executor module for the Waivern Compliance Tool.

This module provides the main execution engine for WCT, including:
- Executor: Main class that manages the execution of runbooks
- ExecutorError: Exception class for executor-related errors

The Executor follows a middleware design pattern, managing the flow of data
between connectors and analysers based on runbook configurations.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from wct.analysers import Analyser, AnalyserError
from wct.analysis import AnalysisResult
from wct.connectors import Connector, ConnectorError
from wct.errors import WCTError
from wct.runbook import (
    AnalyserConfig,
    ConnectorConfig,
    ExecutionStep,
    Runbook,
    RunbookLoader,
)
from wct.schemas import Schema

logger = logging.getLogger(__name__)


class Executor:
    """Main executor for the Waivern Compliance Tool.

    The Executor follows a middleware design pattern, managing the
    flow of data between connectors and analysers based on a runbook
    configuration. It is responsible for loading runbook files,
    loading connectors and analysers, and executing the analysis
    workflow defined within the runbooks.
    """

    def __init__(self) -> None:
        """Initialise the executor with empty connector and analyser registries."""
        self.connectors: dict[str, type[Connector]] = {}
        self.analysers: dict[str, type[Analyser]] = {}

    # The following four methods allow for dynamic registration of connectors and analysers.
    # They are for system-wide registration of available connectors and analysers,
    # not for holding the configured connectors and analysers for individual runbooks.

    def register_available_connector(self, connector_class: type[Connector]) -> None:
        """Register a connector class."""
        self.connectors[connector_class.get_name()] = connector_class

    def register_available_analyser(self, analyser_class: type[Analyser]) -> None:
        """Register an analyser class."""
        self.analysers[analyser_class.get_name()] = analyser_class

    def list_available_connectors(self) -> dict[str, type[Connector]]:
        """Get available built-in connectors."""
        return self.connectors.copy()

    def list_available_analysers(self) -> dict[str, type[Analyser]]:
        """Get all available built-in analysers."""
        return self.analysers.copy()

    def execute_runbook(self, runbook_path: Path) -> list[AnalysisResult]:
        """Load and execute a runbook file."""
        try:
            runbook = RunbookLoader.load(runbook_path)
        except Exception as e:
            raise ExecutorError(f"Failed to load runbook {runbook_path}: {e}") from e

        results: list[AnalysisResult] = []
        for step in runbook.execution:
            result = self._execute_step(step, runbook)
            results.append(result)

        return results

    def _execute_step(self, step: ExecutionStep, runbook: Runbook) -> AnalysisResult:
        """Execute a single step in the runbook."""
        try:
            # Get configurations and validate types
            analyser_config, connector_config = self._get_step_configs(step, runbook)
            analyser_class, connector_class = self._validate_step_types(
                step, analyser_config, connector_config
            )

            # Set up components and schemas
            analyser, connector = self._instantiate_components(
                analyser_class, connector_class, analyser_config, connector_config
            )
            input_schema, output_schema = self._resolve_step_schemas(step, analyser)

            # Execute the analysis
            return self._run_step_analysis(
                step, analyser, connector, input_schema, output_schema, analyser_config
            )

        except (ConnectorError, AnalyserError, ExecutorError, Exception) as e:
            return self._handle_step_error(step, e)

    def _get_step_configs(
        self, step: ExecutionStep, runbook: Runbook
    ) -> tuple[AnalyserConfig, ConnectorConfig]:
        """Get analyser and connector configurations for the step.

        Configurations are guaranteed to exist by Pydantic model validation.
        """
        analyser_config = next(p for p in runbook.analysers if p.name == step.analyser)
        connector_config = next(
            c for c in runbook.connectors if c.name == step.connector
        )
        return analyser_config, connector_config

    def _validate_step_types(
        self,
        step: ExecutionStep,
        analyser_config: AnalyserConfig,
        connector_config: ConnectorConfig,
    ) -> tuple[type[Analyser], type[Connector]]:
        """Validate that analyser and connector types are registered with executor."""
        analyser_class = self.analysers.get(analyser_config.type)
        if not analyser_class:
            raise ExecutorError(f"Unknown analyser type: {analyser_config.type}")

        connector_class = self.connectors.get(connector_config.type)
        if not connector_class:
            raise ExecutorError(f"Unknown connector type: {connector_config.type}")

        return analyser_class, connector_class

    def _instantiate_components(
        self,
        analyser_class: type[Analyser],
        connector_class: type[Connector],
        analyser_config: AnalyserConfig,
        connector_config: ConnectorConfig,
    ) -> tuple[Analyser, Connector]:
        """Instantiate analyser and connector from their configurations."""
        analyser = analyser_class.from_properties(analyser_config.properties or {})
        connector = connector_class.from_properties(connector_config.properties)
        return analyser, connector

    def _resolve_step_schemas(
        self, step: ExecutionStep, analyser: Analyser
    ) -> tuple[Schema, Schema]:
        """Resolve input and output schemas for the step."""
        # Resolve input schema
        supported_input_schemas = analyser.get_supported_input_schemas()
        input_schema = next(
            (s for s in supported_input_schemas if s.name == step.input_schema_name),
            None,
        )
        if not input_schema:
            available_schemas = [s.name for s in supported_input_schemas]
            raise ExecutorError(
                f"Schema '{step.input_schema_name}' not supported. "
                f"Available schemas: {available_schemas}"
            )

        # Resolve output schema
        supported_output_schemas = analyser.get_supported_output_schemas()
        output_schema = next(
            (s for s in supported_output_schemas if s.name == step.output_schema_name),
            None,
        )
        if not output_schema:
            available_schemas = [s.name for s in supported_output_schemas]
            raise ExecutorError(
                f"Schema '{step.output_schema_name}' not supported. "
                f"Available schemas: {available_schemas}"
            )

        return input_schema, output_schema

    def _run_step_analysis(
        self,
        step: ExecutionStep,
        analyser: Analyser,
        connector: Connector,
        input_schema: Schema,
        output_schema: Schema,
        analyser_config: AnalyserConfig,
    ) -> AnalysisResult:
        """Execute the actual analysis step."""
        # Extract data from connector
        connector_message = connector.extract(input_schema)

        # Run the analyser with the extracted data
        result_message = analyser.process(
            input_schema, output_schema, connector_message
        )

        # Construct and return the analysis result
        return AnalysisResult(
            analyser_name=step.analyser,
            input_schema=input_schema.name,
            output_schema=output_schema.name,
            data=result_message.content,
            metadata=analyser_config.metadata,
            success=True,
        )

    def _handle_step_error(
        self, step: ExecutionStep, error: Exception
    ) -> AnalysisResult:
        """Handle execution errors and return appropriate error result."""
        logger.error(f"Step execution failed for {step.analyser}: {error}")
        return self._create_error_result(
            step.analyser,
            error_message=str(error),
            input_schema=step.input_schema_name,
            output_schema=step.output_schema_name,
        )

    def _create_error_result(
        self,
        analyser_name: str,
        error_message: str,
        input_schema: str = "unknown",
        output_schema: str = "unknown",
        metadata: dict[str, Any] | None = None,
    ) -> AnalysisResult:
        """Create an error result for a failed analyser execution.

        Args:
            analyser_name: Name of the analyser that failed
            error_message: Description of the error
            input_schema: Input schema name (if known)
            output_schema: Output schema name (if known)
            metadata: Optional metadata

        Returns:
            Analysis result indicating failure

        """
        return AnalysisResult(
            analyser_name=analyser_name,
            input_schema=input_schema,
            output_schema=output_schema,
            data={},
            metadata=metadata or {},
            success=False,
            error_message=error_message,
        )


class ExecutorError(WCTError):
    """Base exception for executor errors."""
