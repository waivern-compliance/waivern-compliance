from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from wct.connectors import Connector, ConnectorError
from wct.errors import WCTError
from wct.logging import get_orchestrator_logger
from wct.plugins.base import Plugin, PluginError


@dataclass(frozen=True, slots=True)
class ConnectorConfig:
    """Configuration for a connector in a runbook."""

    name: str
    type: str
    properties: dict[str, Any]


class PathConnectorConfig(BaseModel):
    """A shortcut configuration for `FileConnector` or `DirectoryConnector`, requiring only a path."""

    path: Path

    def to_connector_config(self) -> ConnectorConfig:
        """Convert to a full `ConnectorConfig`."""
        if self.path.is_file():
            connector_name = f"file_{self.path.name}"
            return ConnectorConfig(
                name=connector_name,
                type="file",
                properties={"path": self.path},
            )
        elif self.path.is_dir():
            connector_name = f"dir_{self.path.name}"
            return ConnectorConfig(
                name=connector_name,
                type="directory",
                properties={"path": self.path},
            )
        else:
            raise FileNotFoundError(self.path)


@dataclass(frozen=True, slots=True)
class PluginConfig:
    """Configuration for a plugin in a runbook."""

    name: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RunbookConfig:
    """Configuration runbook defining the analysis pipeline."""

    name: str
    description: str
    connectors: list[ConnectorConfig]
    plugins: list[PluginConfig]
    execution_order: list[str]  # Plugin execution order


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Result from a plugin analysis."""

    plugin_name: str
    input_schema: str
    output_schema: str
    data: dict[str, Any]
    metadata: dict[str, Any]
    success: bool
    error_message: str | None = None


class Orchestrator:
    """Main orchestrator for the Waivern Compliance Tool.

    The Orchestrator is the orchestrator of the WCF. It follows a middleware
    design and has three primary responsibilities:

    1. Run a list of analyses, chained or in parallel, reading YAML runbooks
    2. Managing rulesets for static analyses and orchestrating LLM calls
    3. Consolidating outputs from plugins as console output or API endpoints
    """

    def __init__(self):
        self.connectors: dict[str, type[Connector]] = {}
        self.plugins: dict[str, type[Plugin]] = {}
        self.logger = get_orchestrator_logger()
        self._discover_components()

    def _discover_components(self):
        """Discover available connectors and plugins.

        In the future, this could use entry points for plugin discovery.
        For now, we'll manually register built-in components.
        """
        # Register built-in connectors
        # TODO: Import and register FileConnector when implemented
        # self.register_connector(FileConnector)

        # Register built-in plugins
        from wct.plugins.base import ContentAnalysisPlugin

        self.register_plugin(ContentAnalysisPlugin)

    def register_connector(self, connector_class: type[Connector]):
        """Register a connector class."""
        self.connectors[connector_class.get_name()] = connector_class

    def register_plugin(self, plugin_class: type[Plugin]):
        """Register a plugin class."""
        self.plugins[plugin_class.get_name()] = plugin_class

    def load_runbook(self, runbook_path: Path) -> RunbookConfig:
        """Load and parse a runbook configuration file."""
        try:
            with open(runbook_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise OrchestratorError(
                f"Failed to load runbook {runbook_path}: {e}"
            ) from e

        try:
            connectors = [
                ConnectorConfig(
                    name=conn.get("name", conn["type"]),
                    type=conn["type"],
                    properties=conn.get("properties", {}),
                )
                for conn in data.get("connectors", [])
            ]

            plugins = [
                PluginConfig(
                    name=plugin.get("name", plugin["type"]),
                    type=plugin["type"],
                    properties=plugin.get("properties", {}),
                    metadata=plugin.get("metadata", {}),
                )
                for plugin in data.get("plugins", [])
            ]

            return RunbookConfig(
                name=data.get("name", "Unnamed Runbook"),
                description=data.get("description", ""),
                connectors=connectors,
                plugins=plugins,
                execution_order=data.get("execution_order", [p.name for p in plugins]),
            )
        except Exception as e:
            raise OrchestratorError(
                f"Invalid runbook format in {runbook_path}: {e}"
            ) from e

    def run_analysis(self, runbook: RunbookConfig) -> list[AnalysisResult]:
        """Execute analysis based on runbook configuration."""
        results = []
        schema_data: dict[str, dict[str, Any]] = {}

        # Step 1: Run connectors to extract data
        for connector_config in runbook.connectors:
            try:
                connector_class = self.connectors.get(connector_config.type)
                if not connector_class:
                    raise OrchestratorError(
                        f"Unknown connector type: {connector_config.type}"
                    )

                connector = connector_class.from_properties(connector_config.properties)

                # Extract data
                extracted_data = connector.extract(**connector_config.properties)
                schema_name = connector.get_output_schema()
                schema_data[str(schema_name)] = extracted_data

            except (ConnectorError, Exception) as e:
                # Log error but continue with other connectors
                self.logger.error("Connector %s failed: %s", connector_config.name, e)
                continue

        # Step 2: Run plugins in specified order
        for plugin_name in runbook.execution_order:
            plugin_config = next(
                (p for p in runbook.plugins if p.name == plugin_name), None
            )
            if not plugin_config:
                self.logger.warning("Plugin %s not found in runbook", plugin_name)
                continue

            plugin_class = self.plugins.get(plugin_config.type)
            if not plugin_class:
                result = AnalysisResult(
                    plugin_name=plugin_name,
                    input_schema="unknown",
                    output_schema="unknown",
                    data={},
                    metadata=plugin_config.metadata,
                    success=False,
                    error_message=f"Unknown plugin type: {plugin_config.type}",
                )
                results.append(result)
                continue

            try:
                plugin = plugin_class.from_properties(plugin_config.properties or {})

                input_schema = plugin.get_input_schema()
                if input_schema not in schema_data:
                    result = AnalysisResult(
                        plugin_name=plugin_name,
                        input_schema=input_schema,
                        output_schema=plugin.get_output_schema(),
                        data={},
                        metadata=plugin_config.metadata,
                        success=False,
                        error_message=f"Required input schema '{input_schema}' not available",
                    )
                    results.append(result)
                    continue

                # Validate input data
                input_data = schema_data[input_schema]
                plugin.validate_input(input_data)

                # Process data through plugin
                result_data = plugin.process(input_data)

                result = AnalysisResult(
                    plugin_name=plugin_name,
                    input_schema=input_schema,
                    output_schema=plugin.get_output_schema(),
                    data=result_data,
                    metadata=plugin_config.metadata,
                    success=True,
                )
                results.append(result)

                # Make output available for downstream plugins
                schema_data[plugin.get_output_schema()] = result_data

            except (PluginError, Exception) as e:
                result = AnalysisResult(
                    plugin_name=plugin_name,
                    input_schema="unknown",
                    output_schema="unknown",
                    data={},
                    metadata=plugin_config.metadata,
                    success=False,
                    error_message=str(e),
                )
                results.append(result)
                continue

        return results

    def run_runbook_file(self, runbook_path: Path) -> list[AnalysisResult]:
        """Load and execute a runbook file."""
        runbook = self.load_runbook(runbook_path)
        return self.run_analysis(runbook)

    def list_connectors(self) -> dict[str, type[Connector]]:
        """Get all registered connectors."""
        return self.connectors.copy()

    def list_plugins(self) -> dict[str, type[Plugin]]:
        """Get all registered plugins."""
        return self.plugins.copy()


class OrchestratorError(WCTError):
    """Base exception for orchestrator errors."""
