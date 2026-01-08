"""JavaScript language support implementation.

This module provides the JavaScript language support class that implements
the LanguageSupport protocol for language detection.
"""

# JavaScript file extensions
JS_EXTENSIONS = [".js", ".jsx", ".mjs", ".cjs"]


class JavaScriptLanguageSupport:
    """JavaScript language support implementation.

    Provides JavaScript and JSX language detection via file extension mapping.
    """

    @property
    def name(self) -> str:
        """Return the canonical language name."""
        return "javascript"

    @property
    def file_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return JS_EXTENSIONS
