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
class Runbook:
    """A runbook defining the analysis pipeline.

    Runbooks are the core configuration concept in WCT that define:
    - What data sources to connect to (connectors)
    - What analysis to perform (plugins)
    - How to orchestrate the analysis workflow (execution order)
    """

    name: str
    description: str
    connectors: list[ConnectorConfig]
    plugins: list[PluginConfig]
    execution_order: list[str]  # Plugin execution order

    def get_connector_by_name(self, name: str) -> ConnectorConfig | None:
        """Get connector configuration by name."""
        return next((conn for conn in self.connectors if conn.name == name), None)

    def get_plugin_by_name(self, name: str) -> PluginConfig | None:
        """Get plugin configuration by name."""
        return next((plugin for plugin in self.plugins if plugin.name == name), None)

    def validate_execution_order(self) -> list[str]:
        """Validate that all plugins in execution order exist.

        Returns:
            List of validation errors (empty if valid)
        """
        plugin_names = {plugin.name for plugin in self.plugins}
        errors = []

        for plugin_name in self.execution_order:
            if plugin_name not in plugin_names:
                errors.append(
                    f"Plugin '{plugin_name}' in execution_order not found in plugins list"
                )

        return errors

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the runbook configuration.

        Returns:
            Dictionary with runbook statistics
        """
        return {
            "name": self.name,
            "description": self.description,
            "connector_count": len(self.connectors),
            "plugin_count": len(self.plugins),
            "execution_steps": len(self.execution_order),
            "connector_types": list({conn.type for conn in self.connectors}),
            "plugin_types": list({plugin.type for plugin in self.plugins}),
        }


class RunbookError(WCTError):
    """Base exception for runbook-related errors."""

    pass


class RunbookLoadError(RunbookError):
    """Raised when a runbook cannot be loaded."""

    pass


class RunbookValidationError(RunbookError):
    """Raised when a runbook has invalid configuration."""

    pass


class RunbookLoader:
    """Handles loading and parsing of runbook configuration files."""

    def load_from_file(self, runbook_path: Path) -> Runbook:
        """Load and parse a runbook configuration file.

        Args:
            runbook_path: Path to the runbook YAML file

        Returns:
            Parsed runbook configuration

        Raises:
            RunbookLoadError: If the file cannot be loaded
            RunbookValidationError: If the runbook format is invalid
        """
        logger.debug("Loading runbook from: %s", runbook_path)

        try:
            raw_data = self._load_yaml_file(runbook_path)
            runbook_config = self._parse_runbook_data(raw_data)
            self._validate_runbook(runbook_config)

            logger.info("Successfully loaded runbook: %s", runbook_config.name)
            return runbook_config

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
            with open(file_path, "r", encoding="utf-8") as f:
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
            Parsed runbook configuration

        Raises:
            RunbookValidationError: If data structure is invalid
        """
        try:
            connectors = self._parse_connectors(data.get("connectors", []))
            plugins = self._parse_plugins(data.get("plugins", []))
            execution_order = self._parse_execution_order(data, plugins)

            return Runbook(
                name=data.get("name", "Unnamed Runbook"),
                description=data.get("description", ""),
                connectors=connectors,
                plugins=plugins,
                execution_order=execution_order,
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

    def _parse_execution_order(
        self, data: dict[str, Any], plugins: list[PluginConfig]
    ) -> list[str]:
        """Parse and validate plugin execution order.

        Args:
            data: Raw runbook data
            plugins: List of configured plugins

        Returns:
            List of plugin names in execution order
        """
        if "execution_order" in data:
            execution_order = data["execution_order"]
            if not isinstance(execution_order, list):
                raise RunbookValidationError("execution_order must be a list")
            return execution_order
        else:
            # Default to plugin order if no execution order specified
            return [plugin.name for plugin in plugins]

    def _validate_runbook(self, runbook: Runbook) -> None:
        """Validate runbook configuration for consistency.

        Args:
            runbook: Runbook configuration to validate

        Raises:
            RunbookValidationError: If validation fails
        """
        self._validate_execution_order(runbook)
        self._validate_unique_names(runbook)

    def _validate_execution_order(self, runbook: Runbook) -> None:
        """Validate that execution order references existing plugins.

        Args:
            runbook: Runbook configuration to validate
        """
        plugin_names = {plugin.name for plugin in runbook.plugins}

        for plugin_name in runbook.execution_order:
            if plugin_name not in plugin_names:
                raise RunbookValidationError(
                    f"Plugin '{plugin_name}' in execution_order not found in plugins list"
                )

    def _validate_unique_names(self, runbook: Runbook) -> None:
        """Validate that connector and plugin names are unique.

        Args:
            runbook: Runbook configuration to validate
        """
        # Check connector name uniqueness
        connector_names = [conn.name for conn in runbook.connectors]
        if len(connector_names) != len(set(connector_names)):
            raise RunbookValidationError("Connector names must be unique")

        # Check plugin name uniqueness
        plugin_names = [plugin.name for plugin in runbook.plugins]
        if len(plugin_names) != len(set(plugin_names)):
            raise RunbookValidationError("Plugin names must be unique")


class RunbookValidator:
    """Validates runbook configurations for completeness and correctness."""

    def __init__(self, available_connectors: set[str], available_plugins: set[str]):
        """Initialize validator with available component types.

        Args:
            available_connectors: Set of available connector type names
            available_plugins: Set of available plugin type names
        """
        self.available_connectors = available_connectors
        self.available_plugins = available_plugins

    def validate(self, runbook: Runbook) -> list[str]:
        """Validate runbook against available components.

        Args:
            runbook: Runbook configuration to validate

        Returns:
            List of validation warnings (empty if fully valid)
        """
        warnings = []

        # Validate connector types
        for connector in runbook.connectors:
            if connector.type not in self.available_connectors:
                warnings.append(f"Unknown connector type: {connector.type}")

        # Validate plugin types
        for plugin in runbook.plugins:
            if plugin.type not in self.available_plugins:
                warnings.append(f"Unknown plugin type: {plugin.type}")

        return warnings


def load_runbook(runbook_path: Path) -> Runbook:
    """Convenience function to load a runbook configuration.

    Args:
        runbook_path: Path to the runbook YAML file

    Returns:
        Loaded runbook configuration
    """
    loader = RunbookLoader()
    return loader.load_from_file(runbook_path)


def validate_runbook_file(
    runbook_path: Path, available_connectors: set[str], available_plugins: set[str]
) -> tuple[Runbook, list[str]]:
    """Load and validate a runbook file.

    Args:
        runbook_path: Path to the runbook YAML file
        available_connectors: Set of available connector types
        available_plugins: Set of available plugin types

    Returns:
        Tuple of (runbook_config, validation_warnings)
    """
    runbook = load_runbook(runbook_path)
    validator = RunbookValidator(available_connectors, available_plugins)
    warnings = validator.validate(runbook)

    return runbook, warnings
