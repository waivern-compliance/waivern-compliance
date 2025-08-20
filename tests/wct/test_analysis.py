"""Tests for analysis result handling and export functionality.

This module tests the public API of analysis result processing, focusing on
black-box behaviour verification without accessing internal implementation details ✔️.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from wct.analysis import AnalysisResult, AnalysisResultsExporter


class TestAnalysisResultToDictBehaviour:
    """Test AnalysisResult to_dict() method behaviour."""

    def test_successful_result_to_dict_structure(self) -> None:
        """Test that successful analysis result converts to correct dictionary structure."""
        result = AnalysisResult(
            analyser_name="personal_data_analyser",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": [{"pattern": "email", "value": "test@example.com"}]},
            metadata={"version": "1.0", "priority": "high"},
            success=True,
        )

        result_dict = result.to_dict()

        assert result_dict["analyser_name"] == "personal_data_analyser"
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
            analyser_name="processing_purpose_analyser",
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
            analyser_name="comprehensive_analyser",
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
            analyser_name="minimal_analyser",
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


class TestAnalysisResultsExporterSaveToJsonBehaviour:
    """Test AnalysisResultsExporter save_to_json() method behaviour."""

    def test_save_single_successful_result_to_json(self) -> None:
        """Test saving a single successful analysis result creates valid JSON file."""
        result = AnalysisResult(
            analyser_name="personal_data_analyser",
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
            assert result_data["analyser_name"] == "personal_data_analyser"
            assert result_data["success"] is True

    def test_save_multiple_mixed_results_to_json(self) -> None:
        """Test saving multiple results with mixed success/failure status."""
        successful_result = AnalysisResult(
            analyser_name="analyser_1",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            data={"findings": []},
            metadata={},
            success=True,
        )

        failed_result = AnalysisResult(
            analyser_name="analyser_2",
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
            analyser_name="test_analyser",
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
            analyser_name="test_analyser",
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
            analyser_name="test_analyser",
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
            analyser_name="unicode_analyser",
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
                analyser_name="personal_data_analyser",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={"findings": []},
                metadata={},
                success=True,
            ),
            AnalysisResult(
                analyser_name="processing_purpose_analyser",
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
            "personal_data_analyser",
            "processing_purpose_analyser",
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
                analyser_name="analyser_1",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={},
                metadata={},
                success=True,
            ),
            AnalysisResult(
                analyser_name="analyser_2",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={},
                metadata={},
                success=False,
                error_message="Connection timeout",
            ),
            AnalysisResult(
                analyser_name="analyser_3",
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
        assert set(stats["analysers"]) == {"analyser_1", "analyser_2", "analyser_3"}

        # Check error summary
        error_summary = stats["error_summary"]
        assert len(error_summary) == 2
        error_analysers = {error["analyser"] for error in error_summary}
        assert error_analysers == {"analyser_2", "analyser_3"}

    def test_summary_stats_deduplicates_analyser_and_schema_names(self) -> None:
        """Test get_summary_stats correctly deduplicates repeated analyser and schema names."""
        results = [
            AnalysisResult(
                analyser_name="repeated_analyser",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={},
                metadata={},
                success=True,
            ),
            AnalysisResult(
                analyser_name="repeated_analyser",
                input_schema="standard_input",
                output_schema="personal_data_finding",
                data={},
                metadata={},
                success=True,
            ),
            AnalysisResult(
                analyser_name="repeated_analyser",
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
        assert stats["analysers"][0] == "repeated_analyser"
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
                    analyser_name=f"success_analyser_{i}",
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
                    analyser_name=f"failed_analyser_{i}",
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
