"""Tests for orchestration models."""

import pytest
from pydantic import ValidationError

from waivern_orchestration import (
    ArtifactDefinition,
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

from .test_helpers import create_message_with_execution

# =============================================================================
# Artifact Definition Tests
# =============================================================================


class TestArtifactDefinitionTypes:
    """Tests for different artifact types (source, derived, fan-in)."""

    def test_source_artifact_valid(self) -> None:
        """Source artifact with source config should be valid."""
        artifact = ArtifactDefinition(
            source=SourceConfig(type="filesystem", properties={"path": "/tmp"})
        )
        assert artifact.source is not None
        assert artifact.source.type == "filesystem"
        assert artifact.inputs is None

    def test_derived_artifact_valid(self) -> None:
        """Derived artifact with inputs and process should be valid."""
        artifact = ArtifactDefinition(
            inputs="data_source",
            process=ProcessConfig(
                type="personal_data_analyser",
                properties={"ruleset": "local/personal_data/1.0.0"},
            ),
        )
        assert artifact.inputs == "data_source"
        assert artifact.process is not None
        assert artifact.process.type == "personal_data_analyser"
        assert artifact.source is None

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


class TestArtifactDefinitionValidation:
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


# =============================================================================
# Configuration Model Tests
# =============================================================================


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


class TestArtifactDefinitionMetadata:
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


# =============================================================================
# Runbook Model Tests
# =============================================================================


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


# =============================================================================
# Execution Result Tests
# =============================================================================


class TestExecutionResult:
    """Tests for runbook execution result."""

    def test_execution_result_fields(self) -> None:
        """ExecutionResult should have all required fields."""
        test_message = create_message_with_execution(
            content={"data": "test"},
            status="success",
            duration=1.0,
        )
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={"data": test_message},
            skipped={"optional_step"},
            total_duration_seconds=5.5,
        )
        assert result.run_id == "123e4567-e89b-12d3-a456-426614174000"
        assert result.start_timestamp == "2024-01-15T10:30:00+00:00"
        assert "data" in result.artifacts
        assert result.artifacts["data"].extensions is not None
        assert result.artifacts["data"].extensions.execution is not None
        assert result.artifacts["data"].extensions.execution.status == "success"
        assert "optional_step" in result.skipped
        assert result.total_duration_seconds == 5.5


# =============================================================================
# Error Hierarchy Tests
# =============================================================================


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


# =============================================================================
# Child Runbooks - New Model Tests
# =============================================================================


class TestRunbookInputDeclaration:
    """Tests for RunbookInputDeclaration model (child runbook inputs)."""

    def test_runbook_input_declaration_required_fields(self) -> None:
        """RunbookInputDeclaration requires input_schema field."""
        from waivern_orchestration.models import RunbookInputDeclaration

        # Should fail without input_schema
        with pytest.raises(ValidationError) as exc_info:
            # Intentionally omit required parameter to test validation
            RunbookInputDeclaration()  # type: ignore[call-arg]
        assert "input_schema" in str(exc_info.value).lower()

        # Should succeed with input_schema
        declaration = RunbookInputDeclaration(input_schema="standard_input/1.0.0")
        assert declaration.input_schema == "standard_input/1.0.0"

    def test_runbook_input_declaration_defaults(self) -> None:
        """RunbookInputDeclaration has sensible defaults for optional fields."""
        from waivern_orchestration.models import RunbookInputDeclaration

        declaration = RunbookInputDeclaration(input_schema="standard_input/1.0.0")

        # Check defaults
        assert declaration.optional is False
        assert declaration.default is None
        assert declaration.sensitive is False
        assert declaration.description is None

    def test_runbook_input_declaration_default_requires_optional(self) -> None:
        """Setting default value requires optional=True."""
        from waivern_orchestration.models import RunbookInputDeclaration

        # Setting default without optional=True should fail
        with pytest.raises(ValidationError) as exc_info:
            RunbookInputDeclaration(
                input_schema="standard_input/1.0.0",
                default={"some": "value"},
            )
        assert "default" in str(exc_info.value).lower()
        assert "optional" in str(exc_info.value).lower()

        # Setting default with optional=True should succeed
        declaration = RunbookInputDeclaration(
            input_schema="standard_input/1.0.0",
            optional=True,
            default={"some": "value"},
        )
        assert declaration.default == {"some": "value"}


