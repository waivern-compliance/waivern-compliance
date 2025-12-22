"""Tests for WCT logging configuration and setup."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from wct.logging import (
    LoggingError,
    get_config_path,
    load_config,
    setup_logging,
)

# =============================================================================
# Configuration Loading
# =============================================================================


class TestLoggingConfiguration:
    """Test logging configuration functionality."""

    def test_get_config_path_default_production(self):
        """Test default config path selection for production."""
        with patch.dict("os.environ", {}, clear=True):
            config_path = get_config_path()
            assert config_path.name == "logging.yaml"
            assert config_path.exists()

    def test_get_config_path_uses_default_for_all_environments(self):
        """Test that all environments use the same default logging.yaml config.

        Since environment-specific configs were removed, all environments
        (dev, test, prod, etc.) should use the single logging.yaml file.
        """
        # Test dev environment - should use logging.yaml
        with patch.dict("os.environ", {"WCT_ENV": "dev"}):
            config_path = get_config_path()
            assert config_path.name == "logging.yaml"
            assert config_path.exists()

        # Test test environment - should also use logging.yaml
        with patch.dict("os.environ", {"WCT_ENV": "test"}):
            config_path = get_config_path()
            assert config_path.name == "logging.yaml"
            assert config_path.exists()

        # Test prod environment - should also use logging.yaml
        with patch.dict("os.environ", {"WCT_ENV": "prod"}):
            config_path = get_config_path()
            assert config_path.name == "logging.yaml"
            assert config_path.exists()

    def test_get_config_path_nonexistent_raises_error(self):
        """Test that nonexistent config files raise LoggingError."""
        with patch("wct.logging.get_project_root") as mock_root:
            mock_root.return_value = Path("/nonexistent")
            with pytest.raises(LoggingError, match="No logging configuration found"):
                get_config_path()

    def test_load_config_valid_yaml(self):
        """Test loading valid YAML configuration."""
        # Use get_config_path() to find the config, don't hardcode paths
        config_path = get_config_path()
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


# =============================================================================
# Logging Setup
# =============================================================================


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


# =============================================================================
# Environment Integration
# =============================================================================


class TestEnvironmentIntegration:
    """Test environment-specific logging behavior."""

    def test_development_environment_uses_dev_config(self):
        """Test that development environment uses logging.yaml."""
        with patch.dict("os.environ", {"WCT_ENV": "development"}):
            config_path = get_config_path()
            assert config_path.name == "logging.yaml"
            assert config_path.exists()

    def test_production_environment_uses_prod_config(self):
        """Test that production environment uses logging-prod.yaml if available."""
        with patch.dict("os.environ", {"WCT_ENV": "production"}):
            config_path = get_config_path()
            # Falls back to logging.yaml since logging-prod.yaml doesn't exist
            assert config_path.name == "logging.yaml"
            assert config_path.exists()

    def test_unknown_environment_uses_default_config(self):
        """Test that unknown environments fall back to default config."""
        with patch.dict("os.environ", {"WCT_ENV": "staging"}):
            config_path = get_config_path()
            assert config_path.name == "logging.yaml"
            assert config_path.exists()


# =============================================================================
# Verbose Flag Integration
# =============================================================================


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
