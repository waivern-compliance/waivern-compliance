"""Protocols for language support plugins."""

from typing import Protocol, runtime_checkable

from tree_sitter import Language, Node

from waivern_source_code_analyser.languages.models import LanguageExtractionResult


@runtime_checkable
class LanguageSupport(Protocol):
    """Protocol for language support plugins.

    Each language implementation must provide:
    - A canonical name (e.g., 'php', 'typescript')
    - Supported file extensions (e.g., ['.ts', '.tsx'])
    - A method to get the tree-sitter language binding
    - An extract method to parse source code and return results
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

    def extract(self, root_node: Node, source_code: str) -> LanguageExtractionResult:
        """Extract all constructs from parsed source code.

        Each language implementation decides what to extract:
        - PHP: functions, classes
        - TypeScript: functions, classes, interfaces, enums, type aliases
        - Rust: functions, structs, traits, enums

        Args:
            root_node: The root node of the parsed AST
            source_code: The original source code string

        Returns:
            LanguageExtractionResult containing callables and type definitions

        """
        ...
