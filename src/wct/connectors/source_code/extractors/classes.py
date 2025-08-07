"""Class extractor for source code analysis."""

from typing import Any

from tree_sitter import Node

from wct.connectors.source_code.extractors.base import BaseExtractor
from wct.connectors.source_code.extractors.functions import FunctionExtractor


class ClassExtractor(BaseExtractor):
    """Extracts class definitions from source code."""

    def __init__(self, language: str):
        """Initialize class extractor.

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
        classes = []

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
                "line_start": class_node.start_point[0] + 1,
                "line_end": class_node.end_point[0] + 1,
                "extends": self._get_parent_class(class_node, source_code),
                "implements": self._get_implemented_interfaces(class_node, source_code),
                "properties": self._get_class_properties(class_node, source_code),
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

        return "<anonymous>"

    def _get_parent_class(self, class_node: Node, source_code: str) -> str | None:
        """Extract parent class (inheritance).

        Args:
            class_node: Class AST node
            source_code: Original source code

        Returns:
            Parent class name or None
        """
        if self.language == "php":
            extends_node = self.find_child_by_type(class_node, "base_clause")
            if extends_node:
                name_node = self.find_child_by_type(extends_node, "name")
                if name_node:
                    return self.get_node_text(name_node, source_code)

        elif self.language in ["javascript", "typescript"]:
            heritage_node = self.find_child_by_type(class_node, "class_heritage")
            if heritage_node:
                extends_node = self.find_child_by_type(heritage_node, "extends_clause")
                if extends_node:
                    name_node = self.find_child_by_type(extends_node, "identifier")
                    if name_node:
                        return self.get_node_text(name_node, source_code)

        elif self.language == "python":
            argument_list = self.find_child_by_type(class_node, "argument_list")
            if argument_list and argument_list.children:
                # First argument is typically the parent class
                first_arg = (
                    argument_list.children[1]
                    if len(argument_list.children) > 1
                    else None
                )
                if first_arg and first_arg.type == "identifier":
                    return self.get_node_text(first_arg, source_code)

        return None

    def _get_implemented_interfaces(
        self, class_node: Node, source_code: str
    ) -> list[str]:
        """Extract implemented interfaces.

        Args:
            class_node: Class AST node
            source_code: Original source code

        Returns:
            List of interface names
        """
        interfaces = []

        if self.language == "php":
            implements_node = self.find_child_by_type(
                class_node, "class_interface_clause"
            )
            if implements_node:
                name_nodes = self.find_nodes_by_type(implements_node, "name")
                for name_node in name_nodes:
                    interfaces.append(self.get_node_text(name_node, source_code))

        elif self.language in ["javascript", "typescript"]:
            heritage_node = self.find_child_by_type(class_node, "class_heritage")
            if heritage_node:
                implements_node = self.find_child_by_type(
                    heritage_node, "implements_clause"
                )
                if implements_node:
                    name_nodes = self.find_nodes_by_type(implements_node, "identifier")
                    for name_node in name_nodes:
                        interfaces.append(self.get_node_text(name_node, source_code))

        return interfaces

    def _get_class_properties(
        self, class_node: Node, source_code: str
    ) -> list[dict[str, Any]]:
        """Extract class properties/fields.

        Args:
            class_node: Class AST node
            source_code: Original source code

        Returns:
            List of property information
        """
        properties = []

        if self.language == "php":
            # Look for property declarations
            prop_nodes = self.find_nodes_by_type(class_node, "property_declaration")
            for prop_node in prop_nodes:
                prop_info = self._extract_php_property_info(prop_node, source_code)
                if prop_info:
                    properties.append(prop_info)

        elif self.language in ["javascript", "typescript"]:
            # Look for field definitions
            field_nodes = self.find_nodes_by_type(class_node, "field_definition")
            for field_node in field_nodes:
                prop_info = self._extract_js_property_info(field_node, source_code)
                if prop_info:
                    properties.append(prop_info)

        return properties

    def _extract_php_property_info(
        self, prop_node: Node, source_code: str
    ) -> dict[str, Any] | None:
        """Extract PHP property information.

        Args:
            prop_node: Property AST node
            source_code: Original source code

        Returns:
            Property information dictionary
        """
        try:
            # Get property name
            var_node = self.find_child_by_type(prop_node, "variable_name")
            if not var_node:
                return None

            name = self.get_node_text(var_node, source_code)

            # Get type
            type_node = self.find_child_by_type(prop_node, "named_type")
            prop_type = (
                self.get_node_text(type_node, source_code) if type_node else None
            )

            # Get visibility
            visibility = None
            for child in prop_node.children:
                if child.type == "visibility_modifier":
                    visibility = self.get_node_text(child, source_code)
                    break

            # Check if static
            is_static = any(
                child.type == "static_modifier" for child in prop_node.children
            )

            # Get default value
            default_value = None
            assignment_node = self.find_child_by_type(prop_node, "property_initialiser")
            if assignment_node:
                default_value = self.get_node_text(assignment_node, source_code)

            return {
                "name": name,
                "type": prop_type,
                "visibility": visibility,
                "is_static": is_static,
                "default_value": default_value,
            }

        except Exception:
            return None

    def _extract_js_property_info(
        self, field_node: Node, source_code: str
    ) -> dict[str, Any] | None:
        """Extract JavaScript/TypeScript property information.

        Args:
            field_node: Field AST node
            source_code: Original source code

        Returns:
            Property information dictionary
        """
        try:
            # Get property name
            name_node = self.find_child_by_type(field_node, "property_identifier")
            if not name_node:
                return None

            name = self.get_node_text(name_node, source_code)

            # For TypeScript, get type annotation
            prop_type = None
            type_node = self.find_child_by_type(field_node, "type_annotation")
            if type_node:
                prop_type = self.get_node_text(type_node, source_code)

            return {
                "name": name,
                "type": prop_type,
                "visibility": "public",  # Default in JS/TS
                "is_static": False,
                "default_value": None,
            }

        except Exception:
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
        methods = []

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
