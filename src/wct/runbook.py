"""Runbook management with Pydantic validation for WCT.

This module provides Pydantic models and loading functionality for YAML-based runbook
configurations that define WCT analysis pipelines. Runbooks specify:
- Data source connections (connectors)
- Analysis operations (analysers)
- Execution orchestration with schema-aware data flow

All configuration uses Pydantic models for validation and runtime representation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from wct.errors import WCTError

logger = logging.getLogger(__name__)

__all__ = [
    "ConnectorConfigModel",
    "AnalyserConfigModel",
    "ExecutionStepModel",
    "RunbookModel",
    "RunbookSummaryModel",
    "RunbookLoader",
    "RunbookError",
    "RunbookLoadError",
    "RunbookValidationError",
]


class ConnectorConfigModel(BaseModel):
    """Pydantic model for connector configuration."""

    name: str = Field(
        min_length=1,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Connector instance name",
    )
    type: str = Field(min_length=1, description="Connector type identifier")
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Connector-specific configuration properties"
    )


class AnalyserConfigModel(BaseModel):
    """Pydantic model for analyser configuration."""

    name: str = Field(
        min_length=1, pattern=r"^[a-zA-Z0-9._-]+$", description="Analyser instance name"
    )
    type: str = Field(min_length=1, description="Analyser type identifier")
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Analyser-specific configuration properties"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata for the analyser"
    )


class ExecutionStepModel(BaseModel):
    """Pydantic model for execution step configuration."""

    connector: str = Field(
        min_length=1,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Name of connector instance to use",
    )
    analyser: str = Field(
        min_length=1,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Name of analyser instance to use",
    )
    input_schema_name: str = Field(
        min_length=1, description="Schema name for connector output validation"
    )
    output_schema_name: str = Field(
        min_length=1, description="Schema name for analyser output validation"
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional execution metadata and runtime configuration",
    )


class RunbookModel(BaseModel):
    """Pydantic model for complete runbook configuration."""

    name: str = Field(min_length=1, description="Runbook display name")
    description: str = Field(
        min_length=1, description="Runbook description explaining its purpose"
    )
    connectors: list[ConnectorConfigModel] = Field(
        min_length=1, description="List of data source connectors"
    )
    analysers: list[AnalyserConfigModel] = Field(
        min_length=1, description="List of analysis processors"
    )
    execution: list[ExecutionStepModel] = Field(
        min_length=1, description="Execution pipeline steps"
    )

    @field_validator("connectors")
    @classmethod
    def validate_unique_connector_names(
        cls, connectors: list[ConnectorConfigModel]
    ) -> list[ConnectorConfigModel]:
        """Validate that connector names are unique."""
        names = [conn.name for conn in connectors]
        duplicates = [name for name in set(names) if names.count(name) > 1]
        if duplicates:
            raise ValueError(f"Duplicate connector names found: {duplicates}")
        return connectors

    @field_validator("analysers")
    @classmethod
    def validate_unique_analyser_names(
        cls, analysers: list[AnalyserConfigModel]
    ) -> list[AnalyserConfigModel]:
        """Validate that analyser names are unique."""
        names = [analyser.name for analyser in analysers]
        duplicates = [name for name in set(names) if names.count(name) > 1]
        if duplicates:
            raise ValueError(f"Duplicate analyser names found: {duplicates}")
        return analysers

    @model_validator(mode="after")
    def validate_cross_references(self) -> RunbookModel:
        """Validate cross-references between execution steps and components."""
        connector_names = {conn.name for conn in self.connectors}
        analyser_names = {analyser.name for analyser in self.analysers}

        for i, step in enumerate(self.execution):
            if step.connector not in connector_names:
                raise ValueError(
                    f"Execution step {i + 1} references unknown connector '{step.connector}'. "
                    f"Available connectors: {sorted(connector_names)}"
                )

            if step.analyser not in analyser_names:
                raise ValueError(
                    f"Execution step {i + 1} references unknown analyser '{step.analyser}'. "
                    f"Available analysers: {sorted(analyser_names)}"
                )

        return self

    def get_summary(self) -> RunbookSummaryModel:
        """Generate a comprehensive summary of the runbook configuration.

        Returns:
            RunbookSummaryModel instance with configuration statistics

        """
        return RunbookSummaryModel.from_runbook(self)


class RunbookSummaryModel(BaseModel):
    """Pydantic model for runbook summary statistics."""

    name: str = Field(description="Display name of the runbook")
    description: str = Field(
        description="Description text explaining the runbook's purpose"
    )
    connector_count: int = Field(description="Number of configured connector instances")
    analyser_count: int = Field(description="Number of configured analyser instances")
    execution_steps: int = Field(description="Number of execution pipeline steps")
    connector_types: list[str] = Field(
        description="Unique connector types used in the runbook"
    )
    analyser_types: list[str] = Field(
        description="Unique analyser types used in the runbook"
    )

    @classmethod
    def from_runbook(cls, runbook: RunbookModel) -> RunbookSummaryModel:
        """Create a summary from a runbook model."""
        return cls(
            name=runbook.name,
            description=runbook.description,
            connector_count=len(runbook.connectors),
            analyser_count=len(runbook.analysers),
            execution_steps=len(runbook.execution),
            connector_types=list({conn.type for conn in runbook.connectors}),
            analyser_types=list({analyser.type for analyser in runbook.analysers}),
        )


class RunbookLoader:
    """Loads and parses YAML runbook files into validated Pydantic models."""

    @classmethod
    def load(cls, runbook_path: Path) -> RunbookModel:
        """Load and validate a runbook from a YAML file using Pydantic validation.

        Args:
            runbook_path: Path to the runbook YAML file

        Returns:
            Fully loaded and validated RunbookModel instance

        Raises:
            RunbookLoadError: If the file cannot be read or parsed
            RunbookValidationError: If the runbook configuration is invalid

        """
        logger.debug("Loading runbook from: %s", runbook_path)

        try:
            # Load raw YAML data
            raw_data = cls._load_runbook_file(runbook_path)

            # Validate using Pydantic models
            validated_model = RunbookModel.model_validate(raw_data)

            logger.info("Successfully loaded runbook: %s", validated_model.name)
            return validated_model

        except ValidationError as e:
            # Convert Pydantic validation errors to user-friendly messages
            error_details: list[str] = []
            for error in e.errors():
                location = (
                    " -> ".join(str(part) for part in error["loc"])
                    if error["loc"]
                    else "root"
                )
                error_details.append(f"  {location}: {error['msg']}")

            error_message = "Runbook validation failed:\n" + "\n".join(error_details)
            raise RunbookValidationError(error_message) from e

        except Exception as e:
            if isinstance(e, RunbookLoadError | RunbookValidationError):
                raise
            raise RunbookLoadError(f"Failed to load runbook {runbook_path}: {e}") from e

    @staticmethod
    def _load_runbook_file(file_path: Path) -> dict[str, Any]:
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


class RunbookError(WCTError):
    """Base exception for generic runbook-related errors."""

    pass


class RunbookLoadError(RunbookError):
    """Raised when a runbook file cannot be loaded or parsed."""

    pass


class RunbookValidationError(RunbookError):
    """Raised when runbook configuration is structurally invalid."""

    pass
