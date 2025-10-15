"""Tests for SourceCodeConnectorConfig."""

import pytest
from waivern_core.errors import ConnectorConfigError

from wct.connectors.source_code.config import SourceCodeConnectorConfig


class TestSourceCodeConnectorConfig:
    """Test SourceCodeConnectorConfig class."""

    def test_from_properties_with_minimal_config(self, tmp_path):
        """Test from_properties applies correct defaults with minimal config."""
        test_file = tmp_path / "test.php"
        test_file.write_text("<?php echo 'test'; ?>")

        config = SourceCodeConnectorConfig.from_properties({"path": str(test_file)})

        assert config.path == test_file
        assert config.language is None  # Auto-detected
        assert config.file_patterns == ["**/*"]  # Default
        assert config.max_file_size == 10 * 1024 * 1024  # Default 10MB
        assert config.max_files == 4000  # Default
        # Check that default exclusions are applied
        assert len(config.exclude_patterns) > 0
        assert "*.pyc" in config.exclude_patterns
        assert "__pycache__" in config.exclude_patterns

    def test_from_properties_with_full_config(self, tmp_path):
        """Test from_properties respects all provided properties."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        test_file = test_dir / "test.php"
        test_file.write_text("<?php echo 'test'; ?>")

        config = SourceCodeConnectorConfig.from_properties(
            {
                "path": str(test_dir),
                "language": "php",
                "file_patterns": ["*.php", "*.phtml"],
                "max_file_size": 5 * 1024 * 1024,  # 5MB
                "max_files": 1000,
                "exclude_patterns": ["*.log", "temp/"],
            }
        )

        assert config.path == test_dir
        assert config.language == "php"
        assert config.file_patterns == ["*.php", "*.phtml"]
        assert config.max_file_size == 5 * 1024 * 1024
        assert config.max_files == 1000
        assert config.exclude_patterns == ["*.log", "temp/"]

    def test_from_properties_missing_path_raises_error(self):
        """Test from_properties raises error when path is missing."""
        with pytest.raises(ConnectorConfigError, match="path property is required"):
            SourceCodeConnectorConfig.from_properties({})

    def test_from_properties_empty_path_raises_error(self):
        """Test from_properties raises error when path is empty."""
        with pytest.raises(ConnectorConfigError, match="path property is required"):
            SourceCodeConnectorConfig.from_properties({"path": ""})

    def test_from_properties_none_path_raises_error(self):
        """Test from_properties raises error when path is None."""
        with pytest.raises(ConnectorConfigError, match="path property is required"):
            SourceCodeConnectorConfig.from_properties({"path": None})

    def test_from_properties_nonexistent_path_raises_error(self):
        """Test from_properties raises error for nonexistent path."""
        with pytest.raises(
            ConnectorConfigError, match="Invalid source code connector configuration"
        ):
            SourceCodeConnectorConfig.from_properties(
                {"path": "/nonexistent/path/file.php"}
            )

    def test_exclude_patterns_defaults_to_common_exclusions(self, tmp_path):
        """Test that exclude_patterns defaults to common exclusions when not specified."""
        test_file = tmp_path / "test.php"
        test_file.write_text("<?php echo 'test'; ?>")

        config = SourceCodeConnectorConfig.from_properties({"path": str(test_file)})

        # Should contain all common exclusions
        expected_exclusions = [
            "*.pyc",
            "__pycache__",
            "*.class",
            "*.o",
            "*.so",
            "*.dll",
            ".git",
            ".svn",
            ".hg",
            "node_modules",
            ".DS_Store",
            "*.log",
            "*.tmp",
            "*.bak",
            "*.swp",
            "*.swo",
        ]

        for exclusion in expected_exclusions:
            assert exclusion in config.exclude_patterns

    def test_exclude_patterns_can_be_overridden(self, tmp_path):
        """Test that exclude_patterns can be completely overridden by user."""
        test_file = tmp_path / "test.php"
        test_file.write_text("<?php echo 'test'; ?>")

        custom_exclusions = ["*.log", "build/", "temp/"]
        config = SourceCodeConnectorConfig.from_properties(
            {"path": str(test_file), "exclude_patterns": custom_exclusions}
        )

        # Should only contain user-specified patterns, not defaults
        assert config.exclude_patterns == custom_exclusions
        assert "*.pyc" not in config.exclude_patterns
        assert "__pycache__" not in config.exclude_patterns

    def test_exclude_patterns_can_be_disabled_with_empty_list(self, tmp_path):
        """Test that exclude_patterns can be disabled with empty list."""
        test_file = tmp_path / "test.php"
        test_file.write_text("<?php echo 'test'; ?>")

        config = SourceCodeConnectorConfig.from_properties(
            {"path": str(test_file), "exclude_patterns": []}
        )

        # Should have no exclusions
        assert config.exclude_patterns == []
