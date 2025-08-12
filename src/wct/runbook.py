"""Runbook management and loading functionality for WCT.

This module provides classes for loading, parsing, and validating YAML-based runbook
configurations that define WCT analysis pipelines. Runbooks specify:
- Data source connections (connectors)
- Analysis operations (analysers)
- Execution orchestration with schema-aware data flow
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import jsonschema
import yaml

from wct.analysers.base import AnalyserConfig
from wct.connectors.base import ConnectorConfig
from wct.errors import WCTError
from wct.schemas import RunbookSchema, SchemaLoadError

logger = logging.getLogger(__name__)

# No longer needed - using dict[str, Any] directly for context

__all__ = [
    "Runbook",
    "RunbookSummary",
    "RunbookLoader",
    "ExecutionStep",
    "RunbookError",
    "RunbookLoadError",
    "RunbookValidationError",
]


@dataclass(frozen=True, slots=True)
class RunbookSummary:
    """Strongly typed summary of runbook configuration and statistics.

    Provides comprehensive overview of runbook complexity and component breakdown
    useful for debugging, monitoring, and reporting purposes.
    """

    name: str
    """Display name of the runbook."""

    description: str
    """Description text explaining the runbook's purpose."""

    connector_count: int
    """Number of configured connector instances."""

    analyser_count: int
    """Number of configured analyser instances."""

    execution_steps: int
    """Number of execution pipeline steps."""

    connector_types: list[str]
    """Unique connector types used in the runbook."""

    analyser_types: list[str]
    """Unique analyser types used in the runbook."""


@dataclass(frozen=True, slots=True)
class ExecutionStep:
    """Represents a step in the execution pipeline with schema-aware configuration.

    All execution steps require explicit schema specification to ensure proper
    type-safe data flow between connectors and analysers.
    """

    connector: str
    analyser: str
    input_schema_name: str
    output_schema_name: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Runbook:
    """A runbook defining the complete WCT analysis pipeline configuration.

    The runbook system enables reproducible, configurable compliance analysis
    workflows that can be version-controlled and shared across environments.
    """

    name: str
    description: str
    connectors: list[ConnectorConfig]
    analysers: list[AnalyserConfig]
    execution: list[ExecutionStep]  # Analyser execution steps with schema info

    def get_summary(self) -> RunbookSummary:
        """Generate a comprehensive summary of the runbook configuration.

        Provides statistical overview and component breakdown useful for
        debugging, monitoring, and reporting on runbook complexity.

        Returns:
            RunbookSummary instance with strongly typed configuration statistics
        """
        return RunbookSummary(
            name=self.name,
            description=self.description,
            connector_count=len(self.connectors),
            analyser_count=len(self.analysers),
            execution_steps=len(self.execution),
            connector_types=list({conn.type for conn in self.connectors}),
            analyser_types=list({analyser.type for analyser in self.analysers}),
        )