class TestRunbookOutputDeclaration:
    """Tests for RunbookOutputDeclaration model (child runbook outputs)."""

    def test_runbook_output_declaration_required_fields(self) -> None:
        """RunbookOutputDeclaration requires artifact field."""
        from waivern_orchestration.models import RunbookOutputDeclaration

        # Should fail without artifact
        with pytest.raises(ValidationError) as exc_info:
            # Intentionally omit required parameter to test validation
            RunbookOutputDeclaration()  # type: ignore[call-arg]
        assert "artifact" in str(exc_info.value).lower()

        # Should succeed with artifact
        declaration = RunbookOutputDeclaration(artifact="findings")
        assert declaration.artifact == "findings"

    def test_runbook_output_declaration_defaults(self) -> None:
        """RunbookOutputDeclaration has sensible defaults."""
        from waivern_orchestration.models import RunbookOutputDeclaration

        declaration = RunbookOutputDeclaration(artifact="findings")
        assert declaration.description is None


class TestChildRunbookConfig:
    """Tests for ChildRunbookConfig model (child runbook directive)."""

    def test_child_runbook_config_required_fields(self) -> None:
        """ChildRunbookConfig requires path and input_mapping."""
        from waivern_orchestration.models import ChildRunbookConfig

        # Should fail without path
        with pytest.raises(ValidationError) as exc_info:
            # Intentionally omit required parameters to test validation
            ChildRunbookConfig(  # type: ignore[call-arg]
                input_mapping={"source_data": "db_schema"},
                output="findings",
            )
        assert "path" in str(exc_info.value).lower()

        # Should fail without input_mapping
        with pytest.raises(ValidationError) as exc_info:
            ChildRunbookConfig(  # type: ignore[call-arg]
                path="./child.yaml",
                output="findings",
            )
        assert "input_mapping" in str(exc_info.value).lower()

    def test_child_runbook_config_output_xor_output_mapping(self) -> None:
        """Cannot specify both output and output_mapping."""
        from waivern_orchestration.models import ChildRunbookConfig

        with pytest.raises(ValidationError) as exc_info:
            ChildRunbookConfig(
                path="./child.yaml",
                input_mapping={"source_data": "db_schema"},
                output="findings",
                output_mapping={"findings": "child_findings"},
            )
        assert "output" in str(exc_info.value).lower()

    def test_child_runbook_config_output_required(self) -> None:
        """Must specify either output or output_mapping."""
        from waivern_orchestration.models import ChildRunbookConfig

        with pytest.raises(ValidationError) as exc_info:
            ChildRunbookConfig(
                path="./child.yaml",
                input_mapping={"source_data": "db_schema"},
            )
        assert "output" in str(exc_info.value).lower()

    def test_child_runbook_config_single_output(self) -> None:
        """ChildRunbookConfig accepts single output configuration."""
        from waivern_orchestration.models import ChildRunbookConfig

        config = ChildRunbookConfig(
            path="./child.yaml",
            input_mapping={"source_data": "db_schema"},
            output="findings",
        )
        assert config.path == "./child.yaml"
        assert config.input_mapping == {"source_data": "db_schema"}
        assert config.output == "findings"
        assert config.output_mapping is None

    def test_child_runbook_config_multiple_outputs(self) -> None:
        """ChildRunbookConfig accepts output_mapping for multiple outputs."""
        from waivern_orchestration.models import ChildRunbookConfig

        config = ChildRunbookConfig(
            path="./child.yaml",
            input_mapping={"source_data": "db_schema"},
            output_mapping={
                "findings": "child_findings",
                "summary": "child_summary",
            },
        )
        assert config.output is None
        assert config.output_mapping == {
            "findings": "child_findings",
            "summary": "child_summary",
        }


