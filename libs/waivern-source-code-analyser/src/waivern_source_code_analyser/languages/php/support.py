"""PHP language support implementation.

This module provides the main PHP language support class that
implements the LanguageSupport protocol. It delegates extraction work
to specialised extractor classes.
"""

from tree_sitter import Language, Node

from waivern_source_code_analyser.languages.models import LanguageExtractionResult
from waivern_source_code_analyser.languages.php.callable_extractor import (
    PHPCallableExtractor,
)
from waivern_source_code_analyser.languages.php.helpers import PHP_EXTENSIONS
from waivern_source_code_analyser.languages.php.type_extractor import (
    PHPTypeExtractor,
)


class PHPLanguageSupport:
    """PHP language support implementation.

    Provides PHP parsing and extraction capabilities using tree-sitter-php.
    Delegates extraction work to specialised extractor classes for better
    maintainability.
    """

    def __init__(self) -> None:
        """Initialise PHP support with extractors."""
        self._callable_extractor = PHPCallableExtractor()
        self._type_extractor = PHPTypeExtractor(self._callable_extractor)

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

    def extract(self, root_node: Node, source_code: str) -> LanguageExtractionResult:
        """Extract all constructs from parsed PHP source code.

        Args:
            root_node: The root node of the parsed AST
            source_code: The original source code string

        Returns:
            LanguageExtractionResult containing callables and type definitions

        """
        callables = self._callable_extractor.extract_all(root_node, source_code)
        type_definitions = self._type_extractor.extract_all(root_node, source_code)

        return LanguageExtractionResult(
            callables=callables,
            type_definitions=type_definitions,
        )
