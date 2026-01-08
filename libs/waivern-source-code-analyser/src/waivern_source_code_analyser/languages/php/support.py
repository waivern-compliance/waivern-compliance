"""PHP language support implementation.

This module provides the PHP language support class that implements
the LanguageSupport protocol for language detection.
"""

# PHP file extensions
PHP_EXTENSIONS = [".php", ".php3", ".php4", ".php5", ".phtml"]


class PHPLanguageSupport:
    """PHP language support implementation.

    Provides PHP language detection via file extension mapping.
    """

    @property
    def name(self) -> str:
        """Return the canonical language name."""
        return "php"

    @property
    def file_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return PHP_EXTENSIONS
