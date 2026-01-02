"""TypeScript language support implementation."""

from collections.abc import Callable

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
    MemberModel,
    ParameterModel,
    TypeDefinitionModel,
)

# TypeScript file extensions
_TS_EXTENSIONS = [".ts", ".tsx", ".mts", ".cts"]

# TypeScript AST node types
_FUNCTION_TYPES = ["function_declaration"]
_ARROW_FUNCTION_TYPE = "arrow_function"
_METHOD_TYPE = "method_definition"
_CLASS_TYPES = ["class_declaration", "abstract_class_declaration"]
_INTERFACE_TYPE = "interface_declaration"
_TYPE_ALIAS_TYPE = "type_alias_declaration"
_ENUM_TYPE = "enum_declaration"

# Line index offset (tree-sitter uses 0-based, we want 1-based)
_LINE_INDEX_OFFSET = 1


class TypeScriptLanguageSupport:
    """TypeScript language support implementation.

    Provides TypeScript and TSX parsing and extraction capabilities
    using tree-sitter-typescript.
    """

    @property
    def name(self) -> str:
        """Return the canonical language name."""
        return "typescript"

    @property
    def file_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return _TS_EXTENSIONS

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
        callables = self._extract_all_callables(root_node, source_code)
        type_definitions = self._extract_all_type_definitions(root_node, source_code)

        return LanguageExtractionResult(
            callables=callables,
            type_definitions=type_definitions,
        )

    def _extract_all_callables(
        self, root_node: Node, source_code: str
    ) -> list[CallableModel]:
        """Extract all callable constructs from source code.

        Args:
            root_node: The root node of the parsed AST
            source_code: The original source code string

        Returns:
            List of CallableModel for functions and arrow functions

        """
        callables: list[CallableModel] = []

        # Extract standalone functions
        for func_type in _FUNCTION_TYPES:
            for func_node in find_nodes_by_type(root_node, func_type):
                callable_model = self._extract_callable(
                    func_node, source_code, kind="function"
                )
                if callable_model:
                    callables.append(callable_model)

        # Extract top-level arrow functions (assigned to variables)
        for var_node in find_nodes_by_type(root_node, "lexical_declaration"):
            callables.extend(self._extract_arrow_functions(var_node, source_code))

        return callables

    def _extract_all_type_definitions(
        self, root_node: Node, source_code: str
    ) -> list[TypeDefinitionModel]:
        """Extract all type definitions from source code.

        Args:
            root_node: The root node of the parsed AST
            source_code: The original source code string

        Returns:
            List of TypeDefinitionModel for classes, interfaces, enums, and type aliases

        """
        type_definitions: list[TypeDefinitionModel] = []

        # Extract classes (both regular and abstract)
        for class_type in _CLASS_TYPES:
            for node in find_nodes_by_type(root_node, class_type):
                type_def = self._extract_class(node, source_code)
                if type_def:
                    type_definitions.append(type_def)

        # Map of node type to extractor method for other types
        extractors: list[
            tuple[str, Callable[[Node, str], TypeDefinitionModel | None]]
        ] = [
            (_INTERFACE_TYPE, self._extract_interface),
            (_TYPE_ALIAS_TYPE, self._extract_type_alias),
            (_ENUM_TYPE, self._extract_enum),
        ]

        for node_type, extractor in extractors:
            for node in find_nodes_by_type(root_node, node_type):
                type_def = extractor(node, source_code)
                if type_def:
                    type_definitions.append(type_def)

        return type_definitions

    def _extract_callable(
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
            parameters = self._get_parameters(node, source_code)
            return_type = self._get_return_type(node, source_code)
            docstring = self._get_docstring(node, source_code)
            is_async = self._is_async(node)
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
                is_async=is_async,
                docstring=docstring,
            )
        except Exception:
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
        arrow_node = find_child_by_type(declarator, _ARROW_FUNCTION_TYPE)
        if not arrow_node:
            return None

        try:
            name_node = find_child_by_type(declarator, "identifier")
            name = get_node_text(name_node, source_code) if name_node else "<anonymous>"

            parameters = self._get_parameters(arrow_node, source_code)
            return_type = self._get_return_type(arrow_node, source_code)
            docstring = self._get_docstring(var_node, source_code)
            is_async = self._is_async(arrow_node)

            return CallableModel(
                name=name,
                kind="arrow_function",
                line_start=var_node.start_point[0] + _LINE_INDEX_OFFSET,
                line_end=var_node.end_point[0] + _LINE_INDEX_OFFSET,
                parameters=parameters,
                return_type=return_type,
                is_async=is_async,
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
            name = self._get_type_name(node, source_code)
            docstring = self._get_docstring(node, source_code)
            extends = self._get_extends(node, source_code)
            implements = self._get_implements(node, source_code)
            members = self._get_class_members(node, source_code)
            methods = self._get_class_methods(node, source_code)

            return TypeDefinitionModel(
                name=name,
                kind="class",
                line_start=node.start_point[0] + _LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + _LINE_INDEX_OFFSET,
                extends=extends,
                implements=implements,
                members=members,
                methods=methods,
                docstring=docstring,
            )
        except Exception:
            return None

    def _extract_interface(
        self, node: Node, source_code: str
    ) -> TypeDefinitionModel | None:
        """Extract interface information from an interface declaration node.

        Args:
            node: Interface declaration AST node
            source_code: Original source code

        Returns:
            TypeDefinitionModel or None if extraction fails

        """
        try:
            name = self._get_type_name(node, source_code)
            docstring = self._get_docstring(node, source_code)
            extends = self._get_interface_extends(node, source_code)
            members = self._get_interface_members(node, source_code)
            methods = self._get_interface_methods(node, source_code)

            return TypeDefinitionModel(
                name=name,
                kind="interface",
                line_start=node.start_point[0] + _LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + _LINE_INDEX_OFFSET,
                extends=extends,
                members=members,
                methods=methods,
                docstring=docstring,
            )
        except Exception:
            return None

    def _extract_type_alias(
        self, node: Node, source_code: str
    ) -> TypeDefinitionModel | None:
        """Extract type alias information.

        Args:
            node: Type alias declaration AST node
            source_code: Original source code

        Returns:
            TypeDefinitionModel or None if extraction fails

        """
        try:
            name = self._get_type_name(node, source_code)
            docstring = self._get_docstring(node, source_code)

            return TypeDefinitionModel(
                name=name,
                kind="type_alias",
                line_start=node.start_point[0] + _LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + _LINE_INDEX_OFFSET,
                docstring=docstring,
            )
        except Exception:
            return None

    def _extract_enum(self, node: Node, source_code: str) -> TypeDefinitionModel | None:
        """Extract enum information.

        Args:
            node: Enum declaration AST node
            source_code: Original source code

        Returns:
            TypeDefinitionModel or None if extraction fails

        """
        try:
            name = self._get_type_name(node, source_code)
            docstring = self._get_docstring(node, source_code)
            members = self._get_enum_members(node, source_code)

            return TypeDefinitionModel(
                name=name,
                kind="enum",
                line_start=node.start_point[0] + _LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + _LINE_INDEX_OFFSET,
                members=members,
                docstring=docstring,
            )
        except Exception:
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

    def _get_type_name(self, node: Node, source_code: str) -> str:
        """Extract class/interface/enum/type name."""
        name_node = find_child_by_type(node, "type_identifier")
        if name_node:
            return get_node_text(name_node, source_code)

        name_node = find_child_by_type(node, "identifier")
        if name_node:
            return get_node_text(name_node, source_code)

        return "<anonymous>"

    def _get_parameters(self, node: Node, source_code: str) -> list[ParameterModel]:
        """Extract function/method parameters."""
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
            return None

    def _get_return_type(self, node: Node, source_code: str) -> str | None:
        """Extract function/method return type."""
        # Look for return_type node (type annotation after parameters)
        for child in node.children:
            if child.type == "type_annotation":
                if len(child.children) > 1:
                    return get_node_text(child.children[-1], source_code)
        return None

    def _get_docstring(self, node: Node, source_code: str) -> str | None:
        """Extract preceding JSDoc comment."""
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

    def _is_async(self, node: Node) -> bool:
        """Check if function/method is async."""
        for child in node.children:
            if child.type == "async":
                return True
        return False

    def _get_visibility(self, node: Node) -> str | None:
        """Extract method visibility modifier."""
        for child in node.children:
            if child.type == "accessibility_modifier":
                return get_node_text(child, node.text.decode() if node.text else "")
        return None

    def _is_static(self, node: Node) -> bool:
        """Check if method has static modifier."""
        for child in node.children:
            if child.type == "static":
                return True
        return False

    def _get_extends(self, node: Node, source_code: str) -> str | None:
        """Extract parent class name from extends clause."""
        extends_clause = find_child_by_type(node, "class_heritage")
        if extends_clause:
            extends_node = find_child_by_type(extends_clause, "extends_clause")
            if extends_node:
                # First identifier after 'extends' keyword
                for child in extends_node.children:
                    if child.type == "identifier":
                        return get_node_text(child, source_code)
        return None

    def _get_implements(self, node: Node, source_code: str) -> list[str]:
        """Extract implemented interface names."""
        implements: list[str] = []
        heritage = find_child_by_type(node, "class_heritage")
        if heritage:
            implements_clause = find_child_by_type(heritage, "implements_clause")
            if implements_clause:
                for child in implements_clause.children:
                    if child.type == "type_identifier":
                        implements.append(get_node_text(child, source_code))
        return implements

    def _get_interface_extends(self, node: Node, source_code: str) -> str | None:
        """Extract parent interface name from extends clause."""
        extends_clause = find_child_by_type(node, "extends_type_clause")
        if extends_clause:
            for child in extends_clause.children:
                if child.type == "type_identifier":
                    return get_node_text(child, source_code)
        return None

    def _get_class_members(self, node: Node, source_code: str) -> list[MemberModel]:
        """Extract class property members."""
        members: list[MemberModel] = []
        body = find_child_by_type(node, "class_body")
        if not body:
            return members

        for child in body.children:
            if child.type in ["public_field_definition", "property_definition"]:
                member = self._extract_property_member(child, source_code)
                if member:
                    members.append(member)

        return members

    def _get_interface_members(self, node: Node, source_code: str) -> list[MemberModel]:
        """Extract interface property members."""
        members: list[MemberModel] = []
        body = find_child_by_type(node, "object_type")
        if not body:
            body = find_child_by_type(node, "interface_body")
        if not body:
            return members

        for child in body.children:
            if child.type == "property_signature":
                member = self._extract_interface_property(child, source_code)
                if member:
                    members.append(member)

        return members

    def _get_enum_members(self, node: Node, source_code: str) -> list[MemberModel]:
        """Extract enum members."""
        members: list[MemberModel] = []
        body = find_child_by_type(node, "enum_body")
        if not body:
            return members

        for child in body.children:
            if child.type == "enum_assignment":
                name_node = find_child_by_type(child, "property_identifier")
                if name_node:
                    name = get_node_text(name_node, source_code)
                    # Get value if present
                    value = None
                    for i, c in enumerate(child.children):
                        if c.type == "=":
                            if i + 1 < len(child.children):
                                value = get_node_text(
                                    child.children[i + 1], source_code
                                )
                            break
                    members.append(
                        MemberModel(
                            name=name,
                            kind="enum_variant",
                            default_value=value,
                        )
                    )
            elif child.type == "property_identifier":
                name = get_node_text(child, source_code)
                members.append(
                    MemberModel(
                        name=name,
                        kind="enum_variant",
                    )
                )

        return members

    def _extract_property_member(
        self, node: Node, source_code: str
    ) -> MemberModel | None:
        """Extract class property as member."""
        try:
            name_node = find_child_by_type(node, "property_identifier")
            if not name_node:
                return None
            name = get_node_text(name_node, source_code)

            # Get type
            prop_type = None
            type_annotation = find_child_by_type(node, "type_annotation")
            if type_annotation and len(type_annotation.children) > 1:
                prop_type = get_node_text(type_annotation.children[-1], source_code)

            # Get visibility
            visibility = None
            for child in node.children:
                if child.type == "accessibility_modifier":
                    visibility = get_node_text(child, source_code)
                    break

            # Check static
            is_static = any(c.type == "static" for c in node.children)

            # Get default value
            default_value = None
            for i, child in enumerate(node.children):
                if child.type == "=":
                    if i + 1 < len(node.children):
                        default_value = get_node_text(node.children[i + 1], source_code)
                    break

            return MemberModel(
                name=name,
                kind="property",
                type=prop_type,
                visibility=visibility,
                is_static=is_static,
                default_value=default_value,
            )
        except Exception:
            return None

    def _extract_interface_property(
        self, node: Node, source_code: str
    ) -> MemberModel | None:
        """Extract interface property as member."""
        try:
            name_node = find_child_by_type(node, "property_identifier")
            if not name_node:
                return None
            name = get_node_text(name_node, source_code)

            # Check if optional (has ?)
            is_optional = any(c.type == "?" for c in node.children)

            # Get type
            prop_type = None
            type_annotation = find_child_by_type(node, "type_annotation")
            if type_annotation and len(type_annotation.children) > 1:
                prop_type = get_node_text(type_annotation.children[-1], source_code)
            if is_optional and prop_type:
                prop_type = f"{prop_type}?"

            return MemberModel(
                name=name,
                kind="property",
                type=prop_type,
            )
        except Exception:
            return None

    def _get_class_methods(self, node: Node, source_code: str) -> list[CallableModel]:
        """Extract class methods."""
        methods: list[CallableModel] = []
        body = find_child_by_type(node, "class_body")
        if not body:
            return methods

        for method_node in find_nodes_by_type(body, _METHOD_TYPE):
            method = self._extract_callable(method_node, source_code, kind="method")
            if method:
                methods.append(method)

        return methods

    def _get_interface_methods(
        self, node: Node, source_code: str
    ) -> list[CallableModel]:
        """Extract interface method signatures."""
        methods: list[CallableModel] = []
        body = find_child_by_type(node, "object_type")
        if not body:
            body = find_child_by_type(node, "interface_body")
        if not body:
            return methods

        for child in body.children:
            if child.type == "method_signature":
                method = self._extract_method_signature(child, source_code)
                if method:
                    methods.append(method)

        return methods

    def _extract_method_signature(
        self, node: Node, source_code: str
    ) -> CallableModel | None:
        """Extract method signature from interface."""
        try:
            name_node = find_child_by_type(node, "property_identifier")
            name = get_node_text(name_node, source_code) if name_node else "<unknown>"

            parameters = self._get_parameters(node, source_code)
            return_type = self._get_return_type(node, source_code)

            return CallableModel(
                name=name,
                kind="method",
                line_start=node.start_point[0] + _LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + _LINE_INDEX_OFFSET,
                parameters=parameters,
                return_type=return_type,
            )
        except Exception:
            return None
