"""Tests for JSON exporter."""

from unittest.mock import Mock

import pytest
from waivern_orchestration import (
    ArtifactDefinition,
    ArtifactResult,
    ExecutionPlan,
    ExecutionResult,
    Runbook,
    SourceConfig,
)


class TestJsonExporter:
    """Test suite for JsonExporter."""

    @pytest.fixture
    def minimal_runbook(self) -> Runbook:
        """Create minimal valid runbook for testing."""
        return Runbook(
            name="Test Runbook",
            description="Test description",
            artifacts={
                "art1": ArtifactDefinition(
                    source=SourceConfig(type="test", properties={})
                )
            },
        )

    @pytest.fixture
    def minimal_plan(self, minimal_runbook: Runbook) -> ExecutionPlan:
        """Create minimal valid execution plan for testing."""
        return ExecutionPlan(
            runbook=minimal_runbook,
            dag=Mock(),
            artifact_schemas={},
        )

    @pytest.fixture
    def minimal_result(self) -> ExecutionResult:
        """Create minimal valid execution result for testing."""
        return ExecutionResult(
            run_id="test-id",
            start_timestamp="2025-01-01T00:00:00+00:00",
            artifacts={
                "art1": ArtifactResult(
                    artifact_id="art1",
                    success=True,
                    duration_seconds=1.0,
                )
            },
            skipped=set(),
            total_duration_seconds=1.0,
        )

    def test_name_property_returns_json(self) -> None:
        """JsonExporter.name returns 'json'."""
        from wct.exporters.json_exporter import JsonExporter

        exporter = JsonExporter()
        assert exporter.name == "json"

    def test_supported_frameworks_returns_empty_list(self) -> None:
        """JsonExporter.supported_frameworks returns empty list (framework-agnostic)."""
        from wct.exporters.json_exporter import JsonExporter

        exporter = JsonExporter()
        assert exporter.supported_frameworks == []

    def test_validate_returns_empty_list_for_any_result(
        self,
        minimal_result: ExecutionResult,
        minimal_plan: ExecutionPlan,
    ) -> None:
        """JsonExporter.validate() always returns empty list (no validation needed)."""
        from wct.exporters.json_exporter import JsonExporter

        exporter = JsonExporter()
        errors = exporter.validate(minimal_result, minimal_plan)

        assert errors == []

    def test_export_result_is_json_serializable(
        self,
        minimal_result: ExecutionResult,
        minimal_plan: ExecutionPlan,
    ) -> None:
        """Export result can be serialized with json.dumps()."""
        import json

        from wct.exporters.json_exporter import JsonExporter

        exporter = JsonExporter()
        export_result = exporter.export(minimal_result, minimal_plan)

        # Should not raise any errors
        json_str = json.dumps(export_result, indent=2)
        assert isinstance(json_str, str)
        assert len(json_str) > 0
