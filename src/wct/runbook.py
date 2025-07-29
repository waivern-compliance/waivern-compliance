"""Runbook management and loading functionality for WCT."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from wct.connectors.base import ConnectorConfig
from wct.errors import WCTError
from wct.plugins.base import PluginConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExecutionStep:
    """Represents a step in the execution order with detailed configuration.

    Each execution step specifies:
    - connector: Name of the connector to use for data extraction
    - plugin: Name of the plugin to use for analysis
    - input_schema_name: Name of the JSON schema for input validation
    - output_schema_name: Name of the JSON schema for output validation (optional)
    - context: Additional metadata and configuration context (optional)
    """

    connector: str
    plugin: str
    input_schema_name: str | None = None
    output_schema_name: str | None = None
    context: dict[str, Any] | None = None

    def __post_init__(self):
        """Validate required fields."""
        if not self.connector:
            raise ValueError("connector field is required")
        if not self.plugin:
            raise ValueError("plugin field is required")


@dataclass(frozen=True, slots=True)
class Runbook:
    """A runbook defining the analysis pipeline.

    Runbooks are the core configuration concept in WCT that define:
    - What data sources to connect to (connectors)
    - What analysis to perform (plugins)
    - How to orchestrate the analysis workflow (execution steps)
    """

    name: str
    description: str
    connectors: list[ConnectorConfig]
    plugins: list[PluginConfig]
    execution: list[ExecutionStep]  # Plugin execution steps with schema info

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of the runbook.

        Returns:
            Dictionary with runbook statistics
        """
        return {
            "name": self.name,
            "description": self.description,
            "connector_count": len(self.connectors),
            "plugin_count": len(self.plugins),
            "execution_steps": len(self.execution),
            "connector_types": list({conn.type for conn in self.connectors}),
            "plugin_types": list({plugin.type for plugin in self.plugins}),
        }


