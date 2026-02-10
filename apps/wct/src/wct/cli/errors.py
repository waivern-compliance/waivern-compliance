"""CLI error handling for WCT."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import override

import typer
from rich.console import Console
from rich.panel import Panel

logger = logging.getLogger(__name__)
console = Console()


class CLIError(Exception):
    """Exception for CLI-related errors with enhanced context.

    This exception serves as the CLI layer's unified error handling mechanism,
    providing meaningful context about what CLI operation failed and why.
    """

    def __init__(
        self,
        message: str,
        command: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialise CLI error with context.

        Args:
            message: Human-readable error message describing what went wrong
            command: Name of the CLI command that failed (e.g., "run", "validate")
            original_error: The underlying exception that caused this CLI error

        """
        super().__init__(message)
        self.command = command
        self.original_error = original_error

    @override
    def __str__(self) -> str:
        """Return formatted error message with CLI context."""
        base_message = super().__str__()
        if self.command:
            return f"CLI command '{self.command}' failed: {base_message}"
        return base_message


@contextmanager
def cli_error_handler(command: str, title: str) -> Generator[None]:
    """Context manager for unified CLI error handling.

    Catches exceptions, displays them as Rich error panels, and exits
    with code 1. Handles both pre-wrapped CLIError and raw exceptions.

    Args:
        command: CLI command name for error context.
        title: Panel title for the error display.

    """
    try:
        yield
    except CLIError as e:
        logger.error("%s: %s", title, e)
        console.print(Panel(f"[red]{e}[/red]", title=f"❌ {title}", border_style="red"))
        raise typer.Exit(1) from e
    except Exception as e:
        cli_error = CLIError(str(e), command=command, original_error=e)
        logger.error("%s: %s", title, cli_error)
        console.print(
            Panel(f"[red]{cli_error}[/red]", title=f"❌ {title}", border_style="red")
        )
        raise typer.Exit(1) from cli_error
