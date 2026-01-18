"""Tests for source_code v1.0.0 reader."""

from waivern_source_code_analyser import SourceCodeDataModel


class TestSourceCodeReader:
    """Tests for source_code schema v1.0.0 reader module."""

    def test_create_handler_returns_schema_input_handler(self) -> None:
        """Test that create_handler returns a valid SchemaInputHandler."""
        from waivern_data_subject_analyser.schema_readers import source_code_1_0_0
        from waivern_data_subject_analyser.source_code_schema_input_handler import (
            SourceCodeSchemaInputHandler,
        )
        from waivern_data_subject_analyser.types import DataSubjectAnalyserConfig

        # Arrange
        config = DataSubjectAnalyserConfig.from_properties({})

        # Act
        handler = source_code_1_0_0.create_handler(config)

        # Assert
        assert isinstance(handler, SourceCodeSchemaInputHandler)

    def test_read_returns_pydantic_model(self) -> None:
        """Test reader returns SourceCodeDataModel from dict input."""
        from waivern_data_subject_analyser.schema_readers import (
            source_code_1_0_0,
        )

        # Arrange: Valid source_code data as dict (from JSON schema validation)
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

        # Assert - result is Pydantic model with correct data
        assert isinstance(result, SourceCodeDataModel)
        assert result.schemaVersion == "1.0.0"
        assert result.name == "Test source code"
        assert len(result.data) == 1
        assert result.data[0].file_path == "test.py"
        assert result.data[0].raw_content == "def test():\n    pass"
