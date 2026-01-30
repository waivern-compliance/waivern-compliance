"""Tests for core export functionality."""

from unittest.mock import Mock

from waivern_artifact_store.in_memory import AsyncInMemoryStore
from waivern_core import Schema
from waivern_orchestration import ExecutionPlan, ExecutionResult, Runbook

from .conftest import create_error_message, create_success_message

# =============================================================================
# Basic Export Structure
# =============================================================================


class TestBuildCoreExport:
    """Test suite for build_core_export()."""

    async def test_returns_basic_export_structure(
        self, empty_plan: ExecutionPlan, empty_result: ExecutionResult
    ) -> None:
        """Verifies all required top-level keys exist."""
        from wct.exporters.core import build_core_export

        store = AsyncInMemoryStore()
        export = await build_core_export(empty_result, empty_plan, store)
        export_dict = export.model_dump(by_alias=True)

        assert "format_version" in export_dict
        assert "run" in export_dict
        assert "runbook" in export_dict
        assert "summary" in export_dict
        assert "outputs" in export_dict
        assert "errors" in export_dict
        assert "skipped" in export_dict

    async def test_format_version_is_2_0_0(
        self, empty_plan: ExecutionPlan, empty_result: ExecutionResult
    ) -> None:
        """Verifies format_version field is 2.0.0."""
        from wct.exporters.core import build_core_export

        store = AsyncInMemoryStore()
        export = await build_core_export(empty_result, empty_plan, store)

        assert export.format_version == "2.0.0"


# =============================================================================
# Run Metadata - ID and Timestamp
# =============================================================================


class TestBuildCoreExportRunMetadata:
    """Tests for run metadata (ID, timestamp) in exports."""

    async def test_run_id_is_valid_uuid(
        self, empty_plan: ExecutionPlan, empty_result: ExecutionResult
    ) -> None:
        """Verifies run.id can be parsed as UUID."""
        from uuid import UUID

        from wct.exporters.core import build_core_export

        store = AsyncInMemoryStore()
        export = await build_core_export(empty_result, empty_plan, store)

        uuid_obj = UUID(export.run.id)
        assert str(uuid_obj) == export.run.id

    async def test_timestamp_is_iso8601_with_timezone(
        self, empty_plan: ExecutionPlan, empty_result: ExecutionResult
    ) -> None:
        """Verifies run.timestamp is ISO8601 format with timezone."""
        from datetime import datetime

        from wct.exporters.core import build_core_export

        store = AsyncInMemoryStore()
        export = await build_core_export(empty_result, empty_plan, store)

        # Assert - can parse as ISO8601 with timezone
        timestamp = datetime.fromisoformat(export.run.timestamp)
        assert timestamp.tzinfo is not None


# =============================================================================
# Run Status - Completed, Failed, Partial
# =============================================================================


class TestBuildCoreExportStatus:
    """Tests for run status determination in exports."""

    async def test_completed_status_when_all_succeed(
        self, empty_runbook: Runbook
    ) -> None:
        """Status is completed when all artifacts succeed."""
        from wct.exporters.core import build_core_export

        plan = ExecutionPlan(runbook=empty_runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            completed={"art1", "art2"},
            failed=set(),
            skipped=set(),
            total_duration_seconds=3.0,
        )

        store = AsyncInMemoryStore()
        await store.save(result.run_id, "art1", create_success_message(duration=1.0))
        await store.save(result.run_id, "art2", create_success_message(duration=2.0))

        export = await build_core_export(result, plan, store)

        assert export.run.status == "completed"

    async def test_failed_status_when_any_fail(self, empty_runbook: Runbook) -> None:
        """Status is failed when any artifact fails."""
        from wct.exporters.core import build_core_export

        plan = ExecutionPlan(runbook=empty_runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            completed={"art1"},
            failed={"art2"},
            skipped=set(),
            total_duration_seconds=3.0,
        )

        store = AsyncInMemoryStore()
        await store.save(result.run_id, "art1", create_success_message(duration=1.0))
        await store.save(
            result.run_id,
            "art2",
            create_error_message("Something went wrong", duration=2.0),
        )

        export = await build_core_export(result, plan, store)

        assert export.run.status == "failed"

    async def test_partial_status_when_artifacts_skipped(
        self, empty_runbook: Runbook
    ) -> None:
        """Status is partial when artifacts skipped but none failed."""
        from wct.exporters.core import build_core_export

        plan = ExecutionPlan(runbook=empty_runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            completed={"art1"},
            failed=set(),
            skipped={"art2", "art3"},
            total_duration_seconds=1.0,
        )

        store = AsyncInMemoryStore()
        await store.save(result.run_id, "art1", create_success_message(duration=1.0))

        export = await build_core_export(result, plan, store)

        assert export.run.status == "partial"


# =============================================================================
# Errors & Skipped Lists
# =============================================================================


