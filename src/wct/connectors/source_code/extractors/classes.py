"""Class extractor for source code analysis."""

from typing import Any

from tree_sitter import Node

from wct.connectors.source_code.extractors.base import BaseExtractor
from wct.connectors.source_code.extractors.functions import FunctionExtractor

# Constants
_ANONYMOUS_CLASS_NAME = "<anonymous>"
_LINE_INDEX_OFFSET = 1


class ClassExtractor(BaseExtractor):
    """Extracts class definitions from source code."""

    def __init__(self, language: str):
        """Initialise class extractor.

        Args:
            language: Programming language

        """
        super().__init__(language)
        self.function_extractor = FunctionExtractor(language)

    def extract(self, node: Node, source_code: str) -> list[dict[str, Any]]:
        """Extract class information from AST.

        Args:
            node: Root AST node
            source_code: Original source code

        Returns:
            List of class information dictionaries

        """
        classes: list[dict[str, Any]] = []

        # Language-specific class node types
        class_types = self._get_class_node_types()

        for class_type in class_types:
            class_nodes = self.find_nodes_by_type(node, class_type)

            for class_node in class_nodes:
                class_info = self._extract_class_info(class_node, source_code)
                if class_info:
                    classes.append(class_info)

        return classes

    def _get_class_node_types(self) -> list[str]:
        """Get class node types for different languages.

        Returns:
            List of node types that represent classes

        """
        class_types_by_language = {
            "php": ["class_declaration"],
            "javascript": ["class_declaration"],
            "python": ["class_definition"],
            "java": ["class_declaration"],
            "cpp": ["class_specifier"],
            "c": ["struct_specifier"],
            "typescript": ["class_declaration"],
            "go": ["type_declaration"],  # struct types
            "rust": ["struct_item", "enum_item", "impl_item"],
            "ruby": ["class"],
        }

        return class_types_by_language.get(self.language, ["class_declaration"])

    def _extract_class_info(
        self, class_node: Node, source_code: str
    ) -> dict[str, Any] | None:
        """Extract information from a class node.

        Args:
            class_node: Class AST node
            source_code: Original source code

        Returns:
            Class information dictionary or None if extraction fails

        """
        try:
            class_info = {
                "name": self._get_class_name(class_node, source_code),
                "line_start": class_node.start_point[0] + _LINE_INDEX_OFFSET,
                "line_end": class_node.end_point[0] + _LINE_INDEX_OFFSET,
                "docstring": self._get_class_docstring(class_node, source_code),
                "methods": self._get_class_methods(class_node, source_code),
            }

            # Remove None/empty values
            return {k: v for k, v in class_info.items() if v}

        except Exception:
            # Skip classes that can't be parsed
            return None

    def _get_class_name(self, class_node: Node, source_code: str) -> str:
        """Extract class name.

        Args:
            class_node: Class AST node
            source_code: Original source code

        Returns:
            Class name

        """
        if self.language == "php":
            name_node = self.find_child_by_type(class_node, "name")
        elif self.language in ["javascript", "typescript", "java"]:
            name_node = self.find_child_by_type(class_node, "identifier")
        elif self.language == "python":
            name_node = self.find_child_by_type(class_node, "identifier")
        else:
            name_node = self.find_child_by_type(class_node, "identifier")

        if name_node:
            return self.get_node_text(name_node, source_code)

        return _ANONYMOUS_CLASS_NAME

    def _get_class_docstring(self, class_node: Node, source_code: str) -> str | None:
        """Extract class docstring/comment using tree-sitter comment nodes.

        Args:
            class_node: Class AST node
            source_code: Original source code

        Returns:
            Docstring content or None

        """
        # Look for comment node immediately preceding the class
        parent = class_node.parent
        if not parent:
            return None

        # Find class's position in parent's children
        class_index = None
        for i, child in enumerate(parent.children):
            if child == class_node:
                class_index = i
                break

        if class_index is None or class_index == 0:
            return None

        # Look backwards for the nearest comment node
        for i in range(class_index - 1, -1, -1):
            child = parent.children[i]
            if child.type == "comment":
                return self.get_node_text(child, source_code).strip()
            elif not self._is_whitespace_or_trivial(child):
                # Stop if we encounter non-trivial content
                break

        return None

    def _get_class_methods(
        self, class_node: Node, source_code: str
    ) -> list[dict[str, Any]]:
        """Extract class methods.

        Args:
            class_node: Class AST node
            source_code: Original source code

        Returns:
            List of method information

        """
        methods: list[dict[str, Any]] = []

        # Use function extractor to get methods within the class
        method_nodes = []

        if self.language == "php":
            method_nodes = self.find_nodes_by_type(class_node, "method_declaration")
        elif self.language in ["javascript", "typescript"]:
            method_nodes = self.find_nodes_by_type(class_node, "method_definition")
        elif self.language == "python":
            method_nodes = self.find_nodes_by_type(class_node, "function_definition")

        for method_node in method_nodes:
            method_info = self.function_extractor.extract_function_info(
                method_node, source_code
            )
            if method_info:
                methods.append(method_info)

        return methods
