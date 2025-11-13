"""Tests for FilesystemConnectorConfig."""

import pytest
from waivern_core.errors import ConnectorConfigError

from waivern_filesystem.config import FilesystemConnectorConfig


class TestFilesystemConnectorConfig:
    """Test FilesystemConnectorConfig class."""

    def test_from_properties_with_minimal_config(self, tmp_path):
        """Test from_properties applies correct defaults with minimal config."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        config = FilesystemConnectorConfig.from_properties({"path": str(test_file)})

        assert config.path == test_file
        assert config.chunk_size == 8192  # Default
        assert config.encoding == "utf-8"  # Default
        assert config.errors == "strict"  # Default
        assert config.include_patterns is None  # Default
        assert config.exclude_patterns is None  # Default
        assert config.max_files == 1000  # Default

    def test_from_properties_with_full_config(self, tmp_path):
        """Test from_properties respects all provided properties."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        config = FilesystemConnectorConfig.from_properties(
            {
                "path": str(test_file),
                "chunk_size": 4096,
                "encoding": "latin-1",
                "errors": "replace",
                "exclude_patterns": ["*.log", "*.tmp"],
                "max_files": 500,
            }
        )

        assert config.path == test_file
        assert config.chunk_size == 4096
        assert config.encoding == "latin-1"
        assert config.errors == "replace"
        assert config.exclude_patterns == ["*.log", "*.tmp"]
        assert config.max_files == 500

    def test_from_properties_missing_path_raises_error(self):
        """Test from_properties raises error when path is missing."""
        with pytest.raises(ConnectorConfigError, match="path property is required"):
            FilesystemConnectorConfig.from_properties({})

    def test_from_properties_nonexistent_path_raises_error(self):
        """Test from_properties raises error for nonexistent path."""
        with pytest.raises(ConnectorConfigError, match="Path does not exist"):
            FilesystemConnectorConfig.from_properties({"path": "/nonexistent/path"})

    def test_from_properties_with_include_patterns(self, tmp_path):
        """Test from_properties with include_patterns for positive filtering."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        config = FilesystemConnectorConfig.from_properties(
            {"path": str(test_file), "include_patterns": ["**/*.php", "**/*.js"]}
        )

        assert config.path == test_file
        assert config.include_patterns == ["**/*.php", "**/*.js"]
        assert (
            config.exclude_patterns is None
        )  # Should be None when include_patterns is set

    def test_from_properties_include_and_exclude_patterns_are_mutually_exclusive(
        self, tmp_path
    ):
        """Test that include_patterns and exclude_patterns cannot both be specified."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with pytest.raises(
            ConnectorConfigError,
            match="include_patterns and exclude_patterns are mutually exclusive",
        ):
            FilesystemConnectorConfig.from_properties(
                {
                    "path": str(test_file),
                    "include_patterns": ["**/*.php"],
                    "exclude_patterns": ["*.log"],
                }
            )

    def test_from_properties_no_patterns_defaults_to_none(self, tmp_path):
        """Test that not specifying patterns defaults to None (include everything)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        config = FilesystemConnectorConfig.from_properties({"path": str(test_file)})

        assert config.include_patterns is None
        assert config.exclude_patterns is None

    def test_from_properties_empty_include_patterns_list_is_valid(self, tmp_path):
        """Test that empty include_patterns list is valid (matches no files)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        config = FilesystemConnectorConfig.from_properties(
            {"path": str(test_file), "include_patterns": []}
        )

        assert config.include_patterns == []
