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
    template_paths: list[str] = Field(default_factory=list)
    """Directories to search for child runbooks."""


class RunbookInputDeclaration(BaseModel):
    """Declaration of an expected input for a child runbook."""

    input_schema: str
    """Schema identifier (e.g., 'standard_input/1.0.0')."""

    optional: bool = False
    """If true, input doesn't need to be mapped."""

    default: Any = None
    """Default value if not mapped (requires optional=True)."""

    sensitive: bool = False
    """If true, value is redacted from logs and execution results."""

    description: str | None = None
    """Human-readable description."""

    @model_validator(mode="after")
    def validate_default_requires_optional(self) -> Self:
        """Validate that default value requires optional=True."""
        if self.default is not None and not self.optional:
            raise ValueError("'default' requires 'optional: true'")
        return self


class RunbookOutputDeclaration(BaseModel):
    """Declaration of an output that a child runbook exposes."""

    artifact: str
    """Reference to an artifact in this runbook."""

    description: str | None = None
    """Human-readable description."""


class ChildRunbookConfig(BaseModel):
    """Configuration for child runbook directive."""

    path: str
    """Relative path to child runbook file."""

    input_mapping: dict[str, str]
    """Maps child input names to parent artifact IDs."""

    output: str | None = None
    """Single output artifact from child (mutually exclusive with output_mapping)."""

    output_mapping: dict[str, str] | None = None
    """Multiple outputs: {child_artifact: parent_artifact_name}."""

    @model_validator(mode="after")
    def validate_output_config(self) -> Self:
        """Validate that exactly one of output or output_mapping is set."""
        if self.output is None and self.output_mapping is None:
            raise ValueError("Either 'output' or 'output_mapping' required")
        if self.output is not None and self.output_mapping is not None:
            raise ValueError("Cannot specify both 'output' and 'output_mapping'")
        return self


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

    # Phase 3: child runbook composition
    child_runbook: ChildRunbookConfig | None = None
    """Child runbook directive for composition."""

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

    @model_validator(mode="after")
    def validate_child_runbook_constraints(self) -> Self:
        """Validate child_runbook constraints."""
        if self.child_runbook is not None:
            if self.process is not None:
                raise ValueError("Cannot combine 'child_runbook' with 'process'")
            if self.inputs is None:
                raise ValueError("'child_runbook' requires 'inputs'")
        return self


class Runbook(BaseModel):
    """Top-level runbook model."""

    name: str
    description: str
    contact: str | None = None
    config: RunbookConfig = Field(default_factory=RunbookConfig)

    inputs: dict[str, RunbookInputDeclaration] | None = None
    """Declared inputs (makes this a child runbook)."""

    outputs: dict[str, RunbookOutputDeclaration] | None = None
    """Declared outputs (what this runbook exposes)."""

    artifacts: dict[str, ArtifactDefinition] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_child_runbook_constraints(self) -> Self:
        """Validate that runbooks with inputs cannot have source artifacts."""
        if self.inputs:
            for artifact_id, artifact in self.artifacts.items():
                if artifact.source is not None:
                    raise ValueError(
                        f"Runbook with inputs cannot have source artifacts. "
                        f"Found source in '{artifact_id}'."
                    )
        return self

    @model_validator(mode="after")
    def validate_outputs_reference_artifacts(self) -> Self:
        """Validate that outputs reference existing artifacts."""
        if self.outputs:
            for output_name, output_decl in self.outputs.items():
                if output_decl.artifact not in self.artifacts:
                    raise ValueError(
                        f"Output '{output_name}' references non-existent "
                        f"artifact '{output_decl.artifact}'."
                    )
        return self


class ArtifactResult(BaseModel):
    """Result of executing a single artifact."""

    artifact_id: str
    success: bool
    message: Message | None = None
    error: str | None = None
    duration_seconds: float

    # Phase 3: child runbook tracking
    origin: str = "parent"
    """Origin of artifact: 'parent' or 'child:{runbook_name}'."""

    alias: str | None = None
    """Parent artifact name if this is an aliased child artifact."""


class ExecutionResult(BaseModel):
    """Result of executing a complete runbook."""

    run_id: str = Field(..., description="Unique run identifier (UUID)")
    start_timestamp: str = Field(..., description="ISO8601 timestamp with timezone")
    artifacts: dict[str, ArtifactResult] = Field(default_factory=dict)
    skipped: set[str] = Field(default_factory=set)
    total_duration_seconds: float
