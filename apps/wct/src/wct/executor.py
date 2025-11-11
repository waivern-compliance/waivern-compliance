"""Executor module for the Waivern Compliance Tool.

This module provides the main execution engine for WCT, including:
- Executor: Main class that manages the execution of runbooks
- ExecutorError: Exception class for executor-related errors

The Executor follows a middleware design pattern, managing the flow of data
between connectors and analysers based on runbook configurations.
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from pathlib import Path

from waivern_core import Analyser, AnalyserError, Connector, ConnectorError
from waivern_core.component_factory import ComponentFactory
from waivern_core.errors import WaivernError
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_core.services.container import ServiceContainer
from waivern_llm import BaseLLMService
from waivern_llm.di.factory import LLMServiceFactory

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

    def _discover_and_register_schemas(self) -> None:
        """Discover and register schemas from entry points.

        This must be called BEFORE discovering components, as components
        may reference schemas during initialisation.
        """
        schema_eps = entry_points(group="waivern.schemas")

        logger.debug("Discovering schemas from %d entry points", len(list(schema_eps)))

        for ep in entry_points(group="waivern.schemas"):  # Re-query to avoid consuming
            try:
                register_func = ep.load()
                register_func()
                logger.debug("✓ Registered schemas from: %s", ep.name)
            except Exception as e:
                logger.warning("Failed to register schemas from %s: %s", ep.name, e)

    def _discover_connectors(self) -> None:
        """Discover connector factories from entry points."""
        connector_eps = entry_points(group="waivern.connectors")

        logger.debug(
            "Discovering connectors from %d entry points", len(list(connector_eps))
        )

        for ep in entry_points(
            group="waivern.connectors"
        ):  # Re-query to avoid consuming
            try:
                factory_class = ep.load()
                # Instantiate factory with ServiceContainer for DI
                factory = factory_class(self._container)
                self.register_connector_factory(factory)
                logger.debug("✓ Registered connector: %s", ep.name)
            except Exception as e:
                logger.warning("Failed to load connector %s: %s", ep.name, e)

    def _discover_analysers(self) -> None:
        """Discover analyser factories from entry points.

        Factories receive the ServiceContainer and resolve their own dependencies.
        """
        analyser_eps = entry_points(group="waivern.analysers")

        logger.debug(
            "Discovering analysers from %d entry points", len(list(analyser_eps))
        )

        for ep in entry_points(
            group="waivern.analysers"
        ):  # Re-query to avoid consuming
            try:
                factory_class = ep.load()
                # Instantiate factory with ServiceContainer for DI
                factory = factory_class(self._container)
                self.register_analyser_factory(factory)
                logger.debug("✓ Registered analyser: %s", ep.name)
            except Exception as e:
                logger.warning("Failed to load analyser %s: %s", ep.name, e)

    @classmethod
    def create_with_built_ins(cls) -> Executor:
        """Create an executor with components discovered via entry points.

        Components are discovered via entry points - no import-time side effects.
        This enables a true plugin architecture where any installed package can
        provide connectors, analysers, or rulesets.

        Returns:
            Configured executor with all discovered component factories registered

        """
        # Create and configure DI container
        container = ServiceContainer()
        container.register(BaseLLMService, LLMServiceFactory(), lifetime="singleton")
        logger.debug("ServiceContainer configured with infrastructure services")

        # Create executor with container
        executor = cls(container)

        # CRITICAL: Register schemas FIRST, before loading components
        executor._discover_and_register_schemas()

        # Discover and register components (factories resolve dependencies from container)
        executor._discover_connectors()
        executor._discover_analysers()

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

        # Validate execution order (detect cycles)
        execution_order = self._build_execution_order(runbook.execution)

        results: list[AnalysisResult] = []
        artifacts: dict[str, Message] = {}

        for step in execution_order:
            analysis_result, message = self._execute_step(step, runbook, artifacts)
            results.append(analysis_result)

            # Store message in artifacts if step has save_output enabled
            if step.save_output:
                artifacts[step.id] = message
                logger.debug(f"Saved artifact from step '{step.id}' for pipeline use")

        return results

    def _build_execution_order(self, steps: list[ExecutionStep]) -> list[ExecutionStep]:
        """Build execution order and validate no circular dependencies.

        For sequential execution, this validates there are no cycles and returns
        steps in declaration order. Future enhancement can add topological sorting
        for parallel execution.

        Args:
            steps: Execution steps from runbook

        Returns:
            Steps in valid execution order (currently declaration order)

        Raises:
            ExecutorError: If circular dependencies detected

        """
        # Build dependency graph
        dependencies: dict[str, set[str]] = {}
        for step in steps:
            dependencies[step.id] = set()
            if step.input_from:
                dependencies[step.id].add(step.input_from)

        # Validate no cycles using DFS
        visited: set[str] = set()
        for step_id in dependencies:
            if self._has_cycle(step_id, dependencies, visited, set()):
                raise ExecutorError(
                    f"Circular dependency detected in execution steps involving '{step_id}'. "
                    f"Pipeline steps cannot form dependency cycles."
                )

        logger.debug("Execution order validated - no circular dependencies found")

        # For sequential execution, return in declaration order
        return steps

    def _has_cycle(
        self,
        step_id: str,
        dependencies: dict[str, set[str]],
        visited: set[str],
        rec_stack: set[str],
    ) -> bool:
        """Check for cycles in dependency graph using depth-first search.

        Args:
            step_id: Current step being checked
            dependencies: Dependency graph (step_id -> set of dependencies)
            visited: Set of all visited nodes
            rec_stack: Recursion stack for current DFS path

        Returns:
            True if cycle detected, False otherwise

        """
        visited.add(step_id)
        rec_stack.add(step_id)

        # Check all dependencies
        for dep in dependencies.get(step_id, set()):
            # If dependency not visited, recurse
            if dep not in visited:
                if self._has_cycle(dep, dependencies, visited, rec_stack):
                    return True
            # If dependency is in current recursion stack, cycle found
            elif dep in rec_stack:
                return True

        # Remove from recursion stack as we backtrack
        rec_stack.remove(step_id)
        return False

    def _execute_step(
        self,
        step: ExecutionStep,
        runbook: Runbook,
        artifacts: dict[str, Message],
    ) -> tuple[AnalysisResult, Message]:
        """Execute a single step in the runbook.

        Args:
            step: Execution step to run
            runbook: Full runbook configuration
            artifacts: Dictionary of saved Message artifacts from previous steps

        Returns:
            Tuple of (AnalysisResult for user output, Message for pipeline artifacts)

        """
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
            input_schema, output_schema = self._resolve_step_schemas(
                step, connector, analyser
            )

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
        self, step: ExecutionStep, connector: Connector, analyser: Analyser
    ) -> tuple[Schema, Schema]:
        """Resolve input and output schemas with version matching.

        Args:
            step: Execution step with schema requirements
            connector: Connector instance
            analyser: Analyser instance

        Returns:
            Tuple of (input_schema, output_schema) to use

        Raises:
            SchemaNotFoundError: If schema not supported
            VersionMismatchError: If no compatible versions found
            VersionNotSupportedError: If requested version not compatible

        """
        connector_outputs = connector.get_supported_output_schemas()
        analyser_inputs = analyser.get_supported_input_schemas()
        analyser_outputs = analyser.get_supported_output_schemas()

        # Resolve input schema (connector output → analyser input)
        input_schema = self._find_compatible_schema(
            schema_name=step.input_schema,
            requested_version=step.input_schema_version,
            producer_schemas=connector_outputs,
            consumer_schemas=analyser_inputs,
        )

        # Resolve output schema (analyser output)
        output_schema = self._find_compatible_schema(
            schema_name=step.output_schema,
            requested_version=step.output_schema_version,
            producer_schemas=analyser_outputs,
            consumer_schemas=[],  # No consumer for final output
        )

        return input_schema, output_schema

    def _filter_schemas_by_name(
        self, schemas: list[Schema], schema_name: str
    ) -> list[Schema]:
        """Filter schemas by name.

        Args:
            schemas: List of schemas to filter
            schema_name: Name to filter by

        Returns:
            List of schemas matching the name

        """
        return [s for s in schemas if s.name == schema_name]

    def _validate_schema_existence(
        self,
        filtered_schemas: list[Schema],
        schema_name: str,
        component_type: str,
        all_schemas: list[Schema],
    ) -> None:
        """Validate that schema is supported by component.

        Args:
            filtered_schemas: Schemas filtered by name
            schema_name: Name of schema being validated
            component_type: Type of component (Producer/Consumer) for error message
            all_schemas: All schemas supported by component (for error message)

        Raises:
            SchemaNotFoundError: If schema not supported

        """
        if not filtered_schemas:
            available_names = [s.name for s in all_schemas]
            raise SchemaNotFoundError(
                f"{component_type} does not support schema '{schema_name}'. "
                f"Available: {available_names}"
            )

    def _find_compatible_versions(
        self,
        producer_by_name: list[Schema],
        consumer_by_name: list[Schema],
        schema_name: str,
        has_consumer: bool,
    ) -> tuple[dict[str, Schema], set[str]]:
        """Find compatible versions between producer and consumer.

        Args:
            producer_by_name: Producer schemas filtered by name
            consumer_by_name: Consumer schemas filtered by name
            schema_name: Schema name for error messages
            has_consumer: Whether there is a consumer component

        Returns:
            Tuple of (producer_versions_dict, compatible_versions_set)

        Raises:
            VersionMismatchError: If no compatible versions found

        """
        producer_versions = {s.version: s for s in producer_by_name}
        consumer_versions: set[str] = set()

        if has_consumer:
            consumer_versions = {s.version for s in consumer_by_name}
            compatible_versions = set(producer_versions.keys()) & consumer_versions
        else:
            # No consumer - all producer versions are compatible
            compatible_versions = set(producer_versions.keys())

        if not compatible_versions:
            raise VersionMismatchError(
                f"No compatible versions for schema '{schema_name}'. "
                f"Producer supports: {sorted(producer_versions.keys())}. "
                f"Consumer supports: {sorted(consumer_versions) if has_consumer else 'N/A'}"
            )

        return producer_versions, compatible_versions

    def _select_version(
        self,
        requested_version: str | None,
        compatible_versions: set[str],
        producer_versions: dict[str, Schema],
        schema_name: str,
    ) -> Schema:
        """Select specific version from compatible versions.

        Args:
            requested_version: Explicitly requested version (if any)
            compatible_versions: Set of compatible version strings
            producer_versions: Dict mapping versions to Schema objects
            schema_name: Schema name for error messages

        Returns:
            Selected Schema object

        Raises:
            VersionNotSupportedError: If requested version not in compatible set

        """
        if requested_version:
            # Explicit version requested
            if requested_version not in compatible_versions:
                raise VersionNotSupportedError(
                    f"Requested version '{requested_version}' for schema '{schema_name}' "
                    f"not compatible. Compatible versions: {sorted(compatible_versions)}"
                )
            return producer_versions[requested_version]
        else:
            # Auto-select latest compatible version
            latest_version = max(compatible_versions, key=self._version_sort_key)
            return producer_versions[latest_version]

    def _find_compatible_schema(
        self,
        schema_name: str,
        requested_version: str | None,
        producer_schemas: list[Schema],
        consumer_schemas: list[Schema],
    ) -> Schema:
        """Find compatible schema version between producer and consumer.

        Strategy:
        - If version explicitly requested: validate and use it
        - Otherwise: select latest version both support

        Args:
            schema_name: Name of schema to find
            requested_version: Optional specific version requested
            producer_schemas: Schemas the producer can output
            consumer_schemas: Schemas the consumer can accept (empty if no consumer)

        Returns:
            Compatible Schema object

        Raises:
            SchemaNotFoundError: If schema not supported by producer/consumer
            VersionMismatchError: If no compatible versions found
            VersionNotSupportedError: If requested version not compatible

        """
        # Filter by name
        producer_by_name = self._filter_schemas_by_name(producer_schemas, schema_name)
        consumer_by_name = self._filter_schemas_by_name(consumer_schemas, schema_name)

        # Validate schema is supported
        self._validate_schema_existence(
            producer_by_name, schema_name, "Producer", producer_schemas
        )
        if consumer_schemas:
            self._validate_schema_existence(
                consumer_by_name, schema_name, "Consumer", consumer_schemas
            )

        # Find compatible versions
        producer_versions, compatible_versions = self._find_compatible_versions(
            producer_by_name, consumer_by_name, schema_name, bool(consumer_schemas)
        )

        # Select version (explicit or auto-select latest)
        return self._select_version(
            requested_version, compatible_versions, producer_versions, schema_name
        )

    def _version_sort_key(self, version: str) -> tuple[int, int, int]:
        """Convert version string to sortable tuple.

        Args:
            version: Version string like "1.2.3"

        Returns:
            Tuple of (major, minor, patch) for sorting

        Raises:
            ExecutorError: If version format is invalid

        """
        try:
            parts = version.split(".")
            expected_parts = 3
            if len(parts) != expected_parts:
                raise ValueError(
                    "Version must have exactly 3 parts (major.minor.patch)"
                )
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid semantic version format: '{version}' - {e}")
            raise ExecutorError(
                f"Invalid semantic version '{version}': must be in format 'major.minor.patch' (e.g., '1.2.3')"
            ) from e

    def _run_step_analysis(
        self,
        step: ExecutionStep,
        analyser: Analyser,
        connector: Connector,
        input_schema: Schema,
        output_schema: Schema,
        analyser_config: AnalyserConfig,
    ) -> tuple[AnalysisResult, Message]:
        """Execute the actual analysis step.

        Returns:
            Tuple of (AnalysisResult for user output, Message for pipeline artifacts)

        """
        # Extract data from connector
        connector_message = connector.extract(input_schema)

        # Run the analyser with the extracted data
        result_message = analyser.process(
            input_schema, output_schema, connector_message
        )

        analysis_result = AnalysisResult(
            analysis_name=step.name,
            analysis_description=step.description,
            input_schema=input_schema.name,
            output_schema=output_schema.name,
            data=result_message.content,
            metadata=analyser_config.metadata,
            contact=step.contact,
            success=True,
        )

        return analysis_result, result_message

    def _handle_step_error(
        self, step: ExecutionStep, error: Exception
    ) -> tuple[AnalysisResult, Message]:
        """Handle execution errors and return appropriate error result.

        Returns:
            Tuple of (error AnalysisResult, error Message with empty content)

        """
        logger.error(f"Step execution failed for {step.name}: {error}")
        error_result = self._create_error_result(
            step.name,
            step.description,
            error_message=str(error),
            input_schema=step.input_schema,
            output_schema=step.output_schema,
            contact=step.contact,
        )

        # Create error Message with empty content
        error_message = Message(
            id=step.id,
            content={},
            schema=None,
        )

        return error_result, error_message

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


class SchemaNotFoundError(ExecutorError):
    """Raised when required schema is not supported by component."""


class VersionMismatchError(ExecutorError):
    """Raised when no compatible schema versions found."""


class VersionNotSupportedError(ExecutorError):
    """Raised when explicitly requested version is not compatible."""
