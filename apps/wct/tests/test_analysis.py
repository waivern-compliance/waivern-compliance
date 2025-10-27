"""Tests for analysis result handling and export functionality.

This module tests the public API of analysis result processing, focusing on
black-box behaviour verification without accessing internal implementation details ✔️.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from wct.analysis import AnalysisMetadata, AnalysisResult, AnalysisResultsExporter
from wct.organisation import OrganisationConfig


class TestAnalysisResultBehaviour:
    """Test AnalysisResult creation and field access."""

    def test_successful_result_creation(self) -> None:
        """Test that successful analysis result can be created with proper fields."""
        result = AnalysisResult(
            analysis_name="Personal Data Analysis",
            analysis_description="Analysis for detecting personal data patterns",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": [{"pattern": "email", "value": "test@example.com"}]},
            metadata=AnalysisMetadata(description="Personal data detection analysis"),
            success=True,
        )

        assert result.analysis_name == "Personal Data Analysis"
        assert result.input_schema == "standard_input"
        assert result.output_schema == "personal_data_finding"
        assert result.data == {
            "findings": [{"pattern": "email", "value": "test@example.com"}]
        }
        assert result.metadata is not None
        assert result.metadata.description == "Personal data detection analysis"
        assert result.success is True
        assert result.error_message is None

    def test_failed_result_creation(self) -> None:
        """Test that failed analysis result can be created with error message."""
        result = AnalysisResult(
            analysis_name="Processing Purpose Analysis",
            analysis_description="Analysis for identifying data processing purposes",
            input_schema="source_code",
            output_schema="processing_purpose_finding",
            data={},
            success=False,
            error_message="Connector failed to extract data from source",
        )

        assert result.success is False
        assert result.error_message == "Connector failed to extract data from source"
        assert result.data == {}
        assert result.metadata is None

    def test_result_with_complex_data_structures(self) -> None:
        """Test AnalysisResult handles complex nested data structures correctly."""
        complex_data = {
            "personal_data_findings": [
                {
                    "category": "contact_information",
                    "patterns": ["email", "phone"],
                    "evidence": {
                        "file_path": "user_data.php",
                        "line_numbers": [15, 23],
                        "context": "User registration form processing",
                    },
                    "risk_level": "medium",
                    "gdpr_articles": ["Article 6", "Article 7"],
                }
            ],
            "summary": {"total_patterns": 2, "high_risk_count": 0},
        }

        result = AnalysisResult(
            analysis_name="Comprehensive Data Analysis",
            analysis_description="Detailed analysis with complex data structures",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data=complex_data,
            metadata=AnalysisMetadata(
                description="Comprehensive analysis with complex structures"
            ),
            success=True,
        )

        assert result.data == complex_data
        assert result.metadata is not None
        assert (
            result.metadata.description
            == "Comprehensive analysis with complex structures"
        )

    def test_result_with_empty_data(self) -> None:
        """Test AnalysisResult works with empty data."""
        result = AnalysisResult(
            analysis_name="Minimal Analysis",
            analysis_description="Basic analysis with empty data",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={},
            success=True,
        )

        assert result.data == {}
        assert result.metadata is None
        assert result.success is True

    def test_result_with_contact(self) -> None:
        """Test that AnalysisResult properly handles contact information."""
        result = AnalysisResult(
            analysis_name="Contact Test Analysis",
            analysis_description="Analysis testing contact property",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": [{"pattern": "email", "value": "test@example.com"}]},
            metadata=AnalysisMetadata(description="Analysis with contact information"),
            contact="Jane Austin <jane.austin@company.com>",
            success=True,
        )

        assert result.contact == "Jane Austin <jane.austin@company.com>"
        assert result.analysis_name == "Contact Test Analysis"
        assert result.success is True

    def test_result_without_contact(self) -> None:
        """Test that AnalysisResult without contact defaults to None."""
        result = AnalysisResult(
            analysis_name="No Contact Test Analysis",
            analysis_description="Analysis testing no contact property",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": []},
            metadata=AnalysisMetadata(description="Analysis without contact"),
            success=True,
        )

        assert result.contact is None
        assert result.analysis_name == "No Contact Test Analysis"
        assert result.success is True


class TestAnalysisResultsExporterSaveToJsonBehaviour:
    """Test AnalysisResultsExporter save_to_json() method behaviour."""

    def test_save_single_successful_result_to_json(self) -> None:
        """Test saving a single successful analysis result creates valid JSON file."""
        result = AnalysisResult(
            analysis_name="Personal Data Analysis",
            analysis_description="Analysis for detecting personal data patterns",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": [{"pattern": "email", "count": 3}]},
            metadata=AnalysisMetadata(description="Personal data detection"),
            success=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "analysis_results.json"

            AnalysisResultsExporter.save_to_json([result], output_path)

            assert output_path.exists()
            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)

            # Verify export metadata structure
            assert "export_metadata" in saved_data
            assert "results" in saved_data
            assert saved_data["export_metadata"]["total_results"] == 1
            assert saved_data["export_metadata"]["successful_results"] == 1
            assert saved_data["export_metadata"]["failed_results"] == 0
            assert saved_data["export_metadata"]["export_format_version"] == "1.0.0"

            # Verify results data
            assert len(saved_data["results"]) == 1
            result_data = saved_data["results"][0]
            assert result_data["analysis_name"] == "Personal Data Analysis"
            assert result_data["success"] is True

    def test_save_multiple_mixed_results_to_json(self) -> None:
        """Test saving multiple results with mixed success/failure status."""
        successful_result = AnalysisResult(
            analysis_name="Successful Analysis 1",
            analysis_description="First successful analysis test case",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": []},
            metadata=AnalysisMetadata(),
            success=True,
        )

        failed_result = AnalysisResult(
            analysis_name="Failed Analysis 2",
            analysis_description="Second analysis that failed during processing",
            input_schema="source_code",
            output_schema="processing_purpose_finding",
            data={},
            metadata=AnalysisMetadata(),
            success=False,
            error_message="Analysis failed due to invalid input format",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "mixed_results.json"

            AnalysisResultsExporter.save_to_json(
                [successful_result, failed_result], output_path
            )

            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)

            assert saved_data["export_metadata"]["total_results"] == 2
            assert saved_data["export_metadata"]["successful_results"] == 1
            assert saved_data["export_metadata"]["failed_results"] == 1
            assert len(saved_data["results"]) == 2

    def test_save_with_runbook_path_includes_metadata(self) -> None:
        """Test saving results with runbook path includes it in export metadata."""
        result = AnalysisResult(
            analysis_name="Test Analysis",
            analysis_description="Test analysis for runbook path metadata",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={},
            metadata=AnalysisMetadata(),
            success=True,
        )

        runbook_path = Path("/path/to/test_runbook.yaml")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "with_runbook.json"

            AnalysisResultsExporter.save_to_json([result], output_path, runbook_path)

            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)

            assert saved_data["export_metadata"]["runbook_path"] == str(runbook_path)

    def test_save_creates_parent_directories(self) -> None:
        """Test save_to_json creates parent directories if they don't exist."""
        result = AnalysisResult(
            analysis_name="Test Analysis",
            analysis_description="Test analysis for directory creation functionality",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={},
            metadata=AnalysisMetadata(),
            success=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            nested_output_path = (
                Path(temp_dir) / "reports" / "compliance" / "results.json"
            )

            AnalysisResultsExporter.save_to_json([result], nested_output_path)

            assert nested_output_path.exists()
            assert nested_output_path.parent.exists()

    def test_save_empty_results_list(self) -> None:
        """Test saving empty results list creates valid JSON with zero counts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "empty_results.json"

            AnalysisResultsExporter.save_to_json([], output_path)

            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)

            assert saved_data["export_metadata"]["total_results"] == 0
            assert saved_data["export_metadata"]["successful_results"] == 0
            assert saved_data["export_metadata"]["failed_results"] == 0
            assert saved_data["results"] == []

    def test_save_json_includes_timestamp(self) -> None:
        """Test saved JSON includes valid ISO format timestamp."""
        result = AnalysisResult(
            analysis_name="Test Analysis",
            analysis_description="Test analysis for timestamp functionality",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={},
            metadata=AnalysisMetadata(),
            success=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "timestamped.json"

            before_save = datetime.now()
            AnalysisResultsExporter.save_to_json([result], output_path)
            after_save = datetime.now()

            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)

            timestamp_str = saved_data["export_metadata"]["timestamp"]
            saved_timestamp = datetime.fromisoformat(timestamp_str)

            assert before_save <= saved_timestamp <= after_save

    def test_save_handles_unicode_content(self) -> None:
        """Test save_to_json correctly handles Unicode content in results."""
        result = AnalysisResult(
            analysis_name="Unicode Analysis",
            analysis_description="Analysis for testing Unicode content handling",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": [{"pattern": "name", "value": "José García"}]},
            metadata=AnalysisMetadata(description="Análisis de datos personales"),
            success=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "unicode_results.json"

            AnalysisResultsExporter.save_to_json([result], output_path)

            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)

            result_data = saved_data["results"][0]
            assert result_data["data"]["findings"][0]["value"] == "José García"
            assert (
                result_data["metadata"]["description"] == "Análisis de datos personales"
            )

    def test_save_includes_runbook_contact_in_metadata(self) -> None:
        """Test that JSON export includes runbook contact in metadata when runbook is loaded."""
        result = AnalysisResult(
            analysis_name="Test Analysis",
            analysis_description="Test analysis for runbook contact metadata",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": []},
            metadata=AnalysisMetadata(),
            success=True,
        )

        # Create a runbook YAML content with contact
        runbook_content = """
name: "Test Runbook with Contact"
description: "Test runbook"
contact: "Runbook Manager <runbook@company.com>"
connectors:
  - name: test_connector
    type: filesystem
    properties:
      path: ./test
analysers:
  - name: test_analyser
    type: personal_data_analyser
    properties: {}
execution:
  - name: Test Step
    description: Test step
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a runbook file
            runbook_path = Path(temp_dir) / "test_runbook.yaml"
            with open(runbook_path, "w") as f:
                f.write(runbook_content)

            output_path = Path(temp_dir) / "results_with_runbook_contact.json"

            AnalysisResultsExporter.save_to_json(
                results=[result], output_path=output_path, runbook_path=runbook_path
            )

            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)

            # Should include runbook contact in export metadata
            assert "export_metadata" in saved_data
            assert "runbook_contact" in saved_data["export_metadata"]
            assert (
                saved_data["export_metadata"]["runbook_contact"]
                == "Runbook Manager <runbook@company.com>"
            )

    def test_save_handles_missing_runbook_contact(self) -> None:
        """Test export metadata when runbook has no contact property."""
        result = AnalysisResult(
            analysis_name="Test Analysis",
            analysis_description="Test analysis for missing runbook contact",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": []},
            metadata=AnalysisMetadata(),
            success=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "results_no_runbook_contact.json"

            AnalysisResultsExporter.save_to_json(
                results=[result], output_path=output_path
            )

            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)

            # Should include runbook_contact field as None when no runbook provided
            assert "export_metadata" in saved_data
            assert "runbook_contact" in saved_data["export_metadata"]
            assert saved_data["export_metadata"]["runbook_contact"] is None

    def test_save_includes_step_contacts_in_results(self) -> None:
        """Test that individual results include contact from AnalysisResult objects."""
        results = [
            AnalysisResult(
                analysis_name="Analysis with Contact",
                analysis_description="First analysis with contact info",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={"findings": []},
                contact="Alice Smith <alice@company.com>",
                success=True,
            ),
            AnalysisResult(
                analysis_name="Analysis without Contact",
                analysis_description="Second analysis without contact info",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={"findings": []},
                success=True,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "results_with_step_contacts.json"

            AnalysisResultsExporter.save_to_json(results, output_path)

            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)

            # Check that results include contact information
            assert len(saved_data["results"]) == 2
            assert (
                saved_data["results"][0]["contact"] == "Alice Smith <alice@company.com>"
            )
            # Contact field should be excluded when None (empty collections excluded behavior)
            assert "contact" not in saved_data["results"][1]


class TestAnalysisResultsExporterOrganisationMetadata:
    """Test AnalysisResultsExporter organisation metadata functionality."""

    def test_save_with_organisation_config_includes_metadata(self) -> None:
        """Test that providing organisation config includes it in export metadata."""
        config_data = {
            "data_controller": {
                "name": "Test Export Company",
                "address": "Export Street 123",
                "contact_email": "export@test.com",
            }
        }
        org_config = OrganisationConfig.model_validate(config_data)

        result = AnalysisResult(
            analysis_name="Test Analysis",
            analysis_description="Test analysis for organisation metadata functionality",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={},
            metadata=AnalysisMetadata(),
            success=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "with_org_config.json"

            AnalysisResultsExporter.save_to_json(
                [result], output_path, organisation_config=org_config
            )

            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)

            # Verify organisation metadata is included
            assert "organisation" in saved_data["export_metadata"]
            org_data = saved_data["export_metadata"]["organisation"]
            assert org_data["data_controller"]["name"] == "Test Export Company"
            assert org_data["data_controller"]["contact_email"] == "export@test.com"

    @patch("wct.analysis.OrganisationLoader.load")
    def test_save_without_org_config_attempts_automatic_loading(self, mock_load):
        """Test that save_to_json attempts to load organisation config automatically."""
        # Mock successful loading
        config_data = {
            "data_controller": {
                "name": "Auto Loaded Company",
                "address": "Auto Address",
                "contact_email": "auto@company.com",
            }
        }
        mock_org_config = OrganisationConfig.model_validate(config_data)
        mock_load.return_value = mock_org_config

        result = AnalysisResult(
            analysis_name="Test Analysis",
            analysis_description="Test analysis for organisation metadata functionality",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={},
            metadata=AnalysisMetadata(),
            success=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "auto_loaded.json"

            AnalysisResultsExporter.save_to_json([result], output_path)

            # Verify load was called
            mock_load.assert_called_once()

            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)

            # Verify organisation metadata was included
            assert "organisation" in saved_data["export_metadata"]
            org_data = saved_data["export_metadata"]["organisation"]
            assert org_data["data_controller"]["name"] == "Auto Loaded Company"

    @patch("wct.analysis.OrganisationLoader.load")
    def test_save_handles_no_organisation_config_gracefully(self, mock_load):
        """Test that save_to_json handles absence of organisation config gracefully."""
        mock_load.return_value = None

        result = AnalysisResult(
            analysis_name="Test Analysis",
            analysis_description="Test analysis for organisation metadata functionality",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={},
            metadata=AnalysisMetadata(),
            success=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "no_org_config.json"

            AnalysisResultsExporter.save_to_json([result], output_path)

            with open(output_path, encoding="utf-8") as f:
                saved_data = json.load(f)

            # Verify no organisation metadata is included
            assert "organisation" not in saved_data["export_metadata"]

            # Verify other metadata is still present
            assert "timestamp" in saved_data["export_metadata"]
            assert "export_format_version" in saved_data["export_metadata"]
            assert len(saved_data["results"]) == 1
