"""Tests for source_code v1.0.0 reader in waivern_personal_data_analyser."""

from typing import Any

from waivern_core.schemas import StandardInputDataModel

from waivern_personal_data_analyser.schema_readers import source_code_1_0_0

SOURCE_CODE_INPUT: dict[str, Any] = {
    "schemaVersion": "1.0.0",
    "name": "Test source code",
    "description": "Test",
    "source": "test_repo",
    "metadata": {
        "total_files": 1,
        "total_lines": 5,
        "analysis_timestamp": "2025-01-01T00:00:00Z",
    },
    "data": [
        {
            "file_path": "src/auth.php",
            "language": "php",
            "raw_content": "$user_id = $_POST['user_id'];",
            "metadata": {"file_size": 100, "line_count": 5, "last_modified": None},
        }
    ],
}

MULTI_FILE_INPUT: dict[str, Any] = {
    "schemaVersion": "1.0.0",
    "name": "Multi-file source",
    "description": "Test",
    "source": "test_repo",
    "metadata": {
        "total_files": 3,
        "total_lines": 15,
        "analysis_timestamp": "2025-01-01T00:00:00Z",
    },
    "data": [
        {
            "file_path": "src/auth.php",
            "language": "php",
            "raw_content": "$user_id = $_POST['user_id'];",
            "metadata": {"file_size": 50, "line_count": 5, "last_modified": None},
        },
        {
            "file_path": "src/db.php",
            "language": "php",
            "raw_content": "$email = $row['email'];",
            "metadata": {"file_size": 50, "line_count": 5, "last_modified": None},
        },
        {
            "file_path": "src/utils.php",
            "language": "php",
            "raw_content": "function helper() {}",
            "metadata": {"file_size": 20, "line_count": 5, "last_modified": None},
        },
    ],
}


class TestSourceCodeReader:
    """Tests for source_code schema v1.0.0 reader — verifies the transform to StandardInputDataModel."""

    def test_read_returns_standard_input_model(self) -> None:
        """Test reader returns a StandardInputDataModel, not a raw dict."""
        result = source_code_1_0_0.read(SOURCE_CODE_INPUT)

        assert isinstance(result, StandardInputDataModel)

    def test_read_maps_raw_content_to_item_content(self) -> None:
        """Test file raw_content is mapped to item content for pattern matching."""
        result = source_code_1_0_0.read(SOURCE_CODE_INPUT)

        assert result.data[0].content == "$user_id = $_POST['user_id'];"

    def test_read_maps_file_path_to_metadata_source(self) -> None:
        """Test file path is preserved in metadata.source for finding traceability."""
        result = source_code_1_0_0.read(SOURCE_CODE_INPUT)

        assert result.data[0].metadata.source == "src/auth.php"

    def test_read_sets_connector_type(self) -> None:
        """Test connector_type is set to source_code_analyser on all items."""
        result = source_code_1_0_0.read(SOURCE_CODE_INPUT)

        assert result.data[0].metadata.connector_type == "source_code_analyser"

    def test_read_produces_one_item_per_file(self) -> None:
        """Test each source file produces exactly one data item in the correct order."""
        result = source_code_1_0_0.read(MULTI_FILE_INPUT)

        assert len(result.data) == 3
        sources = [item.metadata.source for item in result.data]
        assert sources == ["src/auth.php", "src/db.php", "src/utils.php"]
