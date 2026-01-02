"""TypeScript language support implementation.

This module provides the main TypeScript language support class that
implements the LanguageSupport protocol. It delegates extraction work
to specialised extractor classes.
"""

from tree_sitter import Language, Node

from waivern_source_code_analyser.languages.models import LanguageExtractionResult
from waivern_source_code_analyser.languages.typescript.callable_extractor import (
    TypeScriptCallableExtractor,
)
from waivern_source_code_analyser.languages.typescript.helpers import TS_EXTENSIONS
from waivern_source_code_analyser.languages.typescript.type_extractor import (
    TypeScriptTypeExtractor,
)


class TypeScriptLanguageSupport:
    """TypeScript language support implementation.

    Provides TypeScript and TSX parsing and extraction capabilities
    using tree-sitter-typescript. Delegates extraction work to
    specialised extractor classes for better maintainability.
    """

    def __init__(self) -> None:
        """Initialise TypeScript support with extractors."""
        self._callable_extractor = TypeScriptCallableExtractor()
        self._type_extractor = TypeScriptTypeExtractor(self._callable_extractor)

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

    def extract(self, root_node: Node, source_code: str) -> LanguageExtractionResult:
        """Extract all constructs from parsed TypeScript source code.

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
