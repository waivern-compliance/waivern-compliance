"""Runbook management and loading functionality for WCT."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from wct.analysers.base import AnalyserConfig
from wct.connectors.base import ConnectorConfig
from wct.errors import WCTError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExecutionStep:
    """Represents a step in the execution order with detailed configuration.

    Each execution step specifies:
    - connector: Name of the connector to use for data extraction
    - analyser: Name of the analyser to use for analysis
    - input_schema_name: Name of the JSON schema for input validation
    - output_schema_name: Name of the JSON schema for output validation (optional)
    - context: Additional metadata and configuration context (optional)
    """

    connector: str
    analyser: str
    input_schema_name: str | None = None
    output_schema_name: str | None = None
    context: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.connector:
            raise ValueError("connector field is required")
        if not self.analyser:
            raise ValueError("analyser field is required")


@dataclass(frozen=True, slots=True)
class Runbook:
    """A runbook defining the analysis pipeline.

    Runbooks are the core configuration concept in WCT that define:
    - What data sources to connect to (connectors)
    - What analysis to perform (analysers)
    - How to orchestrate the analysis workflow (execution steps)
    """

    name: str
    description: str
    connectors: list[ConnectorConfig]
    analysers: list[AnalyserConfig]
    execution: list[ExecutionStep]  # Analyser execution steps with schema info

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of the runbook.

        Returns:
            Dictionary with runbook statistics
        """
        return {
            "name": self.name,
            "description": self.description,
            "connector_count": len(self.connectors),
            "analyser_count": len(self.analysers),
            "execution_steps": len(self.execution),
            "connector_types": list({conn.type for conn in self.connectors}),
            "analyser_types": list({analyser.type for analyser in self.analysers}),
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
            if isinstance(e, RunbookLoadError | RunbookValidationError):
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
            analysers = self._parse_analysers(data.get("analysers", []))
            execution = self._parse_execution_steps(data, analysers)

            return Runbook(
                name=data.get("name", "Unnamed Runbook"),
                description=data.get("description", ""),
                connectors=connectors,
                analysers=analysers,
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

    def _parse_analysers(
        self, analysers_data: list[dict[str, Any]]
    ) -> list[AnalyserConfig]:
        """Parse analyser configurations from runbook data.

        Args:
            analysers_data: List of analyser configuration dictionaries

        Returns:
            List of parsed analyser configurations
        """
        analysers = []

        for i, analyser_data in enumerate(analysers_data):
            try:
                if "type" not in analyser_data:
                    raise RunbookValidationError(
                        f"Analyser {i} missing required 'type' field"
                    )

                analyser = AnalyserConfig(
                    name=analyser_data.get("name", analyser_data["type"]),
                    type=analyser_data["type"],
                    properties=analyser_data.get("properties", {}),
                    metadata=analyser_data.get("metadata", {}),
                )
                analysers.append(analyser)

            except Exception as e:
                raise RunbookValidationError(
                    f"Invalid analyser configuration at index {i}: {e}"
                ) from e

        return analysers

    def _parse_execution_steps(
        self, data: dict[str, Any], analysers: list[AnalyserConfig]
    ) -> list[ExecutionStep]:
        """Parse and validate analyser execution steps.

        Args:
            data: Raw runbook data
            analysers: List of configured analysers

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
                        if "analyser" not in step_data:
                            raise RunbookValidationError(
                                f"Execution step {i} missing required 'analyser' field"
                            )

                        steps.append(
                            ExecutionStep(
                                connector=step_data["connector"],
                                analyser=step_data["analyser"],
                                input_schema_name=step_data.get("input_schema_name"),
                                output_schema_name=step_data.get("output_schema_name"),
                                context=step_data.get("context"),
                            )
                        )
                    else:
                        raise RunbookValidationError(
                            f"Execution step {i} must be a dict with 'connector' and 'analyser' fields, got {type(step_data)}"
                        )
                except Exception as e:
                    raise RunbookValidationError(
                        f"Invalid execution step at index {i}: {e}"
                    ) from e

            return steps
        else:
            # Execution is now required - cannot create default steps without connector specification
            raise RunbookValidationError(
                "execution is required and must specify both 'connector' and 'analyser' for each step"
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

        # Check analyser name uniqueness
        analyser_names = [analyser.name for analyser in runbook.analysers]
        if len(analyser_names) != len(set(analyser_names)):
            raise RunbookValidationError("Analyser names must be unique")

        # Validate connector types
        for step in runbook.execution:
            if step.connector not in [conn.name for conn in runbook.connectors]:
                raise RunbookValidationError(f"Unknown connector: {step.connector}")

        # Validate analyser types
        for step in runbook.execution:
            if step.analyser not in [analyser.name for analyser in runbook.analysers]:
                raise RunbookValidationError(f"Unknown analyser: {step.analyser}")


# TODO: Consider moving this to the RunbookLoader class as a static method
def load_runbook(runbook_path: Path) -> Runbook:
    """Load a runbook from the specified path.

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
