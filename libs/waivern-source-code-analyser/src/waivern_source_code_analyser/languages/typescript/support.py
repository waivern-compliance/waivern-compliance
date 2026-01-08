"""TypeScript language support implementation.

This module provides the TypeScript language support class that implements
the LanguageSupport protocol for language detection.
"""

# TypeScript file extensions
TS_EXTENSIONS = [".ts", ".tsx", ".mts", ".cts"]


class TypeScriptLanguageSupport:
    """TypeScript language support implementation.

    Provides TypeScript and TSX language detection via file extension mapping.
    """

    @property
    def name(self) -> str:
        """Return the canonical language name."""
        return "typescript"

    @property
    def file_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return TS_EXTENSIONS
