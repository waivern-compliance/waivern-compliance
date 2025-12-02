"""Source code parser using tree-sitter."""

from pathlib import Path

import tree_sitter_php
from tree_sitter import Language, Node, Parser
from waivern_core.errors import ParserError

# Language registry for individual language packages
_LANGUAGE_REGISTRY: dict[str, Language] = {}
_LANGUAGE_REGISTRY["php"] = Language(tree_sitter_php.language_php())


def _get_tree_sitter_language(name: str) -> Language:
    """Get a tree-sitter Language object for the specified language.

    Args:
        name: Name of the programming language

    Returns:
        Tree-sitter Language object for the specified language

    Raises:
        ParserError: If the language is not supported

    """
    if name not in _LANGUAGE_REGISTRY:
        supported_languages: list[str] = list(_LANGUAGE_REGISTRY.keys())
        raise ParserError(
            f"Language '{name}' not supported. Available: {supported_languages}"
        )
    return _LANGUAGE_REGISTRY[name]


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


# Constants
_DEFAULT_LANGUAGE = "php"
_DEFAULT_ENCODING = "utf-8"


class SourceCodeParser:
    """Parser for source code using tree-sitter."""

    # Supported languages and their file extensions
    _SUPPORTED_LANGUAGES = {
        "php": [".php", ".php3", ".php4", ".php5", ".phtml"],
        # TODO: Add support to the below languages
        # "javascript": [".js", ".jsx", ".mjs", ".cjs"],
        # "python": [".py", ".pyx", ".pyi"],
        # "java": [".java"],
        # "cpp": [".cpp", ".cc", ".cxx", ".c++", ".hpp", ".h", ".hxx"],
        # "c": [".c", ".h"],
        # "typescript": [".ts", ".tsx"],
        # "go": [".go"],
        # "rust": [".rs"],
        # "ruby": [".rb"],
    }

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

        for language, extensions in SourceCodeParser._SUPPORTED_LANGUAGES.items():
            if extension in extensions:
                return language

        raise ParserError(f"Cannot detect language for file extension: {extension}")

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
        return any(
            extension in extensions
            for extensions in SourceCodeParser._SUPPORTED_LANGUAGES.values()
        )

    def _validate_language_support(self, language: str) -> None:
        """Validate that a language is supported.

        Args:
            language: Programming language to validate

        Raises:
            ParserError: If language is not supported

        """
        if language not in self._SUPPORTED_LANGUAGES:
            raise ParserError(
                f"Unsupported language: {language}. "
                f"Supported languages: {list(self._SUPPORTED_LANGUAGES.keys())}"
            )
