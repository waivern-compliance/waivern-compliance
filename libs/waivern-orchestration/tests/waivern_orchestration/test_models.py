"""Tests for orchestration models."""

import pytest
from pydantic import ValidationError

from waivern_orchestration import (
    ArtifactDefinition,
    ArtifactResult,
    ComponentNotFoundError,
    CycleDetectedError,
    ExecuteConfig,
    ExecutionResult,
    MissingArtifactError,
    OrchestrationError,
    ProcessConfig,
    Runbook,
    RunbookConfig,
    RunbookParseError,
    SchemaCompatibilityError,
    SourceConfig,
)


class TestSourceArtifact:
    """Tests for source artifacts (connector-based)."""

    def test_source_artifact_valid(self) -> None:
        """Source artifact with source config should be valid."""
        artifact = ArtifactDefinition(
            source=SourceConfig(type="filesystem", properties={"path": "/tmp"})
        )
        assert artifact.source is not None
        assert artifact.source.type == "filesystem"
        assert artifact.inputs is None


class TestDerivedArtifact:
    """Tests for derived artifacts (processor-based)."""

    def test_derived_artifact_valid(self) -> None:
        """Derived artifact with inputs and process should be valid."""
        artifact = ArtifactDefinition(
            inputs="data_source",
            process=ProcessConfig(
                type="personal_data_analyser", properties={"ruleset": "personal_data"}
            ),
        )
        assert artifact.inputs == "data_source"
        assert artifact.process is not None
        assert artifact.process.type == "personal_data_analyser"
        assert artifact.source is None


class TestFanInArtifact:
    """Tests for fan-in artifacts (multiple inputs)."""

    def test_fan_in_artifact_valid(self) -> None:
        """Fan-in artifact with multiple inputs should be valid."""
        artifact = ArtifactDefinition(
            inputs=["source_a", "source_b"],
            process=ProcessConfig(type="merger", properties={}),
            merge="concatenate",
        )
        assert artifact.inputs == ["source_a", "source_b"]
        assert artifact.merge == "concatenate"

    def test_merge_defaults_to_concatenate(self) -> None:
        """Merge strategy should default to 'concatenate'."""
        artifact = ArtifactDefinition(
            inputs=["source_a", "source_b"],
            process=ProcessConfig(type="merger", properties={}),
        )
        assert artifact.merge == "concatenate"


class TestArtifactValidation:
    """Tests for artifact validation rules."""

    def test_source_xor_inputs_both_set_fails(self) -> None:
        """Setting both source and inputs should raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={}),
                inputs="other_artifact",
            )
        assert (
            "source" in str(exc_info.value).lower()
            or "inputs" in str(exc_info.value).lower()
        )

    def test_source_xor_inputs_neither_set_fails(self) -> None:
        """Setting neither source nor inputs should raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactDefinition()
        assert (
            "source" in str(exc_info.value).lower()
            or "inputs" in str(exc_info.value).lower()
        )


class TestRunbookConfig:
    """Tests for runbook configuration defaults."""

    def test_runbook_config_defaults(self) -> None:
        """RunbookConfig should have sensible defaults."""
        config = RunbookConfig()
        assert config.timeout == 300  # 5 minutes default
        assert config.max_concurrency == 10
        assert config.cost_limit is None  # No limit by default

    def test_runbook_config_max_child_depth_default(self) -> None:
        """RunbookConfig should default max_child_depth to 3."""
        config = RunbookConfig()
        assert config.max_child_depth == 3


class TestExecuteConfig:
    """Tests for execute configuration (Phase 2)."""

    def test_execute_config_valid(self) -> None:
        """ExecuteConfig should accept valid child mode configuration."""
        config = ExecuteConfig(mode="child", timeout=60, cost_limit=1.5)
        assert config.mode == "child"
        assert config.timeout == 60
        assert config.cost_limit == 1.5