class RunbookLoader:
    """Handles loading and parsing of runbook files."""

    def load_from_file(self, runbook_path: Path) -> Runbook:
        """Load and parse a runbook file.

        Args:
            runbook_path: Path to the runbook YAML file

        Returns:
            Parsed runbook

        Raises:
            RunbookLoadError: If the file cannot be loaded
            RunbookValidationError: If the runbook format is invalid
        """
        logger.debug("Loading runbook from: %s", runbook_path)

        try:
            raw_data = self._load_yaml_file(runbook_path)
            runbook = self._parse_runbook_data(raw_data)
            validator = RunbookValidator()
            validator.validate(runbook)

            logger.info("Successfully loaded runbook: %s", runbook.name)
            return runbook

        except Exception as e:
            if isinstance(e, (RunbookLoadError, RunbookValidationError)):
                raise
            raise RunbookLoadError(f"Failed to load runbook {runbook_path}: {e}") from e

    def _load_yaml_file(self, file_path: Path) -> dict[str, Any]:
        """Load YAML data from file.

        Args:
            file_path: Path to the YAML file

        Returns:
            Parsed YAML data as dictionary

        Raises:
            RunbookLoadError: If file cannot be read or parsed
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise RunbookLoadError(
                    f"Runbook must be a YAML object, got {type(data)}"
                )

            return data

        except yaml.YAMLError as e:
            raise RunbookLoadError(f"Invalid YAML in {file_path}: {e}") from e
        except OSError as e:
            raise RunbookLoadError(f"Cannot read file {file_path}: {e}") from e

    def _parse_runbook_data(self, data: dict[str, Any]) -> Runbook:
        """Parse raw runbook data into configuration objects.

        Args:
            data: Raw runbook data from YAML

        Returns:
            Parsed runbook

        Raises:
            RunbookValidationError: If data structure is invalid
        """
        try:
            connectors = self._parse_connectors(data.get("connectors", []))
            plugins = self._parse_plugins(data.get("plugins", []))
            execution = self._parse_execution_steps(data, plugins)

            return Runbook(
                name=data.get("name", "Unnamed Runbook"),
                description=data.get("description", ""),
                connectors=connectors,
                plugins=plugins,
                execution=execution,
            )

        except Exception as e:
            raise RunbookValidationError(f"Invalid runbook structure: {e}") from e

    def _parse_connectors(
        self, connectors_data: list[dict[str, Any]]
    ) -> list[ConnectorConfig]:
        """Parse connector configurations from runbook data.

        Args:
            connectors_data: List of connector configuration dictionaries

        Returns:
            List of parsed connector configurations
        """
        connectors = []

        for i, conn_data in enumerate(connectors_data):
            try:
                if "type" not in conn_data:
                    raise RunbookValidationError(
                        f"Connector {i} missing required 'type' field"
                    )

                connector = ConnectorConfig(
                    name=conn_data.get("name", conn_data["type"]),
                    type=conn_data["type"],
                    properties=conn_data.get("properties", {}),
                )
                connectors.append(connector)

            except Exception as e:
                raise RunbookValidationError(
                    f"Invalid connector configuration at index {i}: {e}"
                ) from e

        return connectors

    def _parse_plugins(self, plugins_data: list[dict[str, Any]]) -> list[PluginConfig]:
        """Parse plugin configurations from runbook data.

        Args:
            plugins_data: List of plugin configuration dictionaries

        Returns:
            List of parsed plugin configurations
        """
        plugins = []

        for i, plugin_data in enumerate(plugins_data):
            try:
                if "type" not in plugin_data:
                    raise RunbookValidationError(
                        f"Plugin {i} missing required 'type' field"
                    )

                plugin = PluginConfig(
                    name=plugin_data.get("name", plugin_data["type"]),
                    type=plugin_data["type"],
                    properties=plugin_data.get("properties", {}),
                    metadata=plugin_data.get("metadata", {}),
                )
                plugins.append(plugin)

            except Exception as e:
                raise RunbookValidationError(
                    f"Invalid plugin configuration at index {i}: {e}"
                ) from e

        return plugins

    def _parse_execution_steps(
        self, data: dict[str, Any], plugins: list[PluginConfig]
    ) -> list[ExecutionStep]:
        """Parse and validate plugin execution steps.

        Args:
            data: Raw runbook data
            plugins: List of configured plugins

        Returns:
            List of ExecutionStep objects in execution order
        """
        if "execution" in data:
            execution = data["execution"]
            if not isinstance(execution, list):
                raise RunbookValidationError("Execution steps must be a list")

            steps = []
            for i, step_data in enumerate(execution):
                try:
                    if isinstance(step_data, dict):
                        if "connector" not in step_data:
                            raise RunbookValidationError(
                                f"Execution step {i} missing required 'connector' field"
                            )
                        if "plugin" not in step_data:
                            raise RunbookValidationError(
                                f"Execution step {i} missing required 'plugin' field"
                            )

                        steps.append(
                            ExecutionStep(
                                connector=step_data["connector"],
                                plugin=step_data["plugin"],
                                input_schema_name=step_data.get("input_schema_name"),
                                output_schema_name=step_data.get("output_schema_name"),
                                context=step_data.get("context"),
                            )
                        )
                    else:
                        raise RunbookValidationError(
                            f"Execution step {i} must be a dict with 'connector' and 'plugin' fields, got {type(step_data)}"
                        )
                except Exception as e:
                    raise RunbookValidationError(
                        f"Invalid execution step at index {i}: {e}"
                    ) from e

            return steps
        else:
            # Execution is now required - cannot create default steps without connector specification
            raise RunbookValidationError(
                "execution is required and must specify both 'connector' and 'plugin' for each step"
            )


class RunbookValidator:
    """Validates runbook for completeness and correctness."""

    def validate(self, runbook: Runbook) -> None:
        """Validate runbook against available components.

        Args:
            runbook: Runbook to validate

        Returns:
            List of validation warnings (empty if fully valid)
        """
        # Check connector name uniqueness
        connector_names = [conn.name for conn in runbook.connectors]
        if len(connector_names) != len(set(connector_names)):
            raise RunbookValidationError("Connector names must be unique")

        # Check plugin name uniqueness
        plugin_names = [plugin.name for plugin in runbook.plugins]
        if len(plugin_names) != len(set(plugin_names)):
            raise RunbookValidationError("Plugin names must be unique")

        # Validate connector types
        for step in runbook.execution:
            if step.connector not in [conn.name for conn in runbook.connectors]:
                raise RunbookValidationError(f"Unknown connector: {step.connector}")

        # Validate plugin types
        for step in runbook.execution:
            if step.plugin not in [plugin.name for plugin in runbook.plugins]:
                raise RunbookValidationError(f"Unknown plugin: {step.plugin}")


# TODO: Consider moving this to the RunbookLoader class as a static method
def load_runbook(runbook_path: Path) -> Runbook:
    """Convenience function to load a runbook.

    Args:
        runbook_path: Path to the runbook YAML file

    Returns:
        Loaded runbook
    """
    loader = RunbookLoader()
    return loader.load_from_file(runbook_path)


class RunbookError(WCTError):
    """Base exception for runbook-related errors."""

    pass


class RunbookLoadError(RunbookError):
    """Raised when a runbook cannot be loaded."""

    pass


class RunbookValidationError(RunbookError):
    """Raised when a runbook has invalid configuration."""

    pass