class RunbookLoader:
    """Loads and parses YAML runbook files into validated configuration objects."""

    def __init__(self) -> None:
        """Initialize with runbook schema for validation."""
        self.runbook_schema = RunbookSchema()

    @classmethod
    def load(cls, runbook_path: Path) -> Runbook:
        """Load and validate a runbook from a YAML file.

        Args:
            runbook_path: Path to the runbook YAML file

        Returns:
            Fully loaded and validated Runbook instance

        Raises:
            RunbookLoadError: If the file cannot be read or parsed
            RunbookValidationError: If the runbook configuration is invalid
        """
        loader = cls()
        logger.debug("Loading runbook from: %s", runbook_path)

        try:
            raw_data = loader._load_runbook_file(runbook_path)
            loader._validate_runbook_schema(raw_data)
            runbook = loader._parse_runbook_data(raw_data)
            loader._validate_cross_references(runbook)

            logger.info("Successfully loaded runbook: %s", runbook.name)
            return runbook

        except Exception as e:
            if isinstance(e, RunbookLoadError | RunbookValidationError):
                raise
            raise RunbookLoadError(f"Failed to load runbook {runbook_path}: {e}") from e

    def _load_runbook_file(self, file_path: Path) -> dict[str, Any]:
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
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise RunbookLoadError(f"Invalid YAML in {file_path}: {e}") from e
        except OSError as e:
            raise RunbookLoadError(f"Cannot read file {file_path}: {e}") from e

    def _validate_runbook_schema(self, data: dict[str, Any]) -> None:
        """Validate runbook data against JSON schema.

        Args:
            data: Raw runbook data from YAML

        Raises:
            RunbookValidationError: If the runbook doesn't match the schema
        """
        try:
            # Validate the runbook data against the schema
            jsonschema.validate(data, self.runbook_schema.schema)

            logger.debug("Runbook schema validation passed")

        except SchemaLoadError as e:
            raise RunbookValidationError(f"Could not load runbook schema: {e}") from e
        except jsonschema.ValidationError as e:
            # Create user-friendly error message
            path = (
                " -> ".join(str(p) for p in e.absolute_path)
                if e.absolute_path
                else "root"
            )
            raise RunbookValidationError(
                f"Invalid runbook structure at '{path}': {e.message}"
            ) from e
        except jsonschema.SchemaError as e:
            raise RunbookValidationError(
                f"Invalid runbook schema definition: {e}"
            ) from e

    def _validate_cross_references(self, runbook: Runbook) -> None:
        """Validate cross-references between execution steps and their components.

        This handles validation logic that cannot be expressed in JSON Schema:
        - Name uniqueness within connector and analyser arrays
        - Cross-references from execution steps to defined connectors/analysers

        Args:
            runbook: Parsed runbook to validate

        Raises:
            RunbookValidationError: If cross-reference validation fails
        """
        # Validate name uniqueness for connectors
        connector_names = [conn.name for conn in runbook.connectors]
        duplicates = [
            name for name in set(connector_names) if connector_names.count(name) > 1
        ]
        if duplicates:
            raise RunbookValidationError(
                f"Duplicate connector names found: {duplicates}"
            )

        # Validate name uniqueness for analysers
        analyser_names = [analyser.name for analyser in runbook.analysers]
        duplicates = [
            name for name in set(analyser_names) if analyser_names.count(name) > 1
        ]
        if duplicates:
            raise RunbookValidationError(
                f"Duplicate analyser names found: {duplicates}"
            )

        # Validate execution step references
        connector_names_set = set(connector_names)
        analyser_names_set = set(analyser_names)

        for i, step in enumerate(runbook.execution):
            if step.connector not in connector_names_set:
                raise RunbookValidationError(
                    f"Execution step {i + 1} references unknown connector '{step.connector}'. "
                    f"Available connectors: {sorted(connector_names_set)}"
                )

            if step.analyser not in analyser_names_set:
                raise RunbookValidationError(
                    f"Execution step {i + 1} references unknown analyser '{step.analyser}'. "
                    f"Available analysers: {sorted(analyser_names_set)}"
                )

        logger.debug("Cross-reference validation passed")

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
        """Parse and validate connector configurations from runbook YAML.

        Processes the 'connectors' section to create ConnectorConfig instances
        with proper validation and error handling. Each connector requires
        a type field and may have optional name and properties.

        Args:
            connectors_data: List of connector configuration dictionaries from YAML

        Returns:
            List of validated ConnectorConfig instances

        Raises:
            RunbookValidationError: If connector configurations are invalid or missing required fields
        """
        connectors: list[ConnectorConfig] = []

        for i, conn_data in enumerate(connectors_data):
            try:
                # JSON Schema ensures required fields are present
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
        """Parse and validate analyser configurations from runbook YAML.

        Processes the 'analysers' section to create AnalyserConfig instances
        with comprehensive validation. Each analyser requires a type field
        and supports optional name, properties, and metadata fields.

        Args:
            analysers_data: List of analyser configuration dictionaries from YAML

        Returns:
            List of validated AnalyserConfig instances

        Raises:
            RunbookValidationError: If analyser configurations are invalid or missing required fields
        """
        analysers: list[AnalyserConfig] = []

        for i, analyser_data in enumerate(analysers_data):
            try:
                # JSON Schema ensures required fields are present
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
        """Parse and validate the execution pipeline configuration.

        Processes the 'execution' section of the runbook to create ordered
        execution steps that define the data flow from connectors to analysers.
        Each step specifies connector-analyser pairing with optional schema names.

        Args:
            data: Raw runbook data dictionary from YAML
            analysers: List of configured analyser instances for validation

        Returns:
            List of ExecutionStep objects in the specified execution order

        Raises:
            RunbookValidationError: If execution steps are malformed or missing required fields
        """
        if "execution" in data:
            # It is safe to use cast here because we validated the schema earlier with JSON Schema definitions
            execution = cast(list[dict[str, Any]], data["execution"])

            steps: list[ExecutionStep] = []
            for i, step_data in enumerate(execution):
                try:
                    # JSON Schema ensures step_data is a dict with required fields
                    steps.append(
                        ExecutionStep(
                            connector=step_data["connector"],
                            analyser=step_data["analyser"],
                            input_schema_name=step_data["input_schema_name"],
                            output_schema_name=step_data["output_schema_name"],
                            context=step_data.get("context", {}),
                        )
                    )
                except Exception as e:
                    raise RunbookValidationError(
                        f"Invalid execution step at index {i}: {e}"
                    ) from e

            return steps
        else:
            # Explicit execution steps are required for schema-aware data flow
            # Cannot auto-generate steps without knowing intended connector-analyser pairing
            raise RunbookValidationError(
                "'execution' section is required and must specify both 'connector' and 'analyser' for each pipeline step"
            )


class RunbookError(WCTError):
    """Base exception for generic runbook-related errors."""

    pass


class RunbookLoadError(RunbookError):
    """Raised when a runbook file cannot be loaded or parsed."""

    pass


class RunbookValidationError(RunbookError):
    """Raised when runbook configuration is structurally invalid."""

    pass
