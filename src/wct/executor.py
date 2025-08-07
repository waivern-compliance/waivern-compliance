"""Executor module for the Waivern Compliance Tool.

This module provides the main execution engine for WCT, including:
- Executor: Main class that manages the execution of runbooks
- ExecutorError: Exception class for executor-related errors

The Executor follows a middleware design pattern, managing the flow of data
between connectors and analysers based on runbook configurations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from wct.analysers import Analyser, AnalyserConfig, AnalyserError
from wct.analysis import AnalysisResult
from wct.connectors import Connector, ConnectorConfig, ConnectorError
from wct.errors import WCTError
from wct.logging import get_executor_logger
from wct.runbook import ExecutionStep, Runbook, load_runbook
from wct.schema import WctSchema


class Executor:
    """Main executor for the Waivern Compliance Tool.

    The Executor follows a middleware design pattern, managing the
    flow of data between connectors and analysers based on a runbook
    configuration. It is responsible for loading runbook files,
    loading connectors and analysers, and executing the analysis
    workflow defined within the runbooks.
    """

    def __init__(self):
        self.connectors: dict[str, type[Connector]] = {}
        self.analysers: dict[str, type[Analyser]] = {}
        self.logger = get_executor_logger()

    # The following four methods allow for dynamic registration of connectors and analysers.
    # They are for system-wide registration of available connectors and analysers,
    # not for holding the configured connectors and analysers for individual runbooks.

    def register_available_connector(self, connector_class: type[Connector]):
        """Register a connector class."""
        self.connectors[connector_class.get_name()] = connector_class

    def register_available_analyser(self, analyser_class: type[Analyser]):
        """Register an analyser class."""
        self.analysers[analyser_class.get_name()] = analyser_class

    def list_available_connectors(self) -> dict[str, type[Connector]]:
        """Get available built-in connectors."""
        return self.connectors.copy()

    def list_available_analysers(self) -> dict[str, type[Analyser]]:
        """Get all available built-in analysers."""
        return self.analysers.copy()

    def load_runbook(self, runbook_path: Path) -> Runbook:
        """Load and parse a runbook file."""
        try:
            return load_runbook(runbook_path)
        except Exception as e:
            raise ExecutorError(f"Failed to load runbook {runbook_path}: {e}") from e

    def execute_runbook(self, runbook_path: Path) -> list[AnalysisResult]:
        """Load and execute a runbook file."""
        runbook = self.load_runbook(runbook_path)
        return self.run_analyses(runbook)

    def run_analyses(self, runbook: Runbook) -> list[AnalysisResult]:
        """Execute analysis based on a runbook."""
        results = []

        for step in runbook.execution:
            result = self._execute_step(step, runbook)
            results.append(result)

        return results

    def _execute_step(self, step: ExecutionStep, runbook: Runbook) -> AnalysisResult:
        """Execute a single step in the runbook.

        This method handles the execution of a step, including loading
        the required analyser and connector, extracting data, and running
        the analysis analyser.

        Args:
            step: The execution step to run
            runbook: The runbook containing the step configuration

        Returns:
            AnalysisResult containing the results of the step execution
        """
        # Get the required analyser and connector for the step
        analyser_config = self._find_analyser_config(runbook.analysers, step.analyser)
        if not analyser_config:
            return self._create_error_result(
                step.analyser,
                error_message=f"Analyser '{step.analyser}' not found in runbook configuration",
            )

        connector_config = self._find_connector_config(
            runbook.connectors, step.connector
        )
        if not connector_config:
            return self._create_error_result(
                step.analyser,
                error_message=f"Connector '{step.connector}' not found in runbook configuration",
            )

        # Get analyser and connector classes
        analyser_class = self.analysers.get(analyser_config.type)
        if not analyser_class:
            return self._create_error_result(
                step.analyser,
                error_message=f"Unknown analyser type: {analyser_config.type}",
            )

        connector_class = self.connectors.get(connector_config.type)
        if not connector_class:
            return self._create_error_result(
                step.analyser,
                error_message=f"Unknown connector type: {connector_config.type}",
            )

        try:
            # Instantiate analyser and connector
            analyser = analyser_class.from_properties(analyser_config.properties or {})
            connector = connector_class.from_properties(connector_config.properties)

            # Load the specified input and output schemas
            input_schema = self._load_schema_from_step(
                step.input_schema_name, analyser.get_supported_input_schemas()
            )
            output_schema = self._load_schema_from_step(
                step.output_schema_name, analyser.get_supported_output_schemas()
            )

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

        except (ConnectorError, AnalyserError, Exception) as e:
            self.logger.error(f"Step execution failed for {step.analyser}: {e}")
            return self._create_error_result(
                step.analyser,
                error_message=str(e),
                input_schema=step.input_schema_name or "unknown",
                output_schema=step.output_schema_name or "unknown",
            )

    def _find_analyser_config(
        self, analyser_configs: list[AnalyserConfig], analyser_name: str
    ) -> AnalyserConfig | None:
        """Find analyser configuration by name.

        Args:
            analyser_configs: List of analyser configurations
            analyser_name: Name of analyser to find

        Returns:
            Analyser configuration if found, None otherwise
        """
        return next((p for p in analyser_configs if p.name == analyser_name), None)

    def _find_connector_config(
        self, connector_configs: list[ConnectorConfig], connector_name: str
    ) -> ConnectorConfig | None:
        """Find connector configuration by name.

        Args:
            connector_configs: List of connector configurations
            connector_name: Name of connector to find

        Returns:
            Connector configuration if found, None otherwise
        """
        return next((c for c in connector_configs if c.name == connector_name), None)

    def _load_schema_from_step(
        self, schema_name: str | None, supported_schemas: list[WctSchema[Any]]
    ) -> WctSchema[Any]:
        """Load schema from step configuration.

        Args:
            schema_name: Name of the schema or None
            supported_schemas: List of supported schemas from analyser

        Returns:
            WctSchema object for the requested schema

        Raises:
            ExecutorError: If schema cannot be loaded or is unsupported
        """
        if not schema_name:
            # Use first supported schema as default
            if not supported_schemas:
                raise ExecutorError("No supported schemas available")
            return supported_schemas[0]

        # Find matching supported schema
        matching_schema = next(
            (s for s in supported_schemas if s.name == schema_name), None
        )

        if not matching_schema:
            raise ExecutorError(
                f"Schema '{schema_name}' not supported. Available schemas: {[s.name for s in supported_schemas]}"
            )

        return matching_schema

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
