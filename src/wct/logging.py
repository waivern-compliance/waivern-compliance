"""Python-standard logging configuration for WCT.

This module provides centralized logging setup following Python best practices
using logging.config.dictConfig() with YAML configuration files stored in src/wct/config/.
"""

from __future__ import annotations

import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Any, cast

import yaml

from wct.utils import ProjectUtilsError, get_project_root


class LoggingError(Exception):
    """Exception raised for logging configuration errors."""

    pass


def get_config_path(
    config_name: str | None = None, environment: str | None = None
) -> Path:
    """Get the path to a logging configuration file.

    Args:
        config_name: Name of config file (without extension)
        environment: Environment (dev, test, prod) for environment-specific configs

    Returns:
        Path to the logging configuration file

    Raises:
        LoggingError: If no suitable configuration file is found

    """
    project_root = get_project_root()
    config_dir = project_root / "src" / "wct" / "config"

    # Determine config file name based on environment
    if config_name:
        config_file = f"{config_name}.yaml"
    elif environment:
        config_file = f"logging-{environment}.yaml"
    else:
        # Default priority: environment-specific -> general
        env = os.getenv("WCT_ENV", "").lower()
        if env and env in ["dev", "development", "test", "prod", "production"]:
            if env in ["development"]:
                env = "dev"
            elif env in ["production"]:
                env = "prod"
            config_file = f"logging-{env}.yaml"
        else:
            config_file = "logging.yaml"

    config_path = config_dir / config_file

    # Fallback to default if specific config doesn't exist
    if not config_path.exists() and config_file != "logging.yaml":
        config_path = config_dir / "logging.yaml"

    if not config_path.exists():
        raise LoggingError(
            f"No logging configuration found. Expected at: {config_path}\n"
            f"Available configs: {list(config_dir.glob('logging*.yaml')) if config_dir.exists() else 'config directory not found'}"
        )

    return config_path


def load_config(config_path: Path) -> dict[str, Any]:
    """Load logging configuration from YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Logging configuration dictionary

    Raises:
        LoggingError: If configuration cannot be loaded or parsed

    """
    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise LoggingError(f"Invalid configuration format in {config_path}")

        # Type checker safety: yaml.safe_load returns Any, but we've verified it's a dict
        return config  # type: ignore[return-value]

    except yaml.YAMLError as e:
        raise LoggingError(f"Failed to parse YAML config {config_path}: {e}") from e
    except OSError as e:
        raise LoggingError(f"Failed to read config file {config_path}: {e}") from e


def create_log_directories(config: dict[str, Any]) -> None:
    """Create log directories referenced in the configuration.

    Args:
        config: Logging configuration dictionary

    """
    handlers = config.get("handlers", {})
    project_root = get_project_root()

    for handler_config in handlers.values():
        if isinstance(handler_config, dict) and "filename" in handler_config:
            # Make log file paths relative to project root
            log_file_path = cast(str, handler_config["filename"])
            if not os.path.isabs(log_file_path):
                log_file = project_root / log_file_path
            else:
                log_file = Path(log_file_path)

            log_file.parent.mkdir(parents=True, exist_ok=True)


def setup_logging(
    config_path: Path | str | None = None,
    level: str | None = None,
    environment: str | None = None,
    force_basic: bool = False,
) -> None:
    """Configure logging using Python standard dictConfig.

    Args:
        config_path: Path to logging configuration file
        level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Environment for config selection (dev, test, prod)
        force_basic: Force basic console logging (fallback mode)

    Raises:
        LoggingError: If logging setup fails

    """
    if force_basic:
        _setup_basic_logging(level or "INFO")
        return

    try:
        # Determine config path
        if isinstance(config_path, str):
            config_path = Path(config_path)
        elif config_path is None:
            config_path = get_config_path(environment=environment)

        # Load and apply configuration
        config = load_config(config_path)

        # Override log level if specified
        if level:
            numeric_level = getattr(logging, level.upper(), None)
            if numeric_level is None:
                raise LoggingError(f"Invalid log level: {level}")

            # Update all loggers in config
            for logger_name in config.get("loggers", {}):
                config["loggers"][logger_name]["level"] = level

            # Update root logger
            if "root" in config:
                config["root"]["level"] = level

            # Update all handlers to respect the new level
            # (handlers can filter out messages below their level)
            for handler_name, handler_config in config.get("handlers", {}).items():
                if isinstance(handler_config, dict) and "level" in handler_config:
                    # Only lower the handler level if the new level is more verbose
                    handler_level_str = cast(
                        str, handler_config["level"]
                    )  # We know it's a string from config
                    current_handler_level = getattr(
                        logging, handler_level_str, logging.INFO
                    )
                    if numeric_level < current_handler_level:
                        config["handlers"][handler_name]["level"] = level

        # Create necessary directories
        create_log_directories(config)

        # Apply configuration
        logging.config.dictConfig(config)

        logger = logging.getLogger(__name__)
        logger.info(
            "Logging configured from: %s", config_path.relative_to(get_project_root())
        )

    except (LoggingError, ProjectUtilsError, ImportError, KeyError, ValueError) as e:
        # Fallback to basic logging on any configuration error
        fallback_level = level or "INFO"
        _setup_basic_logging(fallback_level)

        fallback_logger = logging.getLogger(__name__)
        fallback_logger.warning(
            "Failed to configure logging from file (%s), using basic console logging at %s level",
            e,
            fallback_level,
        )


def _setup_basic_logging(level: str) -> None:
    """Set up basic console logging as fallback.

    Args:
        level: Logging level string

    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure basic logging
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
        force=True,  # Override existing configuration
    )


# Standard Python logging - users should use logging.getLogger(__name__) directly
