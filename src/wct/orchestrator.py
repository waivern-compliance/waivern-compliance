from __future__ import annotations

from pathlib import Path
from typing import Any

from wct.analysis import AnalysisResult
from wct.connectors import Connector, ConnectorConfig, ConnectorError
from wct.errors import WCTError
from wct.logging import get_orchestrator_logger
from wct.plugins import Plugin, PluginConfig, PluginError
from wct.runbook import Runbook
from wct.runbook import load_runbook


class Orchestrator:
    """Main executor for the Waivern Compliance Tool.

    The Orchestrator follows a middleware design pattern, managing the
    flow of data between connectors and plugins based on a runbook
    configuration. It is responsible for loading runbook files,
    loading connectors and plugins, and executing the analysis
    workflow defined within the runbooks.
    """

    def __init__(self):
        self.connectors: dict[str, type[Connector[Any]]] = {}
        self.plugins: dict[str, type[Plugin[Any, Any]]] = {}
        self.logger = get_orchestrator_logger()

    def register_connector(self, connector_class: type[Connector[Any]]):
        """Register a connector class."""
        self.connectors[connector_class.get_name()] = connector_class

    def register_plugin(self, plugin_class: type[Plugin[Any, Any]]):
        """Register a plugin class."""
        self.plugins[plugin_class.get_name()] = plugin_class

    def load_runbook(self, runbook_path: Path) -> Runbook:
        """Load and parse a runbook file."""
        try:
            return load_runbook(runbook_path)
        except Exception as e:
            raise OrchestratorError(
                f"Failed to load runbook {runbook_path}: {e}"
            ) from e

    def run_analysis(self, runbook: Runbook) -> list[AnalysisResult]:
        """Execute analysis based on a runbook."""
        results = []
        schema_data: dict[str, dict[str, Any]] = {}

        # Step 1: Extract data from all connectors
        schema_data.update(self._extract_data_from_connectors(runbook.connectors))

        # Step 2: Execute plugins in specified order
        plugin_results = self._execute_plugins_in_order(
            runbook.plugins, runbook.execution_order, schema_data
        )
        results.extend(plugin_results)

        return results

    def _extract_data_from_connectors(
        self, connector_configs: list[ConnectorConfig]
    ) -> dict[str, dict[str, Any]]:
        """Extract data from all configured connectors.

        Args:
            connector_configs: List of connector configurations

        Returns:
            Dictionary mapping schema names to extracted data
        """
        schema_data: dict[str, dict[str, Any]] = {}

        for connector_config in connector_configs:
            try:
                extracted_data = self._run_single_connector(connector_config)
                if extracted_data:
                    schema_data.update(extracted_data)
            except (ConnectorError, Exception) as e:
                self.logger.error("Connector %s failed: %s", connector_config.name, e)
                continue

        return schema_data

    def _run_single_connector(
        self, connector_config: ConnectorConfig
    ) -> dict[str, dict[str, Any]] | None:
        """Run a single connector and return its extracted data.

        Args:
            connector_config: Configuration for the connector to run

        Returns:
            Dictionary with schema name mapped to extracted data, or None if failed
        """
        connector_class = self.connectors.get(connector_config.type)
        if not connector_class:
            raise OrchestratorError(f"Unknown connector type: {connector_config.type}")

        connector = connector_class.from_properties(connector_config.properties)
        extracted_data = connector.extract()
        schema_info = connector.get_output_schema()

        return {schema_info.name: extracted_data}

    def _execute_plugins_in_order(
        self,
        plugin_configs: list[PluginConfig],
        execution_order: list[str],
        schema_data: dict[str, dict[str, Any]],
    ) -> list[AnalysisResult]:
        """Execute plugins in the specified order.

        Args:
            plugin_configs: List of plugin configurations
            execution_order: Order in which to execute plugins
            schema_data: Available schema data for plugin input

        Returns:
            List of analysis results from plugin execution
        """
        results = []

        for plugin_name in execution_order:
            plugin_config = self._find_plugin_config(plugin_configs, plugin_name)
            if not plugin_config:
                self.logger.warning("Plugin %s not found in runbook", plugin_name)
                continue

            result = self._execute_single_plugin(plugin_config, schema_data)
            results.append(result)

            # Make successful plugin output available for downstream plugins
            if result.success:
                schema_data[result.output_schema] = result.data

        return results

    def _find_plugin_config(
        self, plugin_configs: list[PluginConfig], plugin_name: str
    ) -> PluginConfig | None:
        """Find plugin configuration by name.

        Args:
            plugin_configs: List of plugin configurations
            plugin_name: Name of plugin to find

        Returns:
            Plugin configuration if found, None otherwise
        """
        return next((p for p in plugin_configs if p.name == plugin_name), None)

    def _execute_single_plugin(
        self, plugin_config: PluginConfig, schema_data: dict[str, dict[str, Any]]
    ) -> AnalysisResult:
        """Execute a single plugin and return its result.

        Args:
            plugin_config: Configuration for the plugin to execute
            schema_data: Available schema data for plugin input

        Returns:
            Analysis result from plugin execution
        """
        plugin_class = self.plugins.get(plugin_config.type)
        if not plugin_class:
            return self._create_error_result(
                plugin_config,
                error_message=f"Unknown plugin type: {plugin_config.type}",
            )

        try:
            plugin = plugin_class.from_properties(plugin_config.properties or {})
            return self._process_plugin_data(plugin, plugin_config, schema_data)

        except (PluginError, Exception) as e:
            return self._create_error_result(
                plugin_config,
                error_message=str(e),
            )

    def _process_plugin_data(
        self,
        plugin: Plugin[Any, Any],
        plugin_config: PluginConfig,
        schema_data: dict[str, dict[str, Any]],
    ) -> AnalysisResult:
        """Process data through a plugin instance.

        Args:
            plugin: Instantiated plugin to process data
            plugin_config: Plugin configuration
            schema_data: Available schema data

        Returns:
            Analysis result from processing
        """
        input_schema_info = plugin.get_input_schema()
        output_schema_info = plugin.get_output_schema()

        # Check if required input schema is available
        if input_schema_info.name not in schema_data:
            return AnalysisResult(
                plugin_name=plugin_config.name,
                input_schema=input_schema_info.name,
                output_schema=output_schema_info.name,
                data={},
                metadata=plugin_config.metadata,
                success=False,
                error_message=f"Required input schema '{input_schema_info.name}' not available",
            )

        # Validate and process input data
        input_data = schema_data[input_schema_info.name]
        plugin.validate_input(input_data)
        result_data = plugin.process(input_data)

        return AnalysisResult(
            plugin_name=plugin_config.name,
            input_schema=input_schema_info.name,
            output_schema=output_schema_info.name,
            data=result_data,
            metadata=plugin_config.metadata,
            success=True,
        )

    def _create_error_result(
        self,
        plugin_config: PluginConfig,
        error_message: str,
        input_schema: str = "unknown",
        output_schema: str = "unknown",
    ) -> AnalysisResult:
        """Create an error result for a failed plugin execution.

        Args:
            plugin_config: Configuration of the failed plugin
            error_message: Description of the error
            input_schema: Input schema name (if known)
            output_schema: Output schema name (if known)

        Returns:
            Analysis result indicating failure
        """
        return AnalysisResult(
            plugin_name=plugin_config.name,
            input_schema=input_schema,
            output_schema=output_schema,
            data={},
            metadata=plugin_config.metadata,
            success=False,
            error_message=error_message,
        )

    def execute_runbook(self, runbook_path: Path) -> list[AnalysisResult]:
        """Load and execute a runbook file."""
        runbook = self.load_runbook(runbook_path)
        return self.run_analysis(runbook)

    def list_connectors(self) -> dict[str, type[Connector[Any]]]:
        """Get all registered connectors."""
        return self.connectors.copy()

    def list_plugins(self) -> dict[str, type[Plugin[Any, Any]]]:
        """Get all registered plugins."""
        return self.plugins.copy()


class OrchestratorError(WCTError):
    """Base exception for orchestrator errors."""
