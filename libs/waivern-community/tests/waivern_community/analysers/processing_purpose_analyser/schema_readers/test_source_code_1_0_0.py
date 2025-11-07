"""Tests for source_code v1.0.0 reader."""

from waivern_source_code.schemas import SourceCodeDataModel


class TestSourceCodeReader:
    """Tests for source_code schema v1.0.0 reader module."""

    def test_read_validates_and_returns_typed_model(self) -> None:
        """Test reader validates input and returns SourceCodeDataModel."""
        from waivern_community.analysers.processing_purpose_analyser.schema_readers import (
            source_code_1_0_0,
        )

        # Arrange: Valid source_code data
        input_data = {
            "schemaVersion": "1.0.0",
            "name": "Test source code",
            "description": "Test source code analysis",
            "language": "python",
            "source": "test_repo",
            "metadata": {
                "total_files": 1,
                "total_lines": 10,
                "analysis_timestamp": "2025-01-07T10:00:00Z",
            },
            "data": [
                {
                    "file_path": "test.py",
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
            ],
        }

        # Act
        result = source_code_1_0_0.read(input_data)

        # Assert
        assert isinstance(result, SourceCodeDataModel)
        assert result.schemaVersion == "1.0.0"
        assert result.name == "Test source code"
        assert result.language == "python"
        assert len(result.data) == 1
        assert result.data[0].file_path == "test.py"
