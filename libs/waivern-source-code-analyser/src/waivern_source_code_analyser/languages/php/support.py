"""PHP language support implementation."""

import tree_sitter_php as tsphp
from tree_sitter import Language, Node

from waivern_source_code_analyser.languages.base import (
    find_child_by_type,
    find_children_by_type,
    find_nodes_by_type,
    get_node_text,
    is_trivial_node,
)
from waivern_source_code_analyser.languages.models import (
    CallableModel,
    LanguageExtractionResult,
    ParameterModel,
    TypeDefinitionModel,
)

# PHP file extensions
_PHP_EXTENSIONS = [".php", ".php3", ".php4", ".php5", ".phtml"]

# PHP AST node types
_FUNCTION_TYPES = ["function_definition"]
_METHOD_TYPE = "method_declaration"
_CLASS_TYPE = "class_declaration"

# Line index offset (tree-sitter uses 0-based, we want 1-based)
_LINE_INDEX_OFFSET = 1


class PHPLanguageSupport:
    """PHP language support implementation.

    Provides PHP parsing and extraction capabilities using tree-sitter-php.
    """

    @property
    def name(self) -> str:
        """Return the canonical language name."""
        return "php"

    @property
    def file_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return _PHP_EXTENSIONS

    def get_tree_sitter_language(self) -> Language:
        """Return the tree-sitter PHP language binding."""
        return Language(tsphp.language_php())

    def extract(self, root_node: Node, source_code: str) -> LanguageExtractionResult:
        """Extract all constructs from parsed PHP source code.

        Args:
            root_node: The root node of the parsed AST
            source_code: The original source code string

        Returns:
            LanguageExtractionResult containing callables and type definitions

        """
        callables: list[CallableModel] = []
        type_definitions: list[TypeDefinitionModel] = []

        # Extract standalone functions
        for func_type in _FUNCTION_TYPES:
            for func_node in find_nodes_by_type(root_node, func_type):
                callable_model = self._extract_callable(
                    func_node, source_code, kind="function"
                )
                if callable_model:
                    callables.append(callable_model)

        # Extract classes
        for class_node in find_nodes_by_type(root_node, _CLASS_TYPE):
            type_def = self._extract_class(class_node, source_code)
            if type_def:
                type_definitions.append(type_def)

        return LanguageExtractionResult(
            callables=callables,
            type_definitions=type_definitions,
        )

    def _extract_callable(
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
            parameters = self._get_parameters(node, source_code)
            return_type = self._get_return_type(node, source_code)
            docstring = self._get_docstring(node, source_code)
            visibility = self._get_visibility(node) if kind == "method" else None
            is_static = self._is_static(node) if kind == "method" else False

            return CallableModel(
                name=name,
                kind=kind,
                line_start=node.start_point[0] + _LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + _LINE_INDEX_OFFSET,
                parameters=parameters,
                return_type=return_type,
                visibility=visibility,
                is_static=is_static,
                docstring=docstring,
            )
        except Exception:
            return None

    def _extract_class(
        self, node: Node, source_code: str
    ) -> TypeDefinitionModel | None:
        """Extract class information from a class declaration node.

        Args:
            node: Class declaration AST node
            source_code: Original source code

        Returns:
            TypeDefinitionModel or None if extraction fails

        """
        try:
            name = self._get_class_name(node, source_code)
            docstring = self._get_docstring(node, source_code)
            extends = self._get_extends(node, source_code)
            implements = self._get_implements(node, source_code)
            methods = self._get_class_methods(node, source_code)

            return TypeDefinitionModel(
                name=name,
                kind="class",
                line_start=node.start_point[0] + _LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + _LINE_INDEX_OFFSET,
                extends=extends,
                implements=implements,
                methods=methods,
                docstring=docstring,
            )
        except Exception:
            return None

    def _get_callable_name(self, node: Node, source_code: str) -> str:
        """Extract function/method name."""
        name_node = find_child_by_type(node, "name")
        if name_node:
            return get_node_text(name_node, source_code)
        return "<anonymous>"

    def _get_class_name(self, node: Node, source_code: str) -> str:
        """Extract class name."""
        name_node = find_child_by_type(node, "name")
        if name_node:
            return get_node_text(name_node, source_code)
        return "<anonymous>"

    def _get_parameters(self, node: Node, source_code: str) -> list[ParameterModel]:
        """Extract function/method parameters."""
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

    def _get_return_type(self, node: Node, source_code: str) -> str | None:
        """Extract function/method return type."""
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

    def _get_docstring(self, node: Node, source_code: str) -> str | None:
        """Extract preceding docstring/comment."""
        parent = node.parent
        if not parent:
            return None

        # Find node's position in parent's children
        node_index = None
        for i, child in enumerate(parent.children):
            if child == node:
                node_index = i
                break

        if node_index is None or node_index == 0:
            return None

        # Look backwards for the nearest comment
        for i in range(node_index - 1, -1, -1):
            child = parent.children[i]
            if child.type == "comment":
                return get_node_text(child, source_code).strip()
            elif not is_trivial_node(child):
                break

        return None

    def _get_visibility(self, node: Node) -> str | None:
        """Extract method visibility modifier."""
        for child in node.children:
            if child.type == "visibility_modifier":
                # The text of visibility_modifier is 'public', 'private', or 'protected'
                for grandchild in child.children:
                    if grandchild.type in ["public", "private", "protected"]:
                        return grandchild.type
                # Fallback - check the node text directly
                if child.child_count == 0:
                    # It might be a terminal node
                    return None
        return None

    def _is_static(self, node: Node) -> bool:
        """Check if method has static modifier."""
        for child in node.children:
            if child.type == "static_modifier":
                return True
        return False

    def _get_extends(self, node: Node, source_code: str) -> str | None:
        """Extract parent class name."""
        extends_clause = find_child_by_type(node, "base_clause")
        if extends_clause:
            name_node = find_child_by_type(extends_clause, "name")
            if name_node:
                return get_node_text(name_node, source_code)
        return None

    def _get_implements(self, node: Node, source_code: str) -> list[str]:
        """Extract implemented interface names."""
        implements: list[str] = []
        implements_clause = find_child_by_type(node, "class_interface_clause")
        if implements_clause:
            for name_node in find_children_by_type(implements_clause, "name"):
                implements.append(get_node_text(name_node, source_code))
        return implements

    def _get_class_methods(self, node: Node, source_code: str) -> list[CallableModel]:
        """Extract class methods."""
        methods: list[CallableModel] = []
        for method_node in find_nodes_by_type(node, _METHOD_TYPE):
            method = self._extract_callable(method_node, source_code, kind="method")
            if method:
                methods.append(method)
        return methods
