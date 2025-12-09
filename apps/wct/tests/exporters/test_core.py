"""Tests for core export functionality."""

from unittest.mock import Mock

from waivern_orchestration import ExecutionPlan, ExecutionResult, Runbook


class TestBuildCoreExport:
    """Test suite for build_core_export()."""

    def test_returns_basic_export_structure(self) -> None:
        """Verifies all required top-level keys exist."""
        from wct.exporters.core import build_core_export

        # Arrange
        runbook = Runbook(name="Test", description="Test", artifacts={})
        plan = ExecutionPlan(runbook=runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={},
            skipped=set(),
            total_duration_seconds=0.0,
        )

        # Act
        export = build_core_export(result, plan)
        export_dict = export.model_dump(by_alias=True)

        # Assert - check dict representation (what users see in JSON)
        assert "format_version" in export_dict
        assert "run" in export_dict
        assert "runbook" in export_dict
        assert "summary" in export_dict
        assert "outputs" in export_dict
        assert "errors" in export_dict
        assert "skipped" in export_dict

    def test_format_version_is_2_0_0(self) -> None:
        """Verifies format_version field is 2.0.0."""
        from wct.exporters.core import build_core_export

        # Arrange
        runbook = Runbook(name="Test", description="Test", artifacts={})
        plan = ExecutionPlan(runbook=runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={},
            skipped=set(),
            total_duration_seconds=0.0,
        )

        # Act
        export = build_core_export(result, plan)

        # Assert
        assert export.format_version == "2.0.0"

    def test_run_id_is_valid_uuid(self) -> None:
        """Verifies run.id can be parsed as UUID."""
        from uuid import UUID

        from wct.exporters.core import build_core_export

        # Arrange
        runbook = Runbook(name="Test", description="Test", artifacts={})
        plan = ExecutionPlan(runbook=runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={},
            skipped=set(),
            total_duration_seconds=0.0,
        )

        # Act
        export = build_core_export(result, plan)

        # Assert - Can parse as UUID without error
        uuid_obj = UUID(export.run.id)
        assert str(uuid_obj) == export.run.id

    def test_timestamp_is_iso8601_with_timezone(self) -> None:
        """Verifies run.timestamp is ISO8601 format with timezone."""
        from datetime import datetime

        from wct.exporters.core import build_core_export

        # Arrange
        runbook = Runbook(name="Test", description="Test", artifacts={})
        plan = ExecutionPlan(runbook=runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={},
            skipped=set(),
            total_duration_seconds=0.0,
        )

        # Act
        export = build_core_export(result, plan)

        # Assert - can parse as ISO8601 with timezone
        timestamp = datetime.fromisoformat(export.run.timestamp)
        assert timestamp.tzinfo is not None

    def test_completed_status_when_all_succeed(self) -> None:
        """Status is completed when all artifacts succeed."""
        from waivern_orchestration import ArtifactResult

        from wct.exporters.core import build_core_export

        # Arrange
        runbook = Runbook(name="Test", description="Test", artifacts={})
        plan = ExecutionPlan(runbook=runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={
                "art1": ArtifactResult(
                    artifact_id="art1",
                    success=True,
                    duration_seconds=1.0,
                ),
                "art2": ArtifactResult(
                    artifact_id="art2",
                    success=True,
                    duration_seconds=2.0,
                ),
            },
            skipped=set(),
            total_duration_seconds=3.0,
        )

        # Act
        export = build_core_export(result, plan)

        # Assert - when all artifacts succeed, status should be "completed"
        assert export.run.status == "completed"

    def test_failed_status_when_any_fail(self) -> None:
        """Status is failed when any artifact fails."""
        from waivern_orchestration import ArtifactResult

        from wct.exporters.core import build_core_export

        # Arrange
        runbook = Runbook(name="Test", description="Test", artifacts={})
        plan = ExecutionPlan(runbook=runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={
                "art1": ArtifactResult(
                    artifact_id="art1",
                    success=True,
                    duration_seconds=1.0,
                ),
                "art2": ArtifactResult(
                    artifact_id="art2",
                    success=False,
                    error="Something went wrong",
                    duration_seconds=2.0,
                ),
            },
            skipped=set(),
            total_duration_seconds=3.0,
        )

        # Act
        export = build_core_export(result, plan)

        # Assert - when any artifact fails, status should be "failed"
        assert export.run.status == "failed"

    def test_partial_status_when_artifacts_skipped(self) -> None:
        """Status is partial when artifacts skipped but none failed."""
        from waivern_orchestration import ArtifactResult

        from wct.exporters.core import build_core_export

        # Arrange
        runbook = Runbook(name="Test", description="Test", artifacts={})
        plan = ExecutionPlan(runbook=runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={
                "art1": ArtifactResult(
                    artifact_id="art1",
                    success=True,
                    duration_seconds=1.0,
                ),
            },
            skipped={"art2", "art3"},
            total_duration_seconds=1.0,
        )

        # Act
        export = build_core_export(result, plan)

        # Assert - when artifacts are skipped but none failed, status should be "partial"
        assert export.run.status == "partial"

    def test_errors_list_contains_failed_artifacts(self) -> None:
        """Errors list includes artifact_id and error message for failures."""
        from waivern_orchestration import ArtifactResult

        from wct.exporters.core import build_core_export

        # Arrange
        runbook = Runbook(name="Test", description="Test", artifacts={})
        plan = ExecutionPlan(runbook=runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={
                "art1": ArtifactResult(
                    artifact_id="art1",
                    success=False,
                    error="Database connection failed",
                    duration_seconds=1.0,
                ),
                "art2": ArtifactResult(
                    artifact_id="art2",
                    success=False,
                    error="Timeout exceeded",
                    duration_seconds=2.0,
                ),
            },
            skipped=set(),
            total_duration_seconds=3.0,
        )

        # Act
        export = build_core_export(result, plan)

        # Assert - errors list should contain both failed artifacts
        assert len(export.errors) == 2
        error_ids = {err.artifact_id for err in export.errors}
        assert error_ids == {"art1", "art2"}
        # Check error messages are preserved
        art1_error = next(err for err in export.errors if err.artifact_id == "art1")
        assert art1_error.error == "Database connection failed"

    def test_skipped_list_contains_skipped_artifact_ids(self) -> None:
        """Skipped list contains IDs of skipped artifacts."""
        from waivern_orchestration import ArtifactResult

        from wct.exporters.core import build_core_export

        # Arrange
        runbook = Runbook(name="Test", description="Test", artifacts={})
        plan = ExecutionPlan(runbook=runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={
                "art1": ArtifactResult(
                    artifact_id="art1",
                    success=True,
                    duration_seconds=1.0,
                ),
            },
            skipped={"art2", "art3", "art4"},
            total_duration_seconds=1.0,
        )

        # Act
        export = build_core_export(result, plan)

        # Assert - skipped list should contain all skipped artifact IDs
        assert len(export.skipped) == 3
        assert set(export.skipped) == {"art2", "art3", "art4"}

    def test_summary_counts_are_accurate(self) -> None:
        """Summary total/succeeded/failed/skipped counts match reality."""
        from waivern_orchestration import ArtifactResult

        from wct.exporters.core import build_core_export

        # Arrange
        runbook = Runbook(name="Test", description="Test", artifacts={})
        plan = ExecutionPlan(runbook=runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={
                "success1": ArtifactResult(
                    artifact_id="success1",
                    success=True,
                    duration_seconds=1.0,
                ),
                "success2": ArtifactResult(
                    artifact_id="success2",
                    success=True,
                    duration_seconds=1.0,
                ),
                "failed1": ArtifactResult(
                    artifact_id="failed1",
                    success=False,
                    error="Error",
                    duration_seconds=1.0,
                ),
            },
            skipped={"skipped1", "skipped2"},
            total_duration_seconds=3.0,
        )

        # Act
        export = build_core_export(result, plan)

        # Assert - summary counts should be accurate
        assert export.summary.total == 5  # 3 artifacts + 2 skipped
        assert export.summary.succeeded == 2
        assert export.summary.failed == 1
        assert export.summary.skipped == 2

    def test_outputs_only_include_artifacts_with_output_true(self) -> None:
        """Only artifacts marked output:true appear in outputs list."""
        from waivern_core import Schema

        # Arrange
        from waivern_orchestration import (
            ArtifactDefinition,
            ArtifactResult,
            SourceConfig,
        )

        from wct.exporters.core import build_core_export

        artifacts = {
            "art1": ArtifactDefinition(
                source=SourceConfig(type="test", properties={}),
                output=True,  # Should be in outputs
            ),
            "art2": ArtifactDefinition(
                source=SourceConfig(type="test", properties={}),
                output=False,  # Should NOT be in outputs
            ),
            "art3": ArtifactDefinition(
                source=SourceConfig(type="test", properties={}),
                # output defaults to False - should NOT be in outputs
            ),
        }
        runbook = Runbook(name="Test", description="Test", artifacts=artifacts)
        schema = Schema("test_schema", "1.0.0")
        plan = ExecutionPlan(
            runbook=runbook,
            dag=Mock(),
            artifact_schemas={
                "art1": (None, schema),
                "art2": (None, schema),
                "art3": (None, schema),
            },
        )
        from waivern_core import Message

        message1 = Message(id="m1", content={"data": "test1"}, schema=schema)
        message2 = Message(id="m2", content={"data": "test2"}, schema=schema)
        message3 = Message(id="m3", content={"data": "test3"}, schema=schema)

        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={
                "art1": ArtifactResult(
                    artifact_id="art1",
                    success=True,
                    message=message1,
                    duration_seconds=1.0,
                ),
                "art2": ArtifactResult(
                    artifact_id="art2",
                    success=True,
                    message=message2,
                    duration_seconds=1.0,
                ),
                "art3": ArtifactResult(
                    artifact_id="art3",
                    success=True,
                    message=message3,
                    duration_seconds=1.0,
                ),
            },
            skipped=set(),
            total_duration_seconds=3.0,
        )

        # Act
        export = build_core_export(result, plan)

        # Assert - only art1 should be in outputs
        assert len(export.outputs) == 1
        assert export.outputs[0].artifact_id == "art1"

    def test_output_entry_includes_schema_info(self) -> None:
        """Output entries include schema name/version when available."""
        from waivern_core import Message, Schema
        from waivern_orchestration import (
            ArtifactDefinition,
            ArtifactResult,
            SourceConfig,
        )

        from wct.exporters.core import build_core_export

        # Arrange
        schema = Schema("my_schema", "2.1.0")
        artifacts = {
            "art1": ArtifactDefinition(
                source=SourceConfig(type="test", properties={}), output=True
            )
        }
        runbook = Runbook(name="Test", description="Test", artifacts=artifacts)
        plan = ExecutionPlan(
            runbook=runbook, dag=Mock(), artifact_schemas={"art1": (None, schema)}
        )

        message = Message(id="m1", content={"data": "test"}, schema=schema)
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={
                "art1": ArtifactResult(
                    artifact_id="art1",
                    success=True,
                    message=message,
                    duration_seconds=1.0,
                )
            },
            skipped=set(),
            total_duration_seconds=1.0,
        )

        # Act
        export = build_core_export(result, plan)

        # Assert - output entry should include schema info
        assert len(export.outputs) == 1
        assert export.outputs[0].output_schema is not None
        assert export.outputs[0].output_schema.name == "my_schema"
        assert export.outputs[0].output_schema.version == "2.1.0"

    def test_output_entry_includes_artifact_metadata(self) -> None:
        """Output entries include name/description/contact when present."""
        from waivern_core import Message, Schema
        from waivern_orchestration import (
            ArtifactDefinition,
            ArtifactResult,
            SourceConfig,
        )

        from wct.exporters.core import build_core_export

        # Arrange
        schema = Schema("test_schema", "1.0.0")
        artifacts = {
            "art1": ArtifactDefinition(
                source=SourceConfig(type="test", properties={}),
                name="Artifact One",
                description="First test artifact",
                contact="dev@example.com",
                output=True,
            )
        }
        runbook = Runbook(name="Test", description="Test", artifacts=artifacts)
        plan = ExecutionPlan(
            runbook=runbook, dag=Mock(), artifact_schemas={"art1": (None, schema)}
        )

        message = Message(id="m1", content={"data": "test"}, schema=schema)
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={
                "art1": ArtifactResult(
                    artifact_id="art1",
                    success=True,
                    message=message,
                    duration_seconds=1.0,
                )
            },
            skipped=set(),
            total_duration_seconds=1.0,
        )

        # Act
        export = build_core_export(result, plan)

        # Assert - output entry should include artifact metadata
        assert len(export.outputs) == 1
        assert export.outputs[0].name == "Artifact One"
        assert export.outputs[0].description == "First test artifact"
        assert export.outputs[0].contact == "dev@example.com"

    def test_runbook_contact_omitted_when_not_present(self) -> None:
        """Runbook.contact not in export when runbook has no contact."""
        from wct.exporters.core import build_core_export

        # Arrange
        runbook = Runbook(name="Test", description="Test", artifacts={}, contact=None)
        plan = ExecutionPlan(runbook=runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            artifacts={},
            skipped=set(),
            total_duration_seconds=0.0,
        )

        # Act
        export = build_core_export(result, plan)
        export_dict = export.model_dump(by_alias=True, exclude_none=True)

        # Assert - runbook.contact should not be in export when None
        assert "contact" not in export_dict["runbook"]
