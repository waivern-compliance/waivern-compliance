"""Tests for FilesystemConnector."""

import os
import tempfile
from pathlib import Path

import pytest
from waivern_core.errors import ConnectorConfigError, ConnectorExtractionError
from waivern_core.message import Message
from waivern_core.schemas import (
    FilesystemMetadata,
    Schema,
    StandardInputDataModel,
)

from waivern_filesystem.config import FilesystemConnectorConfig
from waivern_filesystem.connector import FilesystemConnector

# Test constants - expected behaviour from public interface
EXPECTED_CONNECTOR_NAME = "filesystem_connector"
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
        return Schema("standard_input", "1.0.0")

    def test_get_name_returns_correct_name(self):
        """Test get_name returns the connector name."""
        assert FilesystemConnector.get_name() == EXPECTED_CONNECTOR_NAME

    def test_get_supported_output_schemas_returns_standard_input(self):
        """Test that the connector supports standard_input schema."""
        output_schemas = FilesystemConnector.get_supported_output_schemas()

        assert len(output_schemas) == 1
        assert output_schemas[0].name == "standard_input"
        assert output_schemas[0].version == "1.0.0"

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

    def test_extract_with_unsupported_schema_raises_error(self, sample_file):
        """Test extract with unsupported schema raises error."""
        config = FilesystemConnectorConfig.from_properties({"path": str(sample_file)})
        connector = FilesystemConnector(config)
        unsupported_schema = Schema("unsupported_schema", "1.0.0")

        with pytest.raises(ConnectorConfigError, match="Unsupported output schema"):
            connector.extract(unsupported_schema)

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

    def test_extract_directory_with_include_patterns(
        self, sample_directory, standard_input_schema
    ):
        """Test extracting directory with include patterns for positive filtering."""
        # Add files of different types
        (sample_directory / "script.php").write_text("PHP content")
        (sample_directory / "app.js").write_text("JS content")
        (sample_directory / "readme.md").write_text("Markdown content")

        # Pattern "**/*.php" matches all PHP files (gitwildmatch semantics)
        config = FilesystemConnectorConfig.from_properties(
            {
                "path": str(sample_directory),
                "include_patterns": ["**/*.php", "**/*.js"],
            }
        )
        connector = FilesystemConnector(config)

        result = connector.extract(standard_input_schema)

        # Should include only .php and .js files, not .txt or .md files
        content = result.content
        file_contents = [item["content"] for item in content["data"]]
        file_paths = [item["metadata"]["file_path"] for item in content["data"]]

        # PHP and JS files should be included
        assert "PHP content" in file_contents
        assert "JS content" in file_contents

        # TXT and MD files should NOT be included
        assert "Content of file 1" not in file_contents
        assert "Content of file 2" not in file_contents
        assert "Markdown content" not in file_contents

        # Verify only expected file extensions
        assert all(
            path.endswith(".php") or path.endswith(".js") for path in file_paths
        ), f"Unexpected file types in: {file_paths}"

    def test_extract_directory_with_include_patterns_nested_directories(
        self, sample_directory, standard_input_schema
    ):
        """Test that **/*.php matches files at any depth including root (gitwildmatch semantics)."""
        # Create nested directory structure
        nested = sample_directory / "src"
        nested.mkdir()
        (nested / "app.php").write_text("Nested PHP content")
        (sample_directory / "config.php").write_text("Root PHP content")

        # Pattern "**/*.php" should match ALL PHP files (gitwildmatch semantics)
        config = FilesystemConnectorConfig.from_properties(
            {"path": str(sample_directory), "include_patterns": ["**/*.php"]}
        )
        connector = FilesystemConnector(config)

        result = connector.extract(standard_input_schema)

        content = result.content
        file_contents = [item["content"] for item in content["data"]]

        # Both nested AND root PHP files should be included (gitwildmatch behavior)
        assert "Nested PHP content" in file_contents
        assert "Root PHP content" in file_contents

    def test_extract_directory_with_no_patterns_includes_everything(
        self, sample_directory, standard_input_schema
    ):
        """Test that not specifying patterns includes all files."""
        (sample_directory / "test1.txt").write_text("Content 1")
        (sample_directory / "test2.php").write_text("Content 2")
        (sample_directory / "test3.log").write_text("Content 3")

        config = FilesystemConnectorConfig.from_properties(
            {"path": str(sample_directory)}
        )
        connector = FilesystemConnector(config)

        result = connector.extract(standard_input_schema)
        content = result.content
        file_contents = [item["content"] for item in content["data"]]

        # All files should be included when no patterns specified
        assert "Content 1" in file_contents
        assert "Content 2" in file_contents
        assert "Content 3" in file_contents

    def test_extract_directory_with_empty_include_patterns_matches_nothing(
        self, sample_directory, standard_input_schema
    ):
        """Test that explicit empty include_patterns list matches no files."""
        (sample_directory / "test1.txt").write_text("Content 1")
        (sample_directory / "test2.txt").write_text("Content 2")

        config = FilesystemConnectorConfig.from_properties(
            {"path": str(sample_directory), "include_patterns": []}
        )
        connector = FilesystemConnector(config)

        # Empty include_patterns should match nothing
        with pytest.raises(
            ConnectorExtractionError, match="No files found in directory"
        ):
            connector.extract(standard_input_schema)

    def test_extract_directory_with_patterns_containing_special_characters(
        self, sample_directory, standard_input_schema
    ):
        """Test patterns with dashes, dots, underscores work correctly."""
        # Create files with special characters in names
        (sample_directory / "test-file.php").write_text("Dash content")
        (sample_directory / "test_file.js").write_text("Underscore content")
        (sample_directory / ".htaccess").write_text("Dotfile content")
        (sample_directory / "regular.txt").write_text("Regular content")

        config = FilesystemConnectorConfig.from_properties(
            {
                "path": str(sample_directory),
                "include_patterns": ["*-*.php", "*_*.js", ".*"],
            }
        )
        connector = FilesystemConnector(config)

        result = connector.extract(standard_input_schema)
        content = result.content
        file_contents = [item["content"] for item in content["data"]]

        # Files matching special character patterns should be included
        assert "Dash content" in file_contents
        assert "Underscore content" in file_contents
        assert "Dotfile content" in file_contents
        # File not matching pattern should be excluded
        assert "Regular content" not in file_contents

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
            schema = Schema("standard_input", "1.0.0")

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
        assert data_item.metadata.connector_type == "filesystem_connector"
        assert data_item.metadata.file_path == str(sample_file)
        assert str(sample_file) in data_item.metadata.source
