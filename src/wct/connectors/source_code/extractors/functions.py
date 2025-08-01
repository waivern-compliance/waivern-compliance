"""Function extractor for source code analysis."""

from typing import Any

from tree_sitter import Node

from wct.connectors.source_code.extractors.base import BaseExtractor


class FunctionExtractor(BaseExtractor):
    """Extracts function definitions from source code."""

    def extract(self, node: Node, source_code: str) -> list[dict[str, Any]]:
        """Extract function information from AST.

        Args:
            node: Root AST node
            source_code: Original source code

        Returns:
            List of function information dictionaries
        """
        functions = []

        # Language-specific function node types
        function_types = self._get_function_node_types()

        for func_type in function_types:
            function_nodes = self.find_nodes_by_type(node, func_type)

            for func_node in function_nodes:
                func_info = self.extract_function_info(func_node, source_code)
                if func_info:
                    functions.append(func_info)

        return functions

    def _get_function_node_types(self) -> list[str]:
        """Get function node types for different languages.

        Returns:
            List of node types that represent functions
        """
        function_types_by_language = {
            "php": ["function_definition", "method_declaration"],
            "javascript": [
                "function_declaration",
                "function_expression",
                "arrow_function",
                "method_definition",
            ],
            "python": ["function_definition"],
            "java": ["method_declaration"],
            "cpp": ["function_definition", "function_declarator"],
            "c": ["function_definition", "function_declarator"],
            "typescript": [
                "function_declaration",
                "function_expression",
                "arrow_function",
                "method_definition",
            ],
            "go": ["function_declaration", "method_declaration"],
            "rust": ["function_item"],
            "ruby": ["method"],
        }

        return function_types_by_language.get(self.language, ["function_definition"])

    def extract_function_info(
        self, func_node: Node, source_code: str
    ) -> dict[str, Any] | None:
        """Extract information from a function node.

        Args:
            func_node: Function AST node
            source_code: Original source code

        Returns:
            Function information dictionary or None if extraction fails
        """
        try:
            func_info = {
                "name": self._get_function_name(func_node, source_code),
                "line_start": func_node.start_point[0] + 1,
                "line_end": func_node.end_point[0] + 1,
                "parameters": self._get_function_parameters(func_node, source_code),
                "return_type": self._get_return_type(func_node, source_code),
                "visibility": self._get_visibility(func_node, source_code),
                "is_static": self._is_static(func_node),
                "docstring": self._get_docstring(func_node, source_code),
            }

            # Remove None values
            return {k: v for k, v in func_info.items() if v is not None}

        except Exception:
            # Skip functions that can't be parsed
            return None

    def _get_function_name(self, func_node: Node, source_code: str) -> str:
        """Extract function name.

        Args:
            func_node: Function AST node
            source_code: Original source code

        Returns:
            Function name
        """
        if self.language == "php":
            name_node = self.find_child_by_type(func_node, "name")
        elif self.language in ["javascript", "typescript"]:
            name_node = self.find_child_by_type(func_node, "identifier")
        else:
            # Generic approach - look for identifier
            name_node = self.find_child_by_type(func_node, "identifier")

        if name_node:
            return self.get_node_text(name_node, source_code)

        # Fallback - anonymous function
        return "<anonymous>"

    def _get_function_parameters(
        self, func_node: Node, source_code: str
    ) -> list[dict[str, Any]]:
        """Extract function parameters.

        Args:
            func_node: Function AST node
            source_code: Original source code

        Returns:
            List of parameter information
        """
        parameters = []

        if self.language == "php":
            params_node = self.find_child_by_type(func_node, "formal_parameters")
        elif self.language in ["javascript", "typescript"]:
            params_node = self.find_child_by_type(func_node, "formal_parameters")
        elif self.language == "python":
            params_node = self.find_child_by_type(func_node, "parameters")
        else:
            params_node = self.find_child_by_type(
                func_node, "parameters"
            ) or self.find_child_by_type(func_node, "formal_parameters")

        if not params_node:
            return parameters

        # Extract individual parameters
        param_nodes = []
        if self.language == "php":
            param_nodes = self.find_nodes_by_type(params_node, "simple_parameter")
        elif self.language in ["javascript", "typescript"]:
            param_nodes = self.find_nodes_by_type(params_node, "identifier")
        elif self.language == "python":
            param_nodes = self.find_nodes_by_type(params_node, "identifier")

        for param_node in param_nodes:
            param_info = self._extract_parameter_info(param_node, source_code)
            if param_info:
                parameters.append(param_info)

        return parameters

    def _extract_parameter_info(
        self, param_node: Node, source_code: str
    ) -> dict[str, Any] | None:
        """Extract information from a parameter node.

        Args:
            param_node: Parameter AST node
            source_code: Original source code

        Returns:
            Parameter information dictionary
        """
        try:
            if self.language == "php":
                # PHP parameter structure: (simple_parameter (variable_name) (type) (default_value))
                var_node = self.find_child_by_type(param_node, "variable_name")
                name = (
                    self.get_node_text(var_node, source_code)
                    if var_node
                    else "<unknown>"
                )

                type_node = self.find_child_by_type(param_node, "named_type")
                param_type = (
                    self.get_node_text(type_node, source_code) if type_node else None
                )

                default_node = self.find_child_by_type(
                    param_node, "assignment_expression"
                )
                default_value = (
                    self.get_node_text(default_node, source_code)
                    if default_node
                    else None
                )

            else:
                # Generic approach
                name = self.get_node_text(param_node, source_code)
                param_type = None
                default_value = None

            return {
                "name": name,
                "type": param_type,
                "default_value": default_value,
            }

        except Exception:
            return None

    def _get_return_type(self, func_node: Node, source_code: str) -> str | None:
        """Extract function return type.

        Args:
            func_node: Function AST node
            source_code: Original source code

        Returns:
            Return type string or None
        """
        if self.language == "php":
            return_type_node = self.find_child_by_type(func_node, "return_type")
            if return_type_node:
                return self.get_node_text(return_type_node, source_code)

        return None

    def _get_visibility(self, func_node: Node, source_code: str) -> str | None:
        """Extract function visibility (public, private, protected).

        Args:
            func_node: Function AST node
            source_code: Original source code

        Returns:
            Visibility string or None
        """
        if self.language == "php":
            # Look for visibility modifiers in parent or siblings
            parent = func_node.parent
            if parent:
                for child in parent.children:
                    if child.type == "visibility_modifier":
                        return self.get_node_text(child, source_code)

        return None

    def _is_static(self, func_node: Node) -> bool:
        """Check if function is static.

        Args:
            func_node: Function AST node

        Returns:
            True if function is static
        """
        if self.language == "php":
            # Look for static modifier
            parent = func_node.parent
            if parent:
                for child in parent.children:
                    if child.type == "static_modifier":
                        return True

        return False

    def _get_docstring(self, func_node: Node, source_code: str) -> str | None:
        """Extract function docstring/comment.

        Args:
            func_node: Function AST node
            source_code: Original source code

        Returns:
            Docstring content or None
        """
        # Look for comment nodes before the function
        # This is language-specific and would need more sophisticated logic
        return None
