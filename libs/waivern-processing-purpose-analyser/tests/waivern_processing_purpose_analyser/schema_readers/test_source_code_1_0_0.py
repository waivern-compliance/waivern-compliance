"""Tests for source_code v1.0.0 reader."""


class TestSourceCodeReader:
    """Tests for source_code schema v1.0.0 reader module."""

    def test_read_returns_typed_dict(self) -> None:
        """Test reader returns TypedDict with validated schema data."""
        from waivern_processing_purpose_analyser.schema_readers import (
            source_code_1_0_0,
        )

        # Arrange: Valid source_code data
        input_data = {
            "schemaVersion": "1.0.0",
            "name": "Test source code",
            "description": "Test source code analysis",
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
                }
            ],
        }

        # Act
        result = source_code_1_0_0.read(input_data)

        # Assert - Runtime: it's a dict
        assert isinstance(result, dict)
        # Type checker knows: result is SourceCodeSchemaDict
        assert result["schemaVersion"] == "1.0.0"
        assert result["name"] == "Test source code"
        assert len(result["data"]) == 1
        assert result["data"][0]["file_path"] == "test.py"
        # Verify dict structure is preserved
        assert result is input_data  # Same object reference
