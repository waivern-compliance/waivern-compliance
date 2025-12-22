"""Tests for JSON exporter."""

from waivern_orchestration import ExecutionPlan, ExecutionResult

# =============================================================================
# Exporter Properties
# =============================================================================


class TestJsonExporterProperties:
    """Tests for JsonExporter metadata properties."""

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


# =============================================================================
# Validation & Export
# =============================================================================


class TestJsonExporterExport:
    """Tests for JsonExporter validation and export functionality."""

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

        json_str = json.dumps(export_result, indent=2)
        assert isinstance(json_str, str)
        assert len(json_str) > 0
