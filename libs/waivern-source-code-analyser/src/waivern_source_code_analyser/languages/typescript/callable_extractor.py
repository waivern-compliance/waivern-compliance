"""TypeScript callable (function/method) extraction.

This module handles extraction of functions, arrow functions, and methods
from TypeScript source code.
"""

import logging

from tree_sitter import Node

logger = logging.getLogger(__name__)

from waivern_source_code_analyser.languages.base import (
    find_child_by_type,
    find_children_by_type,
    find_nodes_by_type,
    get_node_text,
)
from waivern_source_code_analyser.languages.models import (
    CallableModel,
    ParameterModel,
)
from waivern_source_code_analyser.languages.typescript.helpers import (
    ARROW_FUNCTION_TYPE,
    FUNCTION_TYPES,
    LINE_INDEX_OFFSET,
    get_docstring,
    get_visibility,
    is_async,
    is_static,
)


class TypeScriptCallableExtractor:
    """Extracts callable constructs from TypeScript source code.

    Handles extraction of:
    - Function declarations
    - Arrow functions assigned to variables
    - Methods (when called from type extractor)
    """

    def extract_all(self, root_node: Node, source_code: str) -> list[CallableModel]:
        """Extract all callable constructs from source code.

        Args:
            root_node: The root node of the parsed AST
            source_code: The original source code string

        Returns:
            List of CallableModel for functions and arrow functions

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

        # Extract top-level arrow functions (assigned to variables)
        for var_node in find_nodes_by_type(root_node, "lexical_declaration"):
            callables.extend(self._extract_arrow_functions(var_node, source_code))

        return callables

    def extract_callable(
        self, node: Node, source_code: str, kind: str
    ) -> CallableModel | None:
        """Extract callable information from a function/method node.

        Args:
            node: Function or method AST node
            source_code: Original source code
            kind: Type of callable ("function", "method", "arrow_function")

        Returns:
            CallableModel or None if extraction fails

        """
        try:
            name = self._get_callable_name(node, source_code)
            parameters = self.get_parameters(node, source_code)
            return_type = self.get_return_type(node, source_code)
            docstring_text = get_docstring(node, source_code)
            is_async_func = is_async(node)
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
                is_async=is_async_func,
                docstring=docstring_text,
            )
        except Exception:
            logger.debug(
                "Failed to extract TypeScript callable at line %d",
                node.start_point[0] + LINE_INDEX_OFFSET,
                exc_info=True,
            )
            return None

    def _extract_arrow_functions(
        self, var_node: Node, source_code: str
    ) -> list[CallableModel]:
        """Extract arrow functions from variable declarations.

        Args:
            var_node: Variable declaration node (lexical_declaration)
            source_code: Original source code

        Returns:
            List of CallableModel for arrow functions found

        """
        results: list[CallableModel] = []

        for declarator in find_children_by_type(var_node, "variable_declarator"):
            arrow_callable = self._extract_single_arrow_function(
                declarator, var_node, source_code
            )
            if arrow_callable:
                results.append(arrow_callable)

        return results

    def _extract_single_arrow_function(
        self, declarator: Node, var_node: Node, source_code: str
    ) -> CallableModel | None:
        """Extract a single arrow function from a variable declarator.

        Args:
            declarator: Variable declarator node
            var_node: Parent variable declaration node
            source_code: Original source code

        Returns:
            CallableModel or None if not an arrow function or extraction fails

        """
        arrow_node = find_child_by_type(declarator, ARROW_FUNCTION_TYPE)
        if not arrow_node:
            return None

        try:
            name_node = find_child_by_type(declarator, "identifier")
            name = get_node_text(name_node, source_code) if name_node else "<anonymous>"

            parameters = self.get_parameters(arrow_node, source_code)
            return_type = self.get_return_type(arrow_node, source_code)
            docstring_text = get_docstring(var_node, source_code)
            is_async_func = is_async(arrow_node)

            return CallableModel(
                name=name,
                kind="arrow_function",
                line_start=var_node.start_point[0] + LINE_INDEX_OFFSET,
                line_end=var_node.end_point[0] + LINE_INDEX_OFFSET,
                parameters=parameters,
                return_type=return_type,
                is_async=is_async_func,
                docstring=docstring_text,
            )
        except Exception:
            logger.debug(
                "Failed to extract TypeScript arrow function at line %d",
                var_node.start_point[0] + LINE_INDEX_OFFSET,
                exc_info=True,
            )
            return None

    def _get_callable_name(self, node: Node, source_code: str) -> str:
        """Extract function/method name."""
        # For function declarations
        name_node = find_child_by_type(node, "identifier")
        if name_node:
            return get_node_text(name_node, source_code)

        # For method definitions, name might be property_identifier
        name_node = find_child_by_type(node, "property_identifier")
        if name_node:
            return get_node_text(name_node, source_code)

        return "<anonymous>"

    def get_parameters(self, node: Node, source_code: str) -> list[ParameterModel]:
        """Extract function/method parameters.

        This is a public method to allow reuse by the type extractor
        for interface method signatures.

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

        for param_node in params_node.children:
            if param_node.type in [
                "required_parameter",
                "optional_parameter",
                "rest_parameter",
            ]:
                param = self._extract_parameter(param_node, source_code)
                if param:
                    parameters.append(param)

        return parameters

    def _extract_parameter(self, node: Node, source_code: str) -> ParameterModel | None:
        """Extract parameter information."""
        try:
            # Get parameter name
            name_node = find_child_by_type(node, "identifier")
            if not name_node:
                # Rest parameter uses rest_pattern
                rest_node = find_child_by_type(node, "rest_pattern")
                if rest_node:
                    name_node = find_child_by_type(rest_node, "identifier")
            name = get_node_text(name_node, source_code) if name_node else "<unknown>"

            # For rest parameters, prefix with ...
            if node.type == "rest_parameter":
                name = f"...{name}"

            # Get type annotation
            param_type = None
            type_annotation = find_child_by_type(node, "type_annotation")
            if type_annotation and len(type_annotation.children) > 1:
                # Type is after the colon
                param_type = get_node_text(type_annotation.children[-1], source_code)

            # Get default value
            default_value = None
            for i, child in enumerate(node.children):
                if child.type == "=":
                    if i + 1 < len(node.children):
                        default_value = get_node_text(node.children[i + 1], source_code)
                    break

            return ParameterModel(
                name=name,
                type=param_type,
                default_value=default_value,
            )
        except Exception:
            logger.debug(
                "Failed to extract TypeScript parameter at line %d",
                node.start_point[0] + LINE_INDEX_OFFSET,
                exc_info=True,
            )
            return None

    def get_return_type(self, node: Node, source_code: str) -> str | None:
        """Extract function/method return type.

        This is a public method to allow reuse by the type extractor
        for interface method signatures.

        Args:
            node: The function/method AST node
            source_code: The original source code

        Returns:
            The return type annotation or None

        """
        # Look for return_type node (type annotation after parameters)
        for child in node.children:
            if child.type == "type_annotation":
                if len(child.children) > 1:
                    return get_node_text(child.children[-1], source_code)
        return None
