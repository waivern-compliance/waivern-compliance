"""TypeScript language support implementation.

This module provides the TypeScript language support class that implements
the LanguageSupport protocol for language detection and tree-sitter parsing.
"""

from tree_sitter import Language

# TypeScript file extensions
TS_EXTENSIONS = [".ts", ".tsx", ".mts", ".cts"]


class TypeScriptLanguageSupport:
    """TypeScript language support implementation.

    Provides TypeScript and TSX language detection and tree-sitter binding.
    """

    @property
    def name(self) -> str:
        """Return the canonical language name."""
        return "typescript"

    @property
    def file_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return TS_EXTENSIONS

    def get_tree_sitter_language(self) -> Language:
        """Return the tree-sitter TypeScript language binding.

        Uses TSX language to handle both .ts and .tsx files.

        The import is deferred to allow the module to be imported even when
        tree-sitter-typescript is not installed. This enables graceful degradation
        where unavailable languages are simply skipped during discovery.

        Raises:
            ImportError: If tree-sitter-typescript is not installed

        """
        import tree_sitter_typescript as tsts  # noqa: PLC0415

        return Language(tsts.language_tsx())
