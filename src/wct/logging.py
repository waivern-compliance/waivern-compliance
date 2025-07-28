"""Logging configuration for the WCT system."""

import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for different log levels."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # Add color to the level name
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
            )
        return super().format(record)


def setup_logging(
    level: str = "INFO", format_string: str | None = None, use_colors: bool = True
) -> None:
    """Configure logging for the WCT system.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string for log messages
        use_colors: Whether to use colored output (default: True)
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Default format string
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create formatter
    if use_colors and sys.stderr.isatty():  # Only use colors if output is a terminal
        formatter = ColoredFormatter(format_string)
    else:
        formatter = logging.Formatter(format_string)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    # Add handler to root logger
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Pre-configured loggers for common WCT components
def get_executor_logger() -> logging.Logger:
    """Get logger for executor components."""
    return get_logger("wct.executor")


def get_connector_logger(connector_name: str) -> logging.Logger:
    """Get logger for connector components."""
    return get_logger(f"wct.connectors.{connector_name}")


def get_plugin_logger(plugin_name: str) -> logging.Logger:
    """Get logger for plugin components."""
    return get_logger(f"wct.plugins.{plugin_name}")


def get_ruleset_logger(ruleset_name: str) -> logging.Logger:
    """Get logger for ruleset components."""
    return get_logger(f"wct.rulesets.{ruleset_name}")


def get_cli_logger() -> logging.Logger:
    """Get logger for CLI components."""
    return get_logger("wct.cli")