class TestArtifactMetadata:
    """Tests for artifact metadata fields."""

    def test_artifact_metadata_fields(self) -> None:
        """Artifact should accept optional name, description, contact fields."""
        artifact = ArtifactDefinition(
            name="User Data",
            description="Extracts user data from database",
            contact="team@example.com",
            source=SourceConfig(type="mysql", properties={}),
        )
        assert artifact.name == "User Data"
        assert artifact.description == "Extracts user data from database"
        assert artifact.contact == "team@example.com"

    def test_artifact_schema_override_fields(self) -> None:
        """Artifact should accept optional output_schema field."""
        artifact = ArtifactDefinition(
            inputs="source_data",
            process=ProcessConfig(type="analyser", properties={}),
            output_schema="custom_output/1.0.0",
        )
        assert artifact.output_schema == "custom_output/1.0.0"

    def test_artifact_optional_field(self) -> None:
        """Artifact should accept optional field to mark non-critical artifacts."""
        artifact = ArtifactDefinition(
            inputs="source_data",
            process=ProcessConfig(type="analyser", properties={}),
            optional=True,
        )
        assert artifact.optional is True

        # Default should be False
        artifact_default = ArtifactDefinition(
            inputs="source_data",
            process=ProcessConfig(type="analyser", properties={}),
        )
        assert artifact_default.optional is False

    def test_artifact_execute_field(self) -> None:
        """Artifact should accept execute field for child runbook execution."""
        artifact = ArtifactDefinition(
            inputs="source_data",
            execute=ExecuteConfig(mode="child", timeout=120),
        )
        assert artifact.execute is not None
        assert artifact.execute.mode == "child"
        assert artifact.execute.timeout == 120


class TestRunbook:
    """Tests for the Runbook model."""

    def test_runbook_serialisation_preserves_data(self) -> None:
        """Runbook should serialise to dict and deserialise back correctly."""
        runbook = Runbook(
            name="Test Runbook",
            description="A test runbook",
            artifacts={
                "data": ArtifactDefinition(
                    source=SourceConfig(type="filesystem", properties={"path": "/tmp"})
                ),
                "findings": ArtifactDefinition(
                    inputs="data",
                    process=ProcessConfig(type="analyser", properties={}),
                    output=True,
                ),
            },
        )
        # Serialise to dict
        data = runbook.model_dump(by_alias=True)
        # Deserialise from dict
        restored = Runbook.model_validate(data)
        assert restored.name == runbook.name
        assert restored.description == runbook.description
        assert len(restored.artifacts) == 2
        assert "data" in restored.artifacts
        assert "findings" in restored.artifacts

    def test_runbook_contact_field(self) -> None:
        """Runbook should accept optional contact field."""
        runbook = Runbook(
            name="Test",
            description="Test runbook",
            contact="team@example.com",
            artifacts={
                "data": ArtifactDefinition(
                    source=SourceConfig(type="filesystem", properties={})
                )
            },
        )
        assert runbook.contact == "team@example.com"

    def test_runbook_config_field_default(self) -> None:
        """Runbook should have config field with RunbookConfig default."""
        runbook = Runbook(
            name="Test",
            description="Test runbook",
            artifacts={},
        )
        assert runbook.config is not None
        assert runbook.config.timeout == 300
        assert runbook.config.max_concurrency == 10
        assert runbook.config.max_child_depth == 3


class TestArtifactResult:
    """Tests for artifact execution result."""

    def test_artifact_result_fields(self) -> None:
        """ArtifactResult should have all required fields."""
        result = ArtifactResult(
            artifact_id="data_source",
            success=True,
            message=None,
            error=None,
            duration_seconds=1.5,
        )
        assert result.artifact_id == "data_source"
        assert result.success is True
        assert result.message is None
        assert result.error is None
        assert result.duration_seconds == 1.5


class TestExecutionResult:
    """Tests for runbook execution result."""

    def test_execution_result_fields(self) -> None:
        """ExecutionResult should have all required fields."""
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={
                "data": ArtifactResult(
                    artifact_id="data",
                    success=True,
                    duration_seconds=1.0,
                )
            },
            skipped={"optional_step"},
            total_duration_seconds=5.5,
        )
        assert result.run_id == "123e4567-e89b-12d3-a456-426614174000"
        assert result.start_timestamp == "2024-01-15T10:30:00+00:00"
        assert "data" in result.artifacts
        assert result.artifacts["data"].success is True
        assert "optional_step" in result.skipped
        assert result.total_duration_seconds == 5.5


class TestErrorHierarchy:
    """Tests for error class hierarchy."""

    def test_error_inheritance(self) -> None:
        """All orchestration errors should inherit from OrchestrationError."""
        error_classes = [
            RunbookParseError,
            CycleDetectedError,
            MissingArtifactError,
            SchemaCompatibilityError,
            ComponentNotFoundError,
        ]
        for error_class in error_classes:
            assert issubclass(error_class, OrchestrationError)
            assert issubclass(error_class, Exception)