class TestRunbookConfigTemplatePaths:
    """Tests for template_paths in RunbookConfig."""

    def test_runbook_config_template_paths_default(self) -> None:
        """template_paths defaults to empty list."""
        config = RunbookConfig()
        assert config.template_paths == []

    def test_runbook_config_template_paths_accepts_list(self) -> None:
        """template_paths accepts list of path strings."""
        config = RunbookConfig(
            template_paths=["./templates", "./shared/runbooks"],
        )
        assert config.template_paths == ["./templates", "./shared/runbooks"]


class TestRunbookInputsOutputs:
    """Tests for inputs and outputs fields on Runbook model."""

    def test_runbook_inputs_field(self) -> None:
        """Runbook accepts inputs dict of RunbookInputDeclaration."""
        from waivern_orchestration.models import RunbookInputDeclaration

        runbook = Runbook(
            name="Child Runbook",
            description="A child runbook with inputs",
            inputs={
                "source_data": RunbookInputDeclaration(
                    input_schema="standard_input/1.0.0",
                ),
            },
            artifacts={
                "findings": ArtifactDefinition(
                    inputs="source_data",
                    process=ProcessConfig(type="analyser", properties={}),
                ),
            },
        )
        assert runbook.inputs is not None
        assert "source_data" in runbook.inputs
        assert runbook.inputs["source_data"].input_schema == "standard_input/1.0.0"

    def test_runbook_outputs_field(self) -> None:
        """Runbook accepts outputs dict of RunbookOutputDeclaration."""
        from waivern_orchestration.models import (
            RunbookInputDeclaration,
            RunbookOutputDeclaration,
        )

        runbook = Runbook(
            name="Child Runbook",
            description="A child runbook with outputs",
            inputs={
                "source_data": RunbookInputDeclaration(
                    input_schema="standard_input/1.0.0",
                ),
            },
            outputs={
                "findings": RunbookOutputDeclaration(artifact="analysis_findings"),
            },
            artifacts={
                "analysis_findings": ArtifactDefinition(
                    inputs="source_data",
                    process=ProcessConfig(type="analyser", properties={}),
                ),
            },
        )
        assert runbook.outputs is not None
        assert "findings" in runbook.outputs
        assert runbook.outputs["findings"].artifact == "analysis_findings"

    def test_runbook_with_inputs_cannot_have_source_artifacts(self) -> None:
        """Runbook with inputs section cannot have source artifacts."""
        from waivern_orchestration.models import RunbookInputDeclaration

        with pytest.raises(ValidationError) as exc_info:
            Runbook(
                name="Invalid Child Runbook",
                description="Has both inputs and source",
                inputs={
                    "source_data": RunbookInputDeclaration(
                        input_schema="standard_input/1.0.0",
                    ),
                },
                artifacts={
                    "db_data": ArtifactDefinition(
                        source=SourceConfig(type="mysql", properties={}),
                    ),
                },
            )
        assert "source" in str(exc_info.value).lower()

    def test_runbook_outputs_must_reference_existing_artifacts(self) -> None:
        """Runbook outputs must reference existing artifacts."""
        from waivern_orchestration.models import (
            RunbookInputDeclaration,
            RunbookOutputDeclaration,
        )

        with pytest.raises(ValidationError) as exc_info:
            Runbook(
                name="Invalid Child Runbook",
                description="Output references non-existent artifact",
                inputs={
                    "source_data": RunbookInputDeclaration(
                        input_schema="standard_input/1.0.0",
                    ),
                },
                outputs={
                    "findings": RunbookOutputDeclaration(artifact="non_existent"),
                },
                artifacts={
                    "analysis_findings": ArtifactDefinition(
                        inputs="source_data",
                        process=ProcessConfig(type="analyser", properties={}),
                    ),
                },
            )
        assert "non_existent" in str(exc_info.value).lower()