class TestBuildCoreExportErrorsAndSkipped:
    """Tests for errors and skipped lists in exports."""

    async def test_errors_list_contains_failed_artifacts(
        self, empty_runbook: Runbook
    ) -> None:
        """Errors list includes artifact_id and error message for failures."""
        from wct.exporters.core import build_core_export

        plan = ExecutionPlan(runbook=empty_runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            completed=set(),
            failed={"art1", "art2"},
            skipped=set(),
            total_duration_seconds=3.0,
        )

        store = AsyncInMemoryStore()
        await store.save(
            result.run_id,
            "art1",
            create_error_message("Database connection failed", duration=1.0),
        )
        await store.save(
            result.run_id,
            "art2",
            create_error_message("Timeout exceeded", duration=2.0),
        )

        export = await build_core_export(result, plan, store)

        assert len(export.errors) == 2
        error_ids = {err.artifact_id for err in export.errors}
        assert error_ids == {"art1", "art2"}
        art1_error = next(err for err in export.errors if err.artifact_id == "art1")
        assert art1_error.error == "Database connection failed"

    async def test_skipped_list_contains_skipped_artifact_ids(
        self, empty_runbook: Runbook
    ) -> None:
        """Skipped list contains IDs of skipped artifacts."""
        from wct.exporters.core import build_core_export

        plan = ExecutionPlan(runbook=empty_runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            completed={"art1"},
            failed=set(),
            skipped={"art2", "art3", "art4"},
            total_duration_seconds=1.0,
        )

        store = AsyncInMemoryStore()
        await store.save(result.run_id, "art1", create_success_message(duration=1.0))

        export = await build_core_export(result, plan, store)

        assert len(export.skipped) == 3
        assert set(export.skipped) == {"art2", "art3", "art4"}


# =============================================================================
# Summary Counts
# =============================================================================


class TestBuildCoreExportSummary:
    """Tests for summary statistics in exports."""

    async def test_summary_counts_are_accurate(self, empty_runbook: Runbook) -> None:
        """Summary total/succeeded/failed/skipped counts match reality."""
        from wct.exporters.core import build_core_export

        plan = ExecutionPlan(runbook=empty_runbook, dag=Mock(), artifact_schemas={})
        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            completed={"success1", "success2"},
            failed={"failed1"},
            skipped={"skipped1", "skipped2"},
            total_duration_seconds=3.0,
        )

        store = AsyncInMemoryStore()
        await store.save(
            result.run_id, "success1", create_success_message(duration=1.0)
        )
        await store.save(
            result.run_id, "success2", create_success_message(duration=1.0)
        )
        await store.save(
            result.run_id, "failed1", create_error_message("Error", duration=1.0)
        )

        export = await build_core_export(result, plan, store)

        assert export.summary.total == 5  # 2 completed + 1 failed + 2 skipped
        assert export.summary.succeeded == 2
        assert export.summary.failed == 1
        assert export.summary.skipped == 2


# =============================================================================
# Output Entries - Filtering, Schema, Metadata
# =============================================================================


class TestBuildCoreExportOutputs:
    """Tests for output entries in exports."""

    async def test_outputs_only_include_artifacts_with_output_true(self) -> None:
        """Only artifacts marked output:true appear in outputs list."""
        from waivern_orchestration import ArtifactDefinition, SourceConfig

        from wct.exporters.core import build_core_export

        # Arrange
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

        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            completed={"art1", "art2", "art3"},
            failed=set(),
            skipped=set(),
            total_duration_seconds=3.0,
        )

        store = AsyncInMemoryStore()
        await store.save(
            result.run_id,
            "art1",
            create_success_message({"data": "test1"}, schema=schema),
        )
        await store.save(
            result.run_id,
            "art2",
            create_success_message({"data": "test2"}, schema=schema),
        )
        await store.save(
            result.run_id,
            "art3",
            create_success_message({"data": "test3"}, schema=schema),
        )

        # Act
        export = await build_core_export(result, plan, store)

        # Assert - only art1 should be in outputs
        assert len(export.outputs) == 1
        assert export.outputs[0].artifact_id == "art1"

    async def test_output_entry_includes_schema_info(self) -> None:
        """Output entries include schema name/version when available."""
        from waivern_orchestration import ArtifactDefinition, SourceConfig

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

        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            completed={"art1"},
            failed=set(),
            skipped=set(),
            total_duration_seconds=1.0,
        )

        store = AsyncInMemoryStore()
        await store.save(
            result.run_id,
            "art1",
            create_success_message({"data": "test"}, schema=schema),
        )

        # Act
        export = await build_core_export(result, plan, store)

        # Assert - output entry should include schema info
        assert len(export.outputs) == 1
        assert export.outputs[0].output_schema is not None
        assert export.outputs[0].output_schema.name == "my_schema"
        assert export.outputs[0].output_schema.version == "2.1.0"

    async def test_output_entry_includes_artifact_metadata(self) -> None:
        """Output entries include name/description/contact when present."""
        from waivern_orchestration import ArtifactDefinition, SourceConfig

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

        result = ExecutionResult(
            run_id="123e4567-e89b-12d3-a456-426614174000",
            start_timestamp="2024-01-15T10:30:00+00:00",
            completed={"art1"},
            failed=set(),
            skipped=set(),
            total_duration_seconds=1.0,
        )

        store = AsyncInMemoryStore()
        await store.save(
            result.run_id,
            "art1",
            create_success_message({"data": "test"}, schema=schema),
        )

        # Act
        export = await build_core_export(result, plan, store)

        # Assert - output entry should include artifact metadata
        assert len(export.outputs) == 1
        assert export.outputs[0].name == "Artifact One"
        assert export.outputs[0].description == "First test artifact"
        assert export.outputs[0].contact == "dev@example.com"


# =============================================================================
# Runbook Metadata
# =============================================================================


class TestBuildCoreExportRunbookMetadata:
    """Tests for runbook metadata in exports."""

    async def test_runbook_contact_omitted_when_not_present(
        self, empty_result: ExecutionResult
    ) -> None:
        """Runbook.contact not in export when runbook has no contact."""
        from wct.exporters.core import build_core_export

        runbook = Runbook(name="Test", description="Test", artifacts={}, contact=None)
        plan = ExecutionPlan(runbook=runbook, dag=Mock(), artifact_schemas={})

        store = AsyncInMemoryStore()
        export = await build_core_export(empty_result, plan, store)
        export_dict = export.model_dump(by_alias=True, exclude_none=True)

        assert "contact" not in export_dict["runbook"]
