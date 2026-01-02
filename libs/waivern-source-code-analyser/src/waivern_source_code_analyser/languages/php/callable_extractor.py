"""PHP callable (function/method) extraction.

This module handles extraction of functions and methods from PHP source code.
"""

from tree_sitter import Node

from waivern_source_code_analyser.languages.base import (
    find_child_by_type,
    find_nodes_by_type,
    get_node_text,
    is_trivial_node,
)
from waivern_source_code_analyser.languages.models import (
    CallableModel,
    ParameterModel,
)
from waivern_source_code_analyser.languages.php.helpers import (
    FUNCTION_TYPES,
    LINE_INDEX_OFFSET,
    get_docstring,
    get_visibility,
    is_static,
)


class PHPCallableExtractor:
    """Extracts callable constructs from PHP source code.

    Handles extraction of:
    - Function definitions
    - Methods (when called from type extractor)
    """

    def extract_all(self, root_node: Node, source_code: str) -> list[CallableModel]:
        """Extract all callable constructs from source code.

        Args:
            root_node: The root node of the parsed AST
            source_code: The original source code string

        Returns:
            List of CallableModel for functions

        """
        callables: list[CallableModel] = []

        # Extract standalone functions
        for func_type in FUNCTION_TYPES:
            for func_node in find_nodes_by_type(root_node, func_type):
                callable_model = self.extract_callable(
                    func_node, source_code, kind="function"
                )
                if callable_model:
                    callables.append(callable_model)

        return callables

    def extract_callable(
        self, node: Node, source_code: str, kind: str
    ) -> CallableModel | None:
        """Extract callable information from a function/method node.

        Args:
            node: Function or method AST node
            source_code: Original source code
            kind: Type of callable ("function" or "method")

        Returns:
            CallableModel or None if extraction fails

        """
        try:
            name = self._get_callable_name(node, source_code)
            parameters = self.get_parameters(node, source_code)
            return_type = self.get_return_type(node, source_code)
            docstring_text = get_docstring(node, source_code)
            visibility_mod = (
                get_visibility(node, source_code) if kind == "method" else None
            )
            is_static_method = is_static(node) if kind == "method" else False

            return CallableModel(
                name=name,
                kind=kind,
                line_start=node.start_point[0] + LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + LINE_INDEX_OFFSET,
                parameters=parameters,
                return_type=return_type,
                visibility=visibility_mod,
                is_static=is_static_method,
                docstring=docstring_text,
            )
        except Exception:
            return None

    def _get_callable_name(self, node: Node, source_code: str) -> str:
        """Extract function/method name."""
        name_node = find_child_by_type(node, "name")
        if name_node:
            return get_node_text(name_node, source_code)
        return "<anonymous>"

    def get_parameters(self, node: Node, source_code: str) -> list[ParameterModel]:
        """Extract function/method parameters.

        This is a public method to allow reuse by the type extractor
        for method extraction.

        Args:
            node: The function/method AST node
            source_code: The original source code

        Returns:
            List of ParameterModel for the function's parameters

        """
        parameters: list[ParameterModel] = []

        params_node = find_child_by_type(node, "formal_parameters")
        if not params_node:
            return parameters

        for param_node in find_nodes_by_type(params_node, "simple_parameter"):
            param = self._extract_parameter(param_node, source_code)
            if param:
                parameters.append(param)

        return parameters

    def _extract_parameter(self, node: Node, source_code: str) -> ParameterModel | None:
        """Extract parameter information."""
        try:
            # Get variable name
            var_node = find_child_by_type(node, "variable_name")
            name = get_node_text(var_node, source_code) if var_node else "<unknown>"

            # Get type
            type_node = find_child_by_type(node, "named_type")
            if not type_node:
                type_node = find_child_by_type(node, "optional_type")
            if not type_node:
                type_node = find_child_by_type(node, "primitive_type")
            param_type = get_node_text(type_node, source_code) if type_node else None

            # Get default value
            default_value = None
            for child in node.children:
                if child.type == "=":
                    # Next non-trivial child is the default value
                    idx = node.children.index(child)
                    for next_child in node.children[idx + 1 :]:
                        if not is_trivial_node(next_child):
                            default_value = get_node_text(next_child, source_code)
                            break
                    break

            return ParameterModel(
                name=name,
                type=param_type,
                default_value=default_value,
            )
        except Exception:
            return None

    def get_return_type(self, node: Node, source_code: str) -> str | None:
        """Extract function/method return type.

        This is a public method to allow reuse by the type extractor
        for method extraction.

        Args:
            node: The function/method AST node
            source_code: The original source code

        Returns:
            The return type annotation or None

        """
        # Look for return type after colon
        for i, child in enumerate(node.children):
            if child.type == ":":
                # Next child is the return type
                for next_child in node.children[i + 1 :]:
                    if next_child.type in [
                        "named_type",
                        "primitive_type",
                        "optional_type",
                    ]:
                        return get_node_text(next_child, source_code)
        return None
