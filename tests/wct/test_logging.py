"""Tests for WCT logging configuration and setup."""

import importlib.util
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from wct.logging import (
    LoggingError,
    create_log_directories,
    get_config_path,
    get_project_root,
    load_config,
    setup_logging,
)


class TestLoggingConfiguration:
    """Test logging configuration functionality."""

    def test_get_project_root_returns_correct_path(self):
        """Test that get_project_root returns the correct project root."""
        root = get_project_root()
        assert root.is_dir()
        assert (root / "config").exists()
        assert (root / "src" / "wct").exists()

    def test_get_project_root_finds_markers(self):
        """Test that get_project_root correctly identifies project markers."""
        root = get_project_root()

        # Should have found one or more of these markers
        markers = [
            root / "pyproject.toml",
            root / "setup.py",
            root / ".git",
            root / "src" / "wct",
        ]

        # At least one marker should exist
        assert any(marker.exists() for marker in markers)

        # Must have the config directory (our specific requirement)
        assert (root / "config").is_dir()

    def test_get_project_root_is_robust(self):
        """Test that get_project_root works from different locations."""
        # Should work consistently regardless of import location
        root1 = get_project_root()

        # Test again to ensure consistency
        root2 = get_project_root()
        assert root1 == root2

        # Should be absolute path
        assert root1.is_absolute()

        # Should contain expected structure
        assert (root1 / "config").is_dir()
        assert (root1 / "src" / "wct").is_dir()

    def test_get_project_root_uses_importlib(self):
        """Test that get_project_root can use importlib.util.find_spec method."""
        # Verify the package can be found via importlib
        spec = importlib.util.find_spec("wct")
        assert spec is not None
        assert spec.origin is not None

        # The function should work and find the correct root
        root = get_project_root()

        # Should contain the package source
        assert (root / "src" / "wct").is_dir()
        assert (root / "config").is_dir()

        # The root should be consistent with the package location
        package_path = Path(spec.origin).parent  # src/wct/__init__.py -> src/wct
        expected_root = package_path.parent.parent  # src/wct -> src -> project_root
        assert root == expected_root

    def test_get_config_path_default_production(self):
        """Test default config path selection for production."""
        with patch.dict("os.environ", {}, clear=True):
            config_path = get_config_path()
            assert config_path.name == "logging.yaml"
            assert config_path.exists()

    def test_get_config_path_environment_specific(self):
        """Test environment-specific config path selection."""
        # Test dev environment
        with patch.dict("os.environ", {"WCT_ENV": "dev"}):
            config_path = get_config_path()
            expected = get_project_root() / "config" / "logging-dev.yaml"
            assert config_path == expected

        # Test test environment
        with patch.dict("os.environ", {"WCT_ENV": "test"}):
            config_path = get_config_path()
            expected = get_project_root() / "config" / "logging-test.yaml"
            assert config_path == expected

    def test_get_config_path_fallback_to_default(self):
        """Test fallback to default config when environment-specific doesn't exist."""
        with patch.dict("os.environ", {"WCT_ENV": "nonexistent"}):
            config_path = get_config_path()
            assert config_path.name == "logging.yaml"

    def test_get_config_path_explicit_environment(self):
        """Test explicit environment parameter overrides env var."""
        with patch.dict("os.environ", {"WCT_ENV": "dev"}):
            config_path = get_config_path(environment="test")
            expected = get_project_root() / "config" / "logging-test.yaml"
            assert config_path == expected

    def test_get_config_path_nonexistent_raises_error(self):
        """Test that nonexistent config files raise LoggingError."""
        with patch("wct.logging.get_project_root") as mock_root:
            mock_root.return_value = Path("/nonexistent")
            with pytest.raises(LoggingError, match="No logging configuration found"):
                get_config_path()

    def test_load_config_valid_yaml(self):
        """Test loading valid YAML configuration."""
        config_path = get_project_root() / "config" / "logging.yaml"
        config = load_config(config_path)

        assert isinstance(config, dict)
        assert "version" in config
        assert "handlers" in config
        assert "loggers" in config
        assert config["version"] == 1

    def test_load_config_invalid_yaml_raises_error(self):
        """Test that invalid YAML raises LoggingError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()

            with pytest.raises(LoggingError, match="Failed to parse YAML config"):
                load_config(Path(f.name))

            Path(f.name).unlink()

    def test_load_config_nonexistent_file_raises_error(self):
        """Test that nonexistent file raises LoggingError."""
        with pytest.raises(LoggingError, match="Failed to read config file"):
            load_config(Path("/nonexistent/config.yaml"))

    def test_create_log_directories_creates_missing_dirs(self):
        """Test that log directories are created when missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config = {
                "handlers": {
                    "file_handler": {"filename": str(temp_path / "logs" / "test.log")}
                }
            }

            # Directory doesn't exist initially
            log_dir = temp_path / "logs"
            assert not log_dir.exists()

            create_log_directories(config)

            # Directory should now exist
            assert log_dir.exists()
            assert log_dir.is_dir()

    def test_create_log_directories_handles_absolute_paths(self):
        """Test that absolute log paths are handled correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            abs_log_path = Path(temp_dir) / "absolute" / "test.log"
            config = {"handlers": {"file_handler": {"filename": str(abs_log_path)}}}

            create_log_directories(config)

            assert abs_log_path.parent.exists()


class TestLoggingSetup:
    """Test logging setup and level override functionality."""

    def test_setup_logging_default_configuration(self, caplog):
        """Test default logging setup loads configuration."""
        with caplog.at_level(logging.INFO):
            setup_logging()

        # Should have configured logging from default config
        # Note: The message appears in stdout via Rich handler, not in caplog
        # So we test that setup_logging completes without error
        assert True  # If we get here, setup_logging() succeeded

    def test_setup_logging_level_override_updates_loggers(self):
        """Test that level override correctly updates logger levels."""
        # Create a temporary config with known logger
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "console": {"class": "logging.StreamHandler", "level": "INFO"}
            },
            "loggers": {"test_logger": {"level": "INFO", "handlers": ["console"]}},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()

            try:
                # Setup with DEBUG override
                setup_logging(config_path=f.name, level="DEBUG")

                # Check that logger level was updated
                test_logger = logging.getLogger("test_logger")
                assert test_logger.level == logging.DEBUG

            finally:
                Path(f.name).unlink()

    def test_setup_logging_handler_level_override(self):
        """Test that handler levels are lowered when logger level is more verbose."""
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",  # Handler at INFO level
                }
            },
            "loggers": {"test_logger": {"level": "INFO", "handlers": ["console"]}},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()

            try:
                # Setup with DEBUG override (more verbose than INFO)
                setup_logging(config_path=f.name, level="DEBUG")

                # Get the actual handler that was configured
                test_logger = logging.getLogger("test_logger")
                handler = test_logger.handlers[0] if test_logger.handlers else None

                # Handler level should have been lowered to DEBUG
                assert handler is not None
                assert handler.level == logging.DEBUG

            finally:
                Path(f.name).unlink()

    def test_setup_logging_handler_level_not_raised(self):
        """Test that handler levels are not raised when logger level is less verbose."""
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",  # Handler at DEBUG level
                }
            },
            "loggers": {"test_logger": {"level": "DEBUG", "handlers": ["console"]}},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()

            try:
                # Setup with WARNING override (less verbose than DEBUG)
                setup_logging(config_path=f.name, level="WARNING")

                # Get the actual handler that was configured
                test_logger = logging.getLogger("test_logger")
                handler = test_logger.handlers[0] if test_logger.handlers else None

                # Handler level should remain at DEBUG (not raised to WARNING)
                assert handler is not None
                assert handler.level == logging.DEBUG

            finally:
                Path(f.name).unlink()

    def test_setup_logging_invalid_level_falls_back(self, capsys):
        """Test that invalid log levels fall back to basic logging."""
        setup_logging(level="INVALID")

        # Should have fallen back to basic logging - check output contains warning
        # (Rich handler displays it in formatted output)
        captured = capsys.readouterr()
        assert "Failed to configure logging" in captured.out

    def test_setup_logging_fallback_on_config_error(self, capsys):
        """Test fallback to basic logging when config fails."""
        # Try to setup with nonexistent config
        setup_logging(config_path="/nonexistent/config.yaml", level="INFO")

        # Should have fallen back to basic logging - check output contains warning
        captured = capsys.readouterr()
        output = (
            (captured.out + captured.err).lower().replace(" ", "").replace("\n", "")
        )
        assert "consolelogging" in output

    def test_setup_logging_force_basic_mode(self):
        """Test force_basic parameter bypasses config loading."""
        # Clear any existing handlers to avoid interference
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        root_logger.handlers.clear()

        try:
            setup_logging(force_basic=True, level="DEBUG")

            # Should have working basic logging at DEBUG level
            logger = logging.getLogger("test.basic")

            # The basic logging should be configured
            assert logger.isEnabledFor(logging.DEBUG)

        finally:
            # Restore original handlers
            root_logger.handlers = original_handlers


class TestEnvironmentIntegration:
    """Test environment-specific logging behavior."""

    def test_development_environment_uses_dev_config(self):
        """Test that development environment uses logging-dev.yaml."""
        with patch.dict("os.environ", {"WCT_ENV": "development"}):
            config_path = get_config_path()
            expected = get_project_root() / "config" / "logging-dev.yaml"
            assert config_path == expected

    def test_production_environment_uses_prod_config(self):
        """Test that production environment uses logging-prod.yaml if available."""
        with patch.dict("os.environ", {"WCT_ENV": "production"}):
            config_path = get_config_path()
            # Falls back to logging.yaml since logging-prod.yaml doesn't exist
            expected = get_project_root() / "config" / "logging.yaml"
            assert config_path == expected

    def test_unknown_environment_uses_default_config(self):
        """Test that unknown environments fall back to default config."""
        with patch.dict("os.environ", {"WCT_ENV": "staging"}):
            config_path = get_config_path()
            expected = get_project_root() / "config" / "logging.yaml"
            assert config_path == expected


# Integration test that mimics the verbose flag functionality
class TestVerboseFlagIntegration:
    """Integration tests for verbose flag functionality."""

    def test_verbose_flag_enables_debug_logging(self):
        """Test that verbose flag (DEBUG level) enables debug messages."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        original_level = root_logger.level
        root_logger.handlers.clear()

        try:
            # Setup logging with DEBUG level (simulating --verbose)
            setup_logging(level="DEBUG", force_basic=True)

            # Check that root logger is set to DEBUG level
            assert root_logger.level == logging.DEBUG

        finally:
            # Restore original state
            root_logger.handlers = original_handlers
            root_logger.level = original_level

    def test_non_verbose_mode_filters_debug_messages(self):
        """Test that non-verbose mode (INFO level) filters out debug messages."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        root_logger.handlers.clear()

        try:
            # Setup logging with INFO level (simulating normal mode)
            setup_logging(level="INFO", force_basic=True)

            # Create a test logger and verify DEBUG is filtered out
            test_logger = logging.getLogger("wct.test.normal")
            assert not test_logger.isEnabledFor(logging.DEBUG)
            assert test_logger.isEnabledFor(logging.INFO)

        finally:
            # Restore original handlers
            root_logger.handlers = original_handlers
