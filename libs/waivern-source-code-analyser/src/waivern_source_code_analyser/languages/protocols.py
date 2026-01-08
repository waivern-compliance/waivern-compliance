"""Protocols for language support plugins."""

from typing import Protocol, runtime_checkable

from tree_sitter import Language


@runtime_checkable
class LanguageSupport(Protocol):
    """Protocol for language support plugins.

    Each language implementation must provide:
    - A canonical name (e.g., 'php', 'typescript')
    - Supported file extensions (e.g., ['.ts', '.tsx'])
    - A method to get the tree-sitter language binding

    Note: Structural extraction (extract method) has been removed.
    LLMs understand code structure natively from raw content.
    """

    @property
    def name(self) -> str:
        """Canonical language name (e.g., 'php', 'typescript')."""
        ...

    @property
    def file_extensions(self) -> list[str]:
        """Supported file extensions including dot (e.g., ['.ts', '.tsx'])."""
        ...

    def get_tree_sitter_language(self) -> Language:
        """Get tree-sitter Language object.

        May raise ImportError if the language's tree-sitter binding is not installed.
        """
        ...
