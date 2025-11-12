"""Tests for SourceCodeAnalyserConfig."""

import pytest
from waivern_core.errors import AnalyserConfigError

from waivern_source_code.analyser_config import SourceCodeAnalyserConfig


class TestSourceCodeAnalyserConfig:
    """Test suite for SourceCodeAnalyserConfig validation and creation."""

    def test_valid_config_with_all_fields(self):
        """Test creating config with all fields specified."""
        # Setup
        properties = {
            "language": "php",
            "max_file_size": 5 * 1024 * 1024,  # 5MB
        }

        # Execute
        config = SourceCodeAnalyserConfig.from_properties(properties)

        # Assert
        assert config.language == "php"
        assert config.max_file_size == 5 * 1024 * 1024

    def test_valid_config_with_defaults(self):
        """Test creating config with all defaults (empty dict)."""
        # Setup
        properties = {}

        # Execute
        config = SourceCodeAnalyserConfig.from_properties(properties)

        # Assert
        assert config.language is None  # Auto-detect
        assert config.max_file_size == 10 * 1024 * 1024  # 10MB default

    def test_invalid_language_empty_string(self):
        """Test that empty string language raises AnalyserConfigError."""
        # Setup
        properties = {"language": ""}

        # Execute & Assert
        with pytest.raises(AnalyserConfigError) as exc_info:
            SourceCodeAnalyserConfig.from_properties(properties)

        assert "Language must be a non-empty string" in str(exc_info.value)

    def test_invalid_max_file_size_zero(self):
        """Test that zero max_file_size raises AnalyserConfigError."""
        # Setup
        properties = {"max_file_size": 0}

        # Execute & Assert
        with pytest.raises(AnalyserConfigError) as exc_info:
            SourceCodeAnalyserConfig.from_properties(properties)

        assert "greater than 0" in str(exc_info.value)

    def test_invalid_max_file_size_negative(self):
        """Test that negative max_file_size raises AnalyserConfigError."""
        # Setup
        properties = {"max_file_size": -1}

        # Execute & Assert
        with pytest.raises(AnalyserConfigError) as exc_info:
            SourceCodeAnalyserConfig.from_properties(properties)

        assert "greater than 0" in str(exc_info.value)

    def test_from_properties_with_valid_data(self):
        """Test from_properties() creates valid config instance."""
        # Setup
        properties = {
            "language": "php",
            "max_file_size": 5242880,  # Exact bytes
        }

        # Execute
        config = SourceCodeAnalyserConfig.from_properties(properties)

        # Assert
        assert isinstance(config, SourceCodeAnalyserConfig)
        assert config.language == "php"
        assert config.max_file_size == 5242880

    def test_from_properties_with_invalid_data(self):
        """Test from_properties() raises AnalyserConfigError on invalid input."""
        # Setup
        properties = {"max_file_size": -100}

        # Execute & Assert
        with pytest.raises(AnalyserConfigError) as exc_info:
            SourceCodeAnalyserConfig.from_properties(properties)

        assert "Invalid source code analyser configuration" in str(exc_info.value)

    def test_language_normalised_to_lowercase(self):
        """Test that language is normalised to lowercase."""
        # Setup
        properties = {"language": "PHP"}

        # Execute
        config = SourceCodeAnalyserConfig.from_properties(properties)

        # Assert
        assert config.language == "php"

    def test_language_whitespace_stripped(self):
        """Test that language whitespace is stripped."""
        # Setup
        properties = {"language": "  php  "}

        # Execute
        config = SourceCodeAnalyserConfig.from_properties(properties)

        # Assert
        assert config.language == "php"
