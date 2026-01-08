"""PHP language support implementation.

This module provides the PHP language support class that implements
the LanguageSupport protocol for language detection and tree-sitter parsing.
"""

from tree_sitter import Language

# PHP file extensions
PHP_EXTENSIONS = [".php", ".php3", ".php4", ".php5", ".phtml"]


class PHPLanguageSupport:
    """PHP language support implementation.

    Provides PHP language detection and tree-sitter binding.
    """

    @property
    def name(self) -> str:
        """Return the canonical language name."""
        return "php"

    @property
    def file_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return PHP_EXTENSIONS

    def get_tree_sitter_language(self) -> Language:
        """Return the tree-sitter PHP language binding.

        The import is deferred to allow the module to be imported even when
        tree-sitter-php is not installed. This enables graceful degradation
        where unavailable languages are simply skipped during discovery.

        Raises:
            ImportError: If tree-sitter-php is not installed

        """
        import tree_sitter_php as tsphp  # noqa: PLC0415

        return Language(tsphp.language_php())
