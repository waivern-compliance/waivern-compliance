"""Pydantic models for artifact-centric runbook orchestration."""

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator
from waivern_core import JsonValue

# =============================================================================
# Artifact Configuration
# =============================================================================


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


class ReuseConfig(BaseModel):
    """Configuration for reusing an artifact from a previous run.

    Allows copying an artifact's output from a completed run instead of
    re-executing the production logic. Useful for resuming workflows or
    reusing expensive computations.

    Attributes:
        from_run: The run ID to copy the artifact from.
        artifact: The artifact ID in the source run to copy.

    """

    from_run: str
    artifact: str


# =============================================================================
# Runbook Configuration
# =============================================================================


class RunbookConfig(BaseModel):
    """Optional execution configuration for a runbook."""

    timeout: int = 300
    max_concurrency: int = 10
    max_child_depth: int = 3
    cost_limit: float | None = None
    template_paths: list[str] = Field(default_factory=list)
    """Directories to search for child runbooks."""


# =============================================================================
# Child Runbook Support
# =============================================================================


class RunbookInputDeclaration(BaseModel):
    """Declaration of an expected input for a child runbook."""

    input_schema: str
    """Schema identifier (e.g., 'standard_input/1.0.0')."""

    optional: bool = False
    """If true, input doesn't need to be mapped."""

    default: JsonValue = None
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


# =============================================================================
# Core Models
# =============================================================================


class ArtifactDefinition(BaseModel):
    """Definition of a single artifact in a runbook.

    An artifact has exactly one production method:
    - `source`: Extract data from a connector
    - `inputs` + `process`: Transform data from other artifacts
    - `reuse`: Copy from a previous run

    """

    # Metadata (optional)
    name: str | None = None
    description: str | None = None
    contact: str | None = None

    # Production methods (mutually exclusive)
    source: SourceConfig | None = None
    inputs: str | list[str] | None = None
    process: ProcessConfig | None = None
    reuse: ReuseConfig | None = None
    """Reuse artifact from a previous run instead of re-executing."""

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
    def validate_production_method(self) -> Self:
        """Validate that exactly one production method is specified.

        Production methods are mutually exclusive:
        - `reuse`: Copy from previous run (standalone)
        - `source`: Extract from connector (standalone)
        - `inputs`: Transform with processor (requires inputs)

        """
        has_reuse = self.reuse is not None
        has_source = self.source is not None
        has_inputs = self.inputs is not None

        # Reuse is a standalone production method
        if has_reuse:
            if has_source:
                raise ValueError(
                    "Artifact cannot have both 'reuse' and 'source' - "
                    "they are mutually exclusive"
                )
            if has_inputs:
                raise ValueError(
                    "Artifact cannot have both 'reuse' and 'inputs' - "
                    "they are mutually exclusive"
                )
            return self

        # Without reuse, exactly one of source or inputs must be set
        if has_source and has_inputs:
            raise ValueError(
                "Artifact cannot have both 'source' and 'inputs' - "
                "they are mutually exclusive"
            )
        if not has_source and not has_inputs:
            raise ValueError(
                "Artifact must have 'source', 'inputs', or 'reuse' defined"
            )

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
    framework: str | None = None
    """Regulatory framework this runbook targets (e.g., 'GDPR', 'CCPA')."""
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


# =============================================================================
# Execution Results
# =============================================================================


class ExecutionResult(BaseModel):
    """Result of executing a complete runbook.

    This is a summary of the execution outcome. Artifact data is stored in the
    ArtifactStore and can be loaded using the run_id.

    Attributes:
        run_id: Unique identifier for this run, used to retrieve artifacts from store.
        start_timestamp: ISO8601 timestamp when execution started.
        completed: Artifact IDs that completed successfully.
        failed: Artifact IDs that failed during execution.
        skipped: Artifact IDs skipped due to upstream failures or timeout.
        total_duration_seconds: Total execution time.

    """

    run_id: str = Field(..., description="Unique run identifier (UUID)")
    start_timestamp: str = Field(..., description="ISO8601 timestamp with timezone")
    completed: set[str] = Field(default_factory=set)
    """Artifact IDs that completed successfully."""
    failed: set[str] = Field(default_factory=set)
    """Artifact IDs that failed during execution."""
    skipped: set[str] = Field(default_factory=set)
    """Artifact IDs skipped due to upstream failures or timeout."""
    total_duration_seconds: float
