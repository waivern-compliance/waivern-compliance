"""Pydantic models for artifact-centric runbook orchestration."""

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator
from waivern_core import Message


class SourceConfig(BaseModel):
    """Configuration for a source artifact (connector)."""

    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class ProcessConfig(BaseModel):
    """Configuration for a processor (analyser, orchestrator, etc.)."""

    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class ExecuteConfig(BaseModel):
    """Configuration for child runbook execution (Phase 2)."""

    mode: Literal["child"]
    timeout: int | None = None
    cost_limit: float | None = None


class RunbookConfig(BaseModel):
    """Optional execution configuration for a runbook."""

    timeout: int = 300
    max_concurrency: int = 10
    max_child_depth: int = 3
    cost_limit: float | None = None


class ArtifactDefinition(BaseModel):
    """Definition of a single artifact in a runbook."""

    # Metadata (optional)
    name: str | None = None
    description: str | None = None
    contact: str | None = None

    # Source: exactly one of source or inputs must be set
    source: SourceConfig | None = None
    inputs: str | list[str] | None = None
    process: ProcessConfig | None = None
    merge: Literal["concatenate"] = "concatenate"

    # Schema override (optional)
    output_schema: str | None = None

    # Behaviour
    output: bool = False
    optional: bool = False

    # Phase 2: child runbook execution
    execute: ExecuteConfig | None = None

    @model_validator(mode="after")
    def validate_source_xor_inputs(self) -> Self:
        """Validate that exactly one of source or inputs is set."""
        has_source = self.source is not None
        has_inputs = self.inputs is not None

        if has_source and has_inputs:
            raise ValueError(
                "Artifact cannot have both 'source' and 'inputs' - "
                "they are mutually exclusive"
            )
        if not has_source and not has_inputs:
            raise ValueError("Artifact must have either 'source' or 'inputs' defined")

        return self


class Runbook(BaseModel):
    """Top-level runbook model."""

    name: str
    description: str
    contact: str | None = None
    config: RunbookConfig = Field(default_factory=RunbookConfig)
    artifacts: dict[str, ArtifactDefinition] = Field(default_factory=dict)


class ArtifactResult(BaseModel):
    """Result of executing a single artifact."""

    artifact_id: str
    success: bool
    message: Message | None = None
    error: str | None = None
    duration_seconds: float


class ExecutionResult(BaseModel):
    """Result of executing a complete runbook."""

    run_id: str = Field(..., description="Unique run identifier (UUID)")
    start_timestamp: str = Field(..., description="ISO8601 timestamp with timezone")
    artifacts: dict[str, ArtifactResult] = Field(default_factory=dict)
    skipped: set[str] = Field(default_factory=set)
    total_duration_seconds: float
