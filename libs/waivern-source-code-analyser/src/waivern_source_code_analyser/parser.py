"""Source code parser using tree-sitter."""

from pathlib import Path

from tree_sitter import Language, Node, Parser
from waivern_core.errors import ParserError

from waivern_source_code_analyser.languages.registry import (
    LanguageNotFoundError,
    LanguageRegistry,
)

# Constants
_DEFAULT_LANGUAGE = "php"
_DEFAULT_ENCODING = "utf-8"


def _get_registry() -> LanguageRegistry:
    """Get the language registry with discovery performed.

    Returns:
        LanguageRegistry singleton with all languages discovered

    """
    registry = LanguageRegistry()
    registry.discover()
    return registry


def _get_tree_sitter_language(name: str) -> Language:
    """Get a tree-sitter Language object for the specified language.

    Args:
        name: Name of the programming language

    Returns:
        Tree-sitter Language object for the specified language

    Raises:
        ParserError: If the language is not supported

    """
    try:
        language_support = _get_registry().get(name)
        return language_support.get_tree_sitter_language()
    except LanguageNotFoundError as err:
        supported_languages = _get_registry().list_languages()
        raise ParserError(
            f"Language '{name}' not supported. Available: {supported_languages}"
        ) from err


def _get_parser(name: str) -> Parser:
    """Get a tree-sitter Parser object configured for the specified language.

    Args:
        name: Name of the programming language

    Returns:
        Tree-sitter Parser object configured for the specified language

    Raises:
        ParserError: If the language is not supported

    """
    parser = Parser()
    parser.language = _get_tree_sitter_language(name)
    return parser


class SourceCodeParser:
    """Parser for source code using tree-sitter.

    Uses LanguageRegistry for dynamic language support discovery.
    Languages are registered via entry points (waivern.source_code_languages).
    """

    def __init__(self, language: str = _DEFAULT_LANGUAGE) -> None:
        """Initialise the parser.

        Args:
            language: Programming language to parse (default: php)

        Raises:
            ParserError: If language is not supported or tree-sitter unavailable

        """
        self._validate_language_support(language)

        self.language = language
        self.parser = _get_parser(language)
        self.tree_sitter_language = _get_tree_sitter_language(language)

    @staticmethod
    def detect_language_from_file(file_path: Path) -> str:
        """Detect programming language from file extension.

        Args:
            file_path: Path to the source file

        Returns:
            Detected language name

        Raises:
            ParserError: If language cannot be detected

        """
        extension = file_path.suffix.lower()

        try:
            language_support = _get_registry().get_by_extension(extension)
            return language_support.name
        except LanguageNotFoundError as err:
            raise ParserError(
                f"Cannot detect language for file extension: {extension}"
            ) from err

    def parse(self, source_code: str) -> Node:
        """Parse source code string.

        Args:
            source_code: Source code to parse

        Returns:
            AST root node

        """
        tree = self.parser.parse(bytes(source_code, _DEFAULT_ENCODING))
        return tree.root_node

    @staticmethod
    def is_supported_file(file_path: Path) -> bool:
        """Check if file is supported for parsing.

        Args:
            file_path: Path to check

        Returns:
            True if file extension is supported

        """
        extension = file_path.suffix.lower()
        return extension in _get_registry().list_extensions()

    def _validate_language_support(self, language: str) -> None:
        """Validate that a language is supported.

        Args:
            language: Programming language to validate

        Raises:
            ParserError: If language is not supported

        """
        registry = _get_registry()
        if not registry.is_registered(language):
            raise ParserError(
                f"Unsupported language: {language}. "
                f"Supported languages: {registry.list_languages()}"
            )
