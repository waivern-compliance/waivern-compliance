"""Tests for analysis result handling and export functionality.

This module tests the public API of analysis result processing, focusing on
black-box behaviour verification without accessing internal implementation details ✔️.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from wct.analysis import AnalysisResult, AnalysisResultsExporter
from wct.organisation import OrganisationConfig


class TestAnalysisResultToDictBehaviour:
    """Test AnalysisResult to_dict() method behaviour."""

    def test_successful_result_to_dict_structure(self) -> None:
        """Test that successful analysis result converts to correct dictionary structure."""
        result = AnalysisResult(
            analysis_name="Personal Data Analysis",
            analysis_description="Analysis for detecting personal data patterns",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": [{"pattern": "email", "value": "test@example.com"}]},
            metadata={"version": "1.0", "priority": "high"},
            success=True,
        )

        result_dict = result.to_dict()

        assert result_dict["analysis_name"] == "Personal Data Analysis"
        assert result_dict["input_schema"] == "standard_input"
        assert result_dict["output_schema"] == "personal_data_finding"
        assert result_dict["data"] == {
            "findings": [{"pattern": "email", "value": "test@example.com"}]
        }
        assert result_dict["metadata"] == {"version": "1.0", "priority": "high"}
        assert result_dict["success"] is True
        assert result_dict["error_message"] is None

    def test_failed_result_to_dict_includes_error_message(self) -> None:
        """Test that failed analysis result includes error message in dictionary."""
        result = AnalysisResult(
            analysis_name="Processing Purpose Analysis",
            analysis_description="Analysis for identifying data processing purposes",
            input_schema="source_code",
            output_schema="processing_purpose_finding",
            data={},
            metadata={},
            success=False,
            error_message="Connector failed to extract data from source",
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is False
        assert (
            result_dict["error_message"]
            == "Connector failed to extract data from source"
        )
        assert result_dict["data"] == {}
        assert result_dict["metadata"] == {}

    def test_result_to_dict_with_complex_data_structures(self) -> None:
        """Test to_dict() handles complex nested data structures correctly."""
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
            metadata={"analysis_depth": "detailed", "confidence_threshold": 0.8},
            success=True,
        )

        result_dict = result.to_dict()

        assert result_dict["data"] == complex_data
        assert result_dict["metadata"]["analysis_depth"] == "detailed"
        assert result_dict["metadata"]["confidence_threshold"] == 0.8

    def test_result_to_dict_with_empty_data_and_metadata(self) -> None:
        """Test to_dict() works correctly with empty data and metadata."""
        result = AnalysisResult(
            analysis_name="Minimal Analysis",
            analysis_description="Basic analysis with empty data and metadata",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={},
            metadata={},
            success=True,
        )

        result_dict = result.to_dict()

        assert result_dict["data"] == {}
        assert result_dict["metadata"] == {}
        assert result_dict["success"] is True

    def test_analysis_result_with_contact_to_dict(self) -> None:
        """Test that AnalysisResult with contact converts to dict correctly."""
        result = AnalysisResult(
            analysis_name="Contact Test Analysis",
            analysis_description="Analysis testing contact property",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": [{"pattern": "email", "value": "test@example.com"}]},
            metadata={"version": "1.0"},
            contact="Jane Austin <jane.austin@company.com>",
            success=True,
        )

        result_dict = result.to_dict()

        assert result_dict["contact"] == "Jane Austin <jane.austin@company.com>"
        assert result_dict["analysis_name"] == "Contact Test Analysis"
        assert result_dict["success"] is True

    def test_analysis_result_without_contact_to_dict(self) -> None:
        """Test that AnalysisResult without contact includes None in dict."""
        result = AnalysisResult(
            analysis_name="No Contact Test Analysis",
            analysis_description="Analysis testing no contact property",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": []},
            metadata={"version": "1.0"},
            success=True,
        )

        result_dict = result.to_dict()

        assert "contact" in result_dict
        assert result_dict["contact"] is None
        assert result_dict["analysis_name"] == "No Contact Test Analysis"
        assert result_dict["success"] is True


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
            metadata={"version": "1.0"},
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
            metadata={},
            success=True,
        )

        failed_result = AnalysisResult(
            analysis_name="Failed Analysis 2",
            analysis_description="Second analysis that failed during processing",
            input_schema="source_code",
            output_schema="processing_purpose_finding",
            data={},
            metadata={},
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
            metadata={},
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
            metadata={},
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
            metadata={},
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
            metadata={"description": "Análisis de datos personales"},
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
            metadata={},
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
            metadata={},
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
                metadata={},
                contact="Alice Smith <alice@company.com>",
                success=True,
            ),
            AnalysisResult(
                analysis_name="Analysis without Contact",
                analysis_description="Second analysis without contact info",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={"findings": []},
                metadata={},
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
            assert saved_data["results"][1]["contact"] is None


class TestAnalysisResultsExporterGetSummaryStatsBehaviour:
    """Test AnalysisResultsExporter get_summary_stats() method behaviour."""

    def test_summary_stats_for_empty_results_list(self) -> None:
        """Test get_summary_stats returns correct structure for empty results."""
        stats = AnalysisResultsExporter.get_summary_stats([])

        assert stats["total"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["analysers"] == []
        assert stats["schemas"]["input"] == []
        assert stats["schemas"]["output"] == []

    def test_summary_stats_for_all_successful_results(self) -> None:
        """Test get_summary_stats calculates correct statistics for all successful results."""
        results = [
            AnalysisResult(
                analysis_name="Personal Data Analysis",
                analysis_description="Analysis for detecting personal data patterns",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={"findings": []},
                metadata={},
                success=True,
            ),
            AnalysisResult(
                analysis_name="Processing Purpose Analysis",
                analysis_description="Analysis for identifying data processing purposes",
                input_schema="source_code",
                output_schema="processing_purpose_finding",
                data={"purposes": []},
                metadata={},
                success=True,
            ),
        ]

        stats = AnalysisResultsExporter.get_summary_stats(results)

        assert stats["total"] == 2
        assert stats["successful"] == 2
        assert stats["failed"] == 0
        assert stats["success_rate"] == 100.0
        assert set(stats["analysers"]) == {
            "Personal Data Analysis",
            "Processing Purpose Analysis",
        }
        assert set(stats["schemas"]["input"]) == {"standard_input", "source_code"}
        assert set(stats["schemas"]["output"]) == {
            "personal_data_finding",
            "processing_purpose_finding",
        }
        assert stats["error_summary"] == []

    def test_summary_stats_for_mixed_success_failure_results(self) -> None:
        """Test get_summary_stats handles mixed successful and failed results."""
        results = [
            AnalysisResult(
                analysis_name="Successful Analysis",
                analysis_description="First analysis that completed successfully",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={},
                metadata={},
                success=True,
            ),
            AnalysisResult(
                analysis_name="Failed Connection Analysis",
                analysis_description="Analysis that failed due to connection timeout",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={},
                metadata={},
                success=False,
                error_message="Connection timeout",
            ),
            AnalysisResult(
                analysis_name="Invalid Format Analysis",
                analysis_description="Analysis that failed due to invalid file format",
                input_schema="source_code",
                output_schema="processing_purpose_finding",
                data={},
                metadata={},
                success=False,
                error_message="Invalid file format",
            ),
        ]

        stats = AnalysisResultsExporter.get_summary_stats(results)

        assert stats["total"] == 3
        assert stats["successful"] == 1
        assert stats["failed"] == 2
        assert stats["success_rate"] == pytest.approx(33.33, rel=1e-2)
        assert set(stats["analysers"]) == {
            "Successful Analysis",
            "Failed Connection Analysis",
            "Invalid Format Analysis",
        }

        # Check error summary
        error_summary = stats["error_summary"]
        assert len(error_summary) == 2
        error_analysers = {error["analyser"] for error in error_summary}
        assert error_analysers == {
            "Failed Connection Analysis",
            "Invalid Format Analysis",
        }

    def test_summary_stats_deduplicates_analyser_and_schema_names(self) -> None:
        """Test get_summary_stats correctly deduplicates repeated analyser and schema names."""
        results = [
            AnalysisResult(
                analysis_name="Repeated Analysis",
                analysis_description="First instance of repeated analysis",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={},
                metadata={},
                success=True,
            ),
            AnalysisResult(
                analysis_name="Repeated Analysis",
                analysis_description="Second instance of repeated analysis",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={},
                metadata={},
                success=True,
            ),
            AnalysisResult(
                analysis_name="Repeated Analysis",
                analysis_description="Third instance of repeated analysis that failed",
                input_schema="source_code",
                output_schema="processing_purpose_finding",
                data={},
                metadata={},
                success=False,
                error_message="Processing failed",
            ),
        ]

        stats = AnalysisResultsExporter.get_summary_stats(results)

        assert len(stats["analysers"]) == 1
        assert stats["analysers"][0] == "Repeated Analysis"
        assert set(stats["schemas"]["input"]) == {"standard_input", "source_code"}
        assert set(stats["schemas"]["output"]) == {
            "personal_data_finding",
            "processing_purpose_finding",
        }

    def test_summary_stats_success_rate_calculation_precision(self) -> None:
        """Test get_summary_stats calculates success rate with proper precision."""
        # Create 7 results: 5 successful, 2 failed (71.428571...% success rate)
        results: list[AnalysisResult] = []
        for i in range(5):
            results.append(
                AnalysisResult(
                    analysis_name=f"Successful Analysis {i}",
                    analysis_description=f"Success test case number {i}",
                    input_schema="standard_input",
                    output_schema="personal_data_finding",
                    data={},
                    metadata={},
                    success=True,
                )
            )
        for i in range(2):
            results.append(
                AnalysisResult(
                    analysis_name=f"Failed Analysis {i}",
                    analysis_description=f"Failed test case number {i}",
                    input_schema="standard_input",
                    output_schema="personal_data_finding",
                    data={},
                    metadata={},
                    success=False,
                    error_message=f"Error {i}",
                )
            )

        stats = AnalysisResultsExporter.get_summary_stats(results)

        expected_success_rate = (5 / 7) * 100
        assert stats["success_rate"] == pytest.approx(expected_success_rate, rel=1e-10)


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
            metadata={},
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
            metadata={},
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
            metadata={},
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
