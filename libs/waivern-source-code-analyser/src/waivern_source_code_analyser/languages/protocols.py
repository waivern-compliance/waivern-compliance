"""Protocols for language support plugins."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LanguageSupport(Protocol):
    """Protocol for language support plugins.

    Each language implementation must provide:
    - A canonical name (e.g., 'php', 'typescript')
    - Supported file extensions (e.g., ['.ts', '.tsx'])

    Language plugins enable file extension to language mapping for
    language detection. Raw source code content is passed through
    for pattern matching and LLM analysis.
    """

    @property
    def name(self) -> str:
        """Canonical language name (e.g., 'php', 'typescript')."""
        ...

    @property
    def file_extensions(self) -> list[str]:
        """Supported file extensions including dot (e.g., ['.ts', '.tsx'])."""
        ...
