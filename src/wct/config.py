"""Configuration data classes for WCT orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class ConnectorConfig:
    """Configuration for a connector in a runbook."""

    name: str
    type: str
    properties: dict[str, Any]


class PathConnectorConfig(BaseModel):
    """A shortcut configuration for `file_reader` or
    `directory` connector, requiring only a path."""

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
