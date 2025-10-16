"""Tests for FilesystemConnector."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from waivern_core.errors import ConnectorConfigError, ConnectorExtractionError
from waivern_core.message import Message
from waivern_core.schemas import (
    FilesystemMetadata,
    StandardInputDataModel,
    StandardInputSchema,
)

from waivern_community.connectors.filesystem.config import FilesystemConnectorConfig
from waivern_community.connectors.filesystem.connector import FilesystemConnector

# Test constants - expected behaviour from public interface
EXPECTED_CONNECTOR_NAME = "filesystem"
EXPECTED_DEFAULT_CHUNK_SIZE = 8192
EXPECTED_DEFAULT_ENCODING = "utf-8"
EXPECTED_DEFAULT_ERROR_HANDLING = "strict"
EXPECTED_DEFAULT_MAX_FILES = 1000
EXPECTED_DEFAULT_EXCLUDE_PATTERNS = []

# Test values
TEST_CHUNK_SIZE = 4096
TEST_ENCODING = "latin-1"
TEST_ERROR_HANDLING = "replace"
TEST_MAX_FILES = 500
TEST_EXCLUDE_PATTERNS = ["*.log", "*.tmp"]
TEST_MAX_FILES_LIMIT = 5
TEST_FILE_COUNT = 3
TEST_LARGE_CONTENT_SIZE = 10000
MIN_READABLE_FILES = 2


class TestFilesystemConnector:
    """Tests for FilesystemConnector."""

    @pytest.fixture
    def sample_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test content\nLine 2\nLine 3")
            temp_path = f.name

        yield Path(temp_path)

        # Cleanup
        if Path(temp_path).exists():
            Path(temp_path).unlink()

    @pytest.fixture
    def sample_directory(self):
        """Create a temporary directory with files for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple files
            (temp_path / "file1.txt").write_text("Content of file 1")
            (temp_path / "file2.txt").write_text("Content of file 2")

            # Create a subdirectory with a file
            subdir = temp_path / "subdir"
            subdir.mkdir()
            (subdir / "file3.txt").write_text("Content of file 3")

            yield temp_path

    @pytest.fixture
    def standard_input_schema(self):
        """Standard input schema fixture."""
        return StandardInputSchema()

    def test_get_name_returns_correct_name(self):
        """Test get_name returns the connector name."""
        assert FilesystemConnector.get_name() == EXPECTED_CONNECTOR_NAME

    def test_get_supported_output_schemas_returns_standard_input(self):
        """Test that the connector supports standard_input schema."""
        output_schemas = FilesystemConnector.get_supported_output_schemas()

        assert len(output_schemas) == 1
        assert output_schemas[0].name == "standard_input"
        assert output_schemas[0].version == "1.0.0"

    def test_from_properties_raises_error_without_path(self):
        """Test from_properties raises error when path is missing."""
        properties = {}

        with pytest.raises(ConnectorConfigError, match="path property is required"):
            FilesystemConnector.from_properties(properties)

    def test_init_with_nonexistent_path_raises_error(self):
        """Test initialisation with nonexistent path raises error."""
        nonexistent_path = "/this/path/does/not/exist"

        with pytest.raises(ConnectorConfigError, match="Path does not exist"):
            config = FilesystemConnectorConfig.from_properties(
                {"path": nonexistent_path}
            )
            FilesystemConnector(config)

    def test_init_with_file_succeeds(self, sample_file):
        """Test initialisation with valid file path."""
        config = FilesystemConnectorConfig.from_properties({"path": str(sample_file)})
        connector = FilesystemConnector(config)
        assert connector is not None

    def test_init_with_directory_succeeds(self, sample_directory):
        """Test initialisation with valid directory path."""
        config = FilesystemConnectorConfig.from_properties(
            {"path": str(sample_directory)}
        )
        connector = FilesystemConnector(config)
        assert connector is not None

    def test_extract_without_schema_uses_default(self, sample_file):
        """Test extract without schema uses default schema."""
        config = FilesystemConnectorConfig.from_properties({"path": str(sample_file)})
        connector = FilesystemConnector(config)

        result = connector.extract()

        # Should successfully extract with default schema
        assert result is not None
        assert result.schema is not None
        assert result.schema.name == "standard_input"

    def test_extract_with_unsupported_schema_raises_error(self, sample_file):
        """Test extract with unsupported schema raises error."""
        config = FilesystemConnectorConfig.from_properties({"path": str(sample_file)})
        connector = FilesystemConnector(config)
        mock_schema = Mock()
        mock_schema.name = "unsupported_schema"

        with pytest.raises(ConnectorExtractionError, match="Unsupported output schema"):
            connector.extract(mock_schema)

    def test_extract_single_file_with_standard_input_schema(
        self, sample_file, standard_input_schema
    ):
        """Test extracting single file with standard input schema."""
        config = FilesystemConnectorConfig.from_properties({"path": str(sample_file)})
        connector = FilesystemConnector(config)

        result = connector.extract(standard_input_schema)

        assert isinstance(result, Message)
        assert result.id == f"Content from {sample_file.name}"
        assert result.schema == standard_input_schema
        assert result.schema_validated is True

        # Check content structure
        content = result.content
        assert content["schemaVersion"] == "1.0.0"
        assert content["name"] == f"standard_input_from_{sample_file.name}"
        assert content["description"] == f"Content from file {sample_file.name}"
        assert content["contentEncoding"] == "utf-8"
        assert content["source"] == str(sample_file)
        assert content["metadata"]["file_count"] == 1
        assert content["metadata"]["source_type"] == "file"
        assert len(content["data"]) == 1
        assert "Test content\nLine 2\nLine 3" == content["data"][0]["content"]

    def test_extract_directory_with_standard_input_schema(
        self, sample_directory, standard_input_schema
    ):
        """Test extracting directory with standard input schema."""
        config = FilesystemConnectorConfig.from_properties(
            {"path": str(sample_directory)}
        )
        connector = FilesystemConnector(config)

        result = connector.extract(standard_input_schema)

        assert isinstance(result, Message)
        assert result.schema_validated is True

        # Check content structure
        content = result.content
        assert (
            content["metadata"]["file_count"] == TEST_FILE_COUNT
        )  # file1.txt, file2.txt, subdir/file3.txt
        assert content["metadata"]["source_type"] == "directory"
        assert len(content["data"]) == TEST_FILE_COUNT

        # Check that all files are included
        file_contents = [item["content"] for item in content["data"]]
        assert "Content of file 1" in file_contents
        assert "Content of file 2" in file_contents
        assert "Content of file 3" in file_contents

    def test_extract_directory_with_exclude_patterns(
        self, sample_directory, standard_input_schema
    ):
        """Test extracting directory with exclude patterns through public API."""
        # Add files that should be excluded
        (sample_directory / "file.log").write_text("Log content")
        (sample_directory / "temp.tmp").write_text("Temp content")

        config = FilesystemConnectorConfig.from_properties(
            {"path": str(sample_directory), "exclude_patterns": TEST_EXCLUDE_PATTERNS}
        )
        connector = FilesystemConnector(config)

        result = connector.extract(standard_input_schema)

        # Should exclude .log and .tmp files but include .txt files
        content = result.content
        assert content["metadata"]["file_count"] == TEST_FILE_COUNT  # Only .txt files

        file_contents = [item["content"] for item in content["data"]]
        assert "Log content" not in file_contents
        assert "Temp content" not in file_contents
        assert "Content of file 1" in file_contents
        assert "Content of file 2" in file_contents

    def test_extract_directory_with_max_files_limit(
        self, sample_directory, standard_input_schema
    ):
        """Test extracting directory with max_files limit through public API."""
        # Create many files
        for i in range(10):
            (sample_directory / f"extra_file_{i}.txt").write_text(f"Content {i}")

        config = FilesystemConnectorConfig.from_properties(
            {"path": str(sample_directory), "max_files": TEST_MAX_FILES_LIMIT}
        )
        connector = FilesystemConnector(config)

        result = connector.extract(standard_input_schema)

        # Should limit number of files processed
        content = result.content
        assert content["metadata"]["file_count"] == TEST_MAX_FILES_LIMIT
        assert len(content["data"]) == TEST_MAX_FILES_LIMIT

    def test_extract_large_file_with_chunked_reading(self, standard_input_schema):
        """Test extracting large file with chunked reading through public API."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            # Create content larger than default chunk size
            large_content = "A" * TEST_LARGE_CONTENT_SIZE
            f.write(large_content)
            temp_path = Path(f.name)

        try:
            config = FilesystemConnectorConfig.from_properties(
                {"path": str(temp_path), "chunk_size": 1024}
            )
            connector = FilesystemConnector(config)
            result = connector.extract(standard_input_schema)

            assert isinstance(result, Message)
            content = result.content
            assert content["data"][0]["content"] == large_content
            assert len(content["data"][0]["content"]) == TEST_LARGE_CONTENT_SIZE
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_extract_no_readable_files_raises_error(self):
        """Test extract with no readable files raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create binary file only with invalid UTF-8 bytes
            binary_file = temp_path / "binary.bin"
            binary_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd")

            config = FilesystemConnectorConfig.from_properties({"path": str(temp_path)})
            connector = FilesystemConnector(config)
            schema = StandardInputSchema()

            with pytest.raises(
                ConnectorExtractionError, match="No readable files found"
            ):
                connector.extract(schema)

    def test_extract_handles_file_read_errors_gracefully(
        self, sample_directory, standard_input_schema
    ):
        """Test extract handles individual file read errors gracefully."""
        # Create a file with restrictive permissions (if on Unix-like system)
        restricted_file = sample_directory / "restricted.txt"
        restricted_file.write_text("This file will be restricted")

        try:
            # Make file unreadable (only works on Unix-like systems)
            if os.name != "nt":  # Not Windows
                restricted_file.chmod(0o000)

            config = FilesystemConnectorConfig.from_properties(
                {"path": str(sample_directory)}
            )
            connector = FilesystemConnector(config)
            result = connector.extract(standard_input_schema)

            # Should still succeed with other readable files
            assert isinstance(result, Message)
            # Should have fewer files than total (restricted file skipped)
            content = result.content
            if os.name != "nt":  # On Unix-like systems, file should be skipped
                assert (
                    content["metadata"]["file_count"] >= MIN_READABLE_FILES
                )  # At least file1.txt and file2.txt

        finally:
            # Restore permissions for cleanup
            if os.name != "nt" and restricted_file.exists():
                restricted_file.chmod(0o644)

    def test_extract_creates_filesystem_metadata(
        self, sample_file, standard_input_schema
    ):
        """Test that filesystem connector creates FilesystemMetadata with accurate file context."""
        config = FilesystemConnectorConfig.from_properties({"path": str(sample_file)})
        connector = FilesystemConnector(config)

        result = connector.extract(standard_input_schema)

        # Validate the result conforms to FilesystemMetadata expectations
        typed_result = StandardInputDataModel[FilesystemMetadata].model_validate(
            result.content
        )

        # Should have 1 data item for the file
        assert len(typed_result.data) == 1

        # Verify data item has proper FilesystemMetadata
        data_item = typed_result.data[0]
        assert data_item.metadata.connector_type == "filesystem"
        assert data_item.metadata.file_path == str(sample_file)
        assert str(sample_file) in data_item.metadata.source