class TestArtifactChildRunbook:
    """Tests for child_runbook field on ArtifactDefinition."""

    def test_artifact_child_runbook_field(self) -> None:
        """ArtifactDefinition accepts child_runbook field."""
        from waivern_orchestration.models import ChildRunbookConfig

        artifact = ArtifactDefinition(
            inputs="source_data",
            child_runbook=ChildRunbookConfig(
                path="./child.yaml",
                input_mapping={"source_data": "source_data"},
                output="findings",
            ),
        )
        assert artifact.child_runbook is not None
        assert artifact.child_runbook.path == "./child.yaml"

    def test_artifact_child_runbook_cannot_have_process(self) -> None:
        """Artifact with child_runbook cannot have process."""
        from waivern_orchestration.models import ChildRunbookConfig

        with pytest.raises(ValidationError) as exc_info:
            ArtifactDefinition(
                inputs="source_data",
                process=ProcessConfig(type="analyser", properties={}),
                child_runbook=ChildRunbookConfig(
                    path="./child.yaml",
                    input_mapping={"source_data": "source_data"},
                    output="findings",
                ),
            )
        assert "child_runbook" in str(exc_info.value).lower()

    def test_artifact_child_runbook_requires_inputs(self) -> None:
        """Artifact with child_runbook requires inputs."""
        from waivern_orchestration.models import ChildRunbookConfig

        with pytest.raises(ValidationError) as exc_info:
            ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={}),
                child_runbook=ChildRunbookConfig(
                    path="./child.yaml",
                    input_mapping={"source_data": "source_data"},
                    output="findings",
                ),
            )
        # Will fail on child_runbook requiring inputs (source artifacts don't have inputs)
        error_msg = str(exc_info.value).lower()
        assert "child_runbook" in error_msg or "inputs" in error_msg

    def test_artifact_child_runbook_valid_configuration(self) -> None:
        """Valid child_runbook artifact configuration works."""
        from waivern_orchestration.models import ChildRunbookConfig

        artifact = ArtifactDefinition(
            inputs=["source_a", "source_b"],
            child_runbook=ChildRunbookConfig(
                path="./comprehensive.yaml",
                input_mapping={
                    "data_a": "source_a",
                    "data_b": "source_b",
                },
                output_mapping={
                    "findings": "child_findings",
                    "summary": "child_summary",
                },
            ),
        )
        assert artifact.child_runbook is not None
        assert artifact.source is None
        assert artifact.process is None
        assert artifact.inputs == ["source_a", "source_b"]


# =============================================================================
# Runbook Framework Field Tests
# =============================================================================


class TestRunbookFramework:
    """Tests for the framework field on Runbook model."""

    def test_framework_field_is_optional(self) -> None:
        """Framework field should be optional and default to None."""
        runbook = Runbook(
            name="Test Runbook",
            description="A test runbook",
            artifacts={
                "data": ArtifactDefinition(
                    source=SourceConfig(type="filesystem", properties={"path": "/tmp"})
                )
            },
        )
        assert runbook.framework is None

    def test_framework_serialisation_preserves_value(self) -> None:
        """Framework field should be preserved in serialisation."""
        runbook = Runbook(
            name="GDPR Runbook",
            description="A GDPR compliance runbook",
            framework="GDPR",
            artifacts={
                "data": ArtifactDefinition(
                    source=SourceConfig(type="filesystem", properties={"path": "/tmp"})
                )
            },
        )
        data = runbook.model_dump(by_alias=True)
        restored = Runbook.model_validate(data)
        assert restored.framework == "GDPR"


class TestNewErrorTypes:
    """Tests for new error types for child runbooks."""

    def test_error_hierarchy_includes_new_errors(self) -> None:
        """New child runbook errors inherit from OrchestrationError."""
        from waivern_orchestration.errors import (
            ChildRunbookNotFoundError,
            CircularRunbookError,
            InvalidOutputMappingError,
            InvalidPathError,
            MissingInputMappingError,
            OrchestrationError,
        )

        error_classes = [
            InvalidPathError,
            ChildRunbookNotFoundError,
            CircularRunbookError,
            MissingInputMappingError,
            InvalidOutputMappingError,
        ]
        for error_class in error_classes:
            assert issubclass(error_class, OrchestrationError)
            assert issubclass(error_class, Exception)
