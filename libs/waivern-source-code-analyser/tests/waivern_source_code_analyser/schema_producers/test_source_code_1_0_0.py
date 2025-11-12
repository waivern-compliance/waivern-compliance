"""Tests for source_code v1.0.0 producer."""


class TestSourceCodeProducer:
    """Tests for source_code schema v1.0.0 producer module."""

    def test_produce_formats_output_correctly(self) -> None:
        """Test producer formats source_code output with correct structure."""
        from waivern_source_code_analyser.schema_producers import (
            source_code_1_0_0,
        )

        # Arrange - based on SourceCodeDataModel structure
        schema_version = "1.0.0"
        source_config = {
            "path_name": "test_project",
            "path_str": "/path/to/test_project",
            "language": "python",
        }
        analysis_summary = {
            "total_files": 1,
            "total_lines": 10,
        }

        files_data = [
            {
                "file_path": "/path/to/test_project/test.py",
                "language": "python",
                "raw_content": "def test():\n    pass",
                "metadata": {
                    "file_size": 100,
                    "line_count": 2,
                    "last_modified": "2025-01-07T10:00:00Z",
                },
                "functions": [],
                "classes": [],
                "imports": [],
            }
        ]

        # Act
        result = source_code_1_0_0.produce(
            schema_version=schema_version,
            source_config=source_config,
            analysis_summary=analysis_summary,
            files_data=files_data,
        )

        # Assert
        assert result["schemaVersion"] == "1.0.0"
        assert result["name"] == "source_code_analysis_test_project"
        assert result["language"] == "python"
        assert result["source"] == "/path/to/test_project"
        assert result["metadata"]["total_files"] == 1
        assert result["metadata"]["total_lines"] == 10
        assert "analysis_timestamp" in result["metadata"]
        assert len(result["data"]) == 1
        assert result["data"][0]["file_path"] == "/path/to/test_project/test.py"
