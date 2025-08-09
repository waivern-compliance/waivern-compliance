"""Source code parser using tree-sitter."""

from pathlib import Path

import tree_sitter_php
from tree_sitter import Language, Node, Parser

from wct.connectors.base import ConnectorConfigError

# Language registry for individual language packages
LANGUAGE_REGISTRY = {}

LANGUAGE_REGISTRY["php"] = Language(tree_sitter_php.language_php())


def get_language(name: str) -> Language:
    """Get a tree-sitter Language object for the specified language.

    Args:
        name: Name of the programming language

    Returns:
        Tree-sitter Language object for the specified language

    Raises:
        ConnectorConfigError: If the language is not supported
    """
    if name not in LANGUAGE_REGISTRY:
        raise ConnectorConfigError(
            f"Language '{name}' not supported. Available: {list(LANGUAGE_REGISTRY.keys())}"
        )
    return LANGUAGE_REGISTRY[name]


def get_parser(name: str) -> Parser:
    """Get a tree-sitter Parser object configured for the specified language.

    Args:
        name: Name of the programming language

    Returns:
        Tree-sitter Parser object configured for the specified language

    Raises:
        ConnectorConfigError: If the language is not supported
    """
    parser = Parser()
    parser.language = get_language(name)
    return parser


class SourceCodeParser:
    """Parser for source code using tree-sitter."""

    # Supported languages and their file extensions
    SUPPORTED_LANGUAGES = {
        "php": [".php", ".php3", ".php4", ".php5", ".phtml"],
        "javascript": [".js", ".jsx", ".mjs", ".cjs"],
        "python": [".py", ".pyx", ".pyi"],
        "java": [".java"],
        "cpp": [".cpp", ".cc", ".cxx", ".c++", ".hpp", ".h", ".hxx"],
        "c": [".c", ".h"],
        "typescript": [".ts", ".tsx"],
        "go": [".go"],
        "rust": [".rs"],
        "ruby": [".rb"],
    }

    def __init__(self, language: str = "php"):
        """Initialise the parser.

        Args:
            language: Programming language to parse (default: php)

        Raises:
            ConnectorConfigError: If language is not supported or tree-sitter unavailable
        """
        if language not in self.SUPPORTED_LANGUAGES:
            raise ConnectorConfigError(
                f"Unsupported language: {language}. "
                f"Supported languages: {list(self.SUPPORTED_LANGUAGES.keys())}"
            )

        self.language = language
        self.parser = get_parser(language)
        self.tree_sitter_language = get_language(language)

    def detect_language_from_file(self, file_path: Path) -> str:
        """Detect programming language from file extension.

        Args:
            file_path: Path to the source file

        Returns:
            Detected language name

        Raises:
            ConnectorConfigError: If language cannot be detected
        """
        extension = file_path.suffix.lower()

        for language, extensions in self.SUPPORTED_LANGUAGES.items():
            if extension in extensions:
                return language

        raise ConnectorConfigError(
            f"Cannot detect language for file extension: {extension}"
        )

    def parse_file(self, file_path: Path) -> tuple[Node, str]:
        """Parse a source code file.

        Args:
            file_path: Path to the source file

        Returns:
            Tuple of (AST root node, source code content)

        Raises:
            ConnectorConfigError: If file cannot be parsed
        """
        try:
            source_code = file_path.read_text(encoding="utf-8")
            return self.parse_code(source_code), source_code
        except UnicodeDecodeError as e:
            raise ConnectorConfigError(f"Cannot decode file {file_path}: {e}") from e
        except Exception as e:
            raise ConnectorConfigError(f"Cannot parse file {file_path}: {e}") from e

    def parse_code(self, source_code: str) -> Node:
        """Parse source code string.

        Args:
            source_code: Source code to parse

        Returns:
            AST root node
        """
        tree = self.parser.parse(bytes(source_code, "utf-8"))
        return tree.root_node

    def is_supported_file(self, file_path: Path) -> bool:
        """Check if file is supported for parsing.

        Args:
            file_path: Path to check

        Returns:
            True if file extension is supported
        """
        extension = file_path.suffix.lower()
        return any(
            extension in extensions for extensions in self.SUPPORTED_LANGUAGES.values()
        )

    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """Get all supported file extensions.

        Returns:
            List of supported file extensions
        """
        extensions = []
        for exts in cls.SUPPORTED_LANGUAGES.values():
            extensions.extend(exts)
        return sorted(set(extensions))
