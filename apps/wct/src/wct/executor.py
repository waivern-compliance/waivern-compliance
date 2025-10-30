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

from waivern_community.analysers.data_subject_analyser import (
    DataSubjectAnalyserFactory,
)
from waivern_community.analysers.processing_purpose_analyser import (
    ProcessingPurposeAnalyserFactory,
)
from waivern_community.connectors import (
    FilesystemConnectorFactory,
    SourceCodeConnectorFactory,
    SQLiteConnectorFactory,
)
from waivern_core import Analyser, AnalyserError, Connector, ConnectorError
from waivern_core.component_factory import ComponentFactory
from waivern_core.errors import WaivernError
from waivern_core.schemas import Schema
from waivern_core.services.container import ServiceContainer
from waivern_llm import BaseLLMService
from waivern_llm.di.factory import LLMServiceFactory
from waivern_mysql import MySQLConnectorFactory
from waivern_personal_data_analyser import PersonalDataAnalyserFactory

from wct.analysis import AnalysisResult
from wct.runbook import (
    AnalyserConfig,
    ConnectorConfig,
    ExecutionStep,
    Runbook,
    RunbookLoader,
)

logger = logging.getLogger(__name__)


class Executor:
    """Main executor for the Waivern Compliance Tool.

    The Executor follows a middleware design pattern, managing the
    flow of data between connectors and analysers based on a runbook
    configuration. It is responsible for loading runbook files,
    loading connectors and analysers, and executing the analysis
    workflow defined within the runbooks.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise the executor with DI container and empty factory registries.

        Args:
            container: DI container managing infrastructure services

        """
        self._container = container
        self.connector_factories: dict[str, ComponentFactory[Connector]] = {}
        self.analyser_factories: dict[str, ComponentFactory[Analyser]] = {}

    @classmethod
    def create_with_built_ins(cls) -> Executor:
        """Create an executor pre-configured with all built-in connectors and analysers.

        This method:
        1. Creates and configures the DI container with infrastructure services
        2. Instantiates all component factories with injected dependencies
        3. Registers factories with the executor

        Returns:
            Configured executor with all built-in component factories registered

        """
        # Create and configure DI container
        container = ServiceContainer()
        container.register(BaseLLMService, LLMServiceFactory(), lifetime="singleton")
        logger.debug("ServiceContainer configured with infrastructure services")

        # Create executor with container
        executor = cls(container)

        # Get infrastructure services from container (may be None if unavailable)
        try:
            llm_service = container.get_service(BaseLLMService)
            logger.debug("Retrieved LLM service from container")
        except ValueError:
            llm_service = None
            logger.warning(
                "LLM service unavailable - analysers will run without LLM validation"
            )

        # Register analyser factories with LLM service dependency
        executor.register_analyser_factory(PersonalDataAnalyserFactory(llm_service))
        executor.register_analyser_factory(
            ProcessingPurposeAnalyserFactory(llm_service)
        )
        executor.register_analyser_factory(DataSubjectAnalyserFactory(llm_service))

        # Register connector factories (no service dependencies)
        executor.register_connector_factory(FilesystemConnectorFactory())
        executor.register_connector_factory(SourceCodeConnectorFactory())
        executor.register_connector_factory(SQLiteConnectorFactory())
        executor.register_connector_factory(MySQLConnectorFactory())

        logger.info(
            "Executor initialised with %d connector factories and %d analyser factories",
            len(executor.connector_factories),
            len(executor.analyser_factories),
        )

        return executor

    # The following four methods allow for dynamic registration of factories.
    # They are for system-wide registration of available component factories,
    # not for holding the configured component instances for individual runbooks.

    def register_connector_factory(self, factory: ComponentFactory[Connector]) -> None:
        """Register a connector factory.

        Args:
            factory: ComponentFactory that creates connector instances

        """
        component_name = factory.get_component_name()
        self.connector_factories[component_name] = factory
        logger.debug("Registered connector factory: %s", component_name)

    def register_analyser_factory(self, factory: ComponentFactory[Analyser]) -> None:
        """Register an analyser factory.

        Args:
            factory: ComponentFactory that creates analyser instances

        """
        component_name = factory.get_component_name()
        self.analyser_factories[component_name] = factory
        logger.debug("Registered analyser factory: %s", component_name)

    def list_available_connectors(self) -> dict[str, ComponentFactory[Connector]]:
        """Get available connector factories.

        Returns:
            Dictionary mapping component names to connector factories

        """
        return self.connector_factories.copy()

    def list_available_analysers(self) -> dict[str, ComponentFactory[Analyser]]:
        """Get all available analyser factories.

        Returns:
            Dictionary mapping component names to analyser factories

        """
        return self.analyser_factories.copy()

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
        logger.info("Executing analysis: %s", step.name)
        if step.description:
            logger.info("Analysis description: %s", step.description)

        try:
            # Get configurations and validate types
            analyser_config, connector_config = self._get_step_configs(step, runbook)
            analyser_type, connector_type = self._validate_step_types(
                step, analyser_config, connector_config
            )

            # Set up components and schemas
            analyser, connector = self._instantiate_components(
                analyser_type, connector_type, analyser_config, connector_config
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
    ) -> tuple[str, str]:
        """Validate that analyser and connector types are registered with executor.

        Returns:
            Tuple of (analyser_type_name, connector_type_name)

        Raises:
            ExecutorError: If analyser or connector type not registered

        """
        if analyser_config.type not in self.analyser_factories:
            raise ExecutorError(f"Unknown analyser type: {analyser_config.type}")

        if connector_config.type not in self.connector_factories:
            raise ExecutorError(f"Unknown connector type: {connector_config.type}")

        return analyser_config.type, connector_config.type

    def _instantiate_components(
        self,
        analyser_type: str,
        connector_type: str,
        analyser_config: AnalyserConfig,
        connector_config: ConnectorConfig,
    ) -> tuple[Analyser, Connector]:
        """Instantiate analyser and connector from their configurations using factories.

        Args:
            analyser_type: Analyser type name (registered factory key)
            connector_type: Connector type name (registered factory key)
            analyser_config: Analyser configuration from runbook
            connector_config: Connector configuration from runbook

        Returns:
            Tuple of (analyser_instance, connector_instance)

        Raises:
            ExecutorError: If factory not found or component cannot be created

        """
        # Get factories from registries
        analyser_factory = self.analyser_factories.get(analyser_type)
        if not analyser_factory:
            raise ExecutorError(f"Unknown analyser type: {analyser_type}")

        connector_factory = self.connector_factories.get(connector_type)
        if not connector_factory:
            raise ExecutorError(f"Unknown connector type: {connector_type}")

        # Pass raw properties dict to factories - they convert to their specific config types
        analyser_properties = analyser_config.properties or {}
        connector_properties = connector_config.properties

        # Check availability before creation
        if not analyser_factory.can_create(analyser_properties):
            error_msg = f"Analyser '{analyser_type}' cannot be created with given configuration. "
            # Add helpful context if LLM validation might be the issue
            if analyser_config.properties and analyser_config.properties.get(
                "llm_validation", {}
            ).get("enable_llm_validation"):
                error_msg += "LLM service may be unavailable (required when LLM validation is enabled)."
            raise ExecutorError(error_msg)

        if not connector_factory.can_create(connector_properties):
            raise ExecutorError(
                f"Connector '{connector_type}' cannot be created with given configuration"
            )

        # Create component instances (transient lifecycle)
        logger.debug("Creating analyser instance: %s", analyser_type)
        analyser = analyser_factory.create(analyser_properties)

        logger.debug("Creating connector instance: %s", connector_type)
        connector = connector_factory.create(connector_properties)

        return analyser, connector

    def _resolve_step_schemas(
        self, step: ExecutionStep, analyser: Analyser
    ) -> tuple[Schema, Schema]:
        """Resolve input and output schemas for the step.

        Schema validation is handled during runbook loading and analyser
        initialization, so we just need to find the matching schemas.
        """
        # Find input schema by name (validated during runbook loading)
        supported_input_schemas = analyser.get_supported_input_schemas()
        input_schema = next(
            (s for s in supported_input_schemas if s.name == step.input_schema),
            None,
        )

        # Find output schema by name (validated during runbook loading)
        supported_output_schemas = analyser.get_supported_output_schemas()
        output_schema = next(
            (s for s in supported_output_schemas if s.name == step.output_schema),
            None,
        )

        # These should never be None due to earlier validation, but check for safety
        if input_schema is None:
            raise ExecutorError(f"Input schema '{step.input_schema}' not found")
        if output_schema is None:
            raise ExecutorError(f"Output schema '{step.output_schema}' not found")

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

        return AnalysisResult(
            analysis_name=step.name,
            analysis_description=step.description,
            input_schema=input_schema.name,
            output_schema=output_schema.name,
            data=result_message.content,
            metadata=analyser_config.metadata,
            contact=step.contact,
            success=True,
        )

    def _handle_step_error(
        self, step: ExecutionStep, error: Exception
    ) -> AnalysisResult:
        """Handle execution errors and return appropriate error result."""
        logger.error(f"Step execution failed for {step.name}: {error}")
        return self._create_error_result(
            step.name,
            step.description,
            error_message=str(error),
            input_schema=step.input_schema,
            output_schema=step.output_schema,
            contact=step.contact,
        )

    def _create_error_result(
        self,
        analysis_name: str,
        analysis_description: str,
        error_message: str,
        input_schema: str = "unknown",
        output_schema: str = "unknown",
        contact: str | None = None,
    ) -> AnalysisResult:
        """Create an error result for a failed analysis execution.

        Args:
            analysis_name: Name of the analysis that failed
            analysis_description: Description of the analysis that failed
            error_message: Description of the error
            input_schema: Input schema name (if known)
            output_schema: Output schema name (if known)
            contact: Optional contact information for the analysis step

        Returns:
            Analysis result indicating failure

        """
        return AnalysisResult(
            analysis_name=analysis_name,
            analysis_description=analysis_description,
            input_schema=input_schema,
            output_schema=output_schema,
            data={},
            contact=contact,
            success=False,
            error_message=error_message,
        )


class ExecutorError(WaivernError):
    """Base exception for executor errors."""
