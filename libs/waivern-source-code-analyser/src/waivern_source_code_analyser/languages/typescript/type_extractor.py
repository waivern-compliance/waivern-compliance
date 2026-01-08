"""TypeScript type definition extraction.

This module handles extraction of classes, interfaces, enums, and type aliases
from TypeScript source code.
"""

import logging
from typing import TYPE_CHECKING

from tree_sitter import Node

logger = logging.getLogger(__name__)

from waivern_source_code_analyser.languages.base import (
    find_child_by_type,
    find_nodes_by_type,
    get_node_text,
)
from waivern_source_code_analyser.languages.models import (
    CallableModel,
    MemberModel,
    TypeDefinitionModel,
)
from waivern_source_code_analyser.languages.typescript.helpers import (
    CLASS_TYPES,
    ENUM_TYPE,
    INTERFACE_TYPE,
    LINE_INDEX_OFFSET,
    METHOD_TYPE,
    TYPE_ALIAS_TYPE,
    get_docstring,
    get_visibility,
    is_static,
)

if TYPE_CHECKING:
    from waivern_source_code_analyser.languages.typescript.callable_extractor import (
        TypeScriptCallableExtractor,
    )


class TypeScriptTypeExtractor:
    """Extracts type definitions from TypeScript source code.

    Handles extraction of:
    - Classes (including abstract classes)
    - Interfaces
    - Enums
    - Type aliases
    """

    def __init__(self, callable_extractor: "TypeScriptCallableExtractor") -> None:
        """Initialise with a callable extractor for method extraction.

        Args:
            callable_extractor: Extractor for extracting class methods

        """
        self._callable_extractor = callable_extractor

    def extract_all(
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
        for class_type in CLASS_TYPES:
            for node in find_nodes_by_type(root_node, class_type):
                type_def = self._extract_class(node, source_code)
                if type_def:
                    type_definitions.append(type_def)

        # Extract interfaces
        for node in find_nodes_by_type(root_node, INTERFACE_TYPE):
            type_def = self._extract_interface(node, source_code)
            if type_def:
                type_definitions.append(type_def)

        # Extract type aliases
        for node in find_nodes_by_type(root_node, TYPE_ALIAS_TYPE):
            type_def = self._extract_type_alias(node, source_code)
            if type_def:
                type_definitions.append(type_def)

        # Extract enums
        for node in find_nodes_by_type(root_node, ENUM_TYPE):
            type_def = self._extract_enum(node, source_code)
            if type_def:
                type_definitions.append(type_def)

        return type_definitions

    def _extract_class(
        self, node: Node, source_code: str
    ) -> TypeDefinitionModel | None:
        """Extract class information from a class declaration node."""
        try:
            name = self._get_type_name(node, source_code)
            docstring_text = get_docstring(node, source_code)
            extends = self._get_extends(node, source_code)
            implements = self._get_implements(node, source_code)
            members = self._get_class_members(node, source_code)
            methods = self._get_class_methods(node, source_code)

            return TypeDefinitionModel(
                name=name,
                kind="class",
                line_start=node.start_point[0] + LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + LINE_INDEX_OFFSET,
                extends=extends,
                implements=implements,
                members=members,
                methods=methods,
                docstring=docstring_text,
            )
        except Exception:
            logger.debug(
                "Failed to extract TypeScript class at line %d",
                node.start_point[0] + LINE_INDEX_OFFSET,
                exc_info=True,
            )
            return None

    def _extract_interface(
        self, node: Node, source_code: str
    ) -> TypeDefinitionModel | None:
        """Extract interface information from an interface declaration node."""
        try:
            name = self._get_type_name(node, source_code)
            docstring_text = get_docstring(node, source_code)
            extends = self._get_interface_extends(node, source_code)
            members = self._get_interface_members(node, source_code)
            methods = self._get_interface_methods(node, source_code)

            return TypeDefinitionModel(
                name=name,
                kind="interface",
                line_start=node.start_point[0] + LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + LINE_INDEX_OFFSET,
                extends=extends,
                members=members,
                methods=methods,
                docstring=docstring_text,
            )
        except Exception:
            logger.debug(
                "Failed to extract TypeScript interface at line %d",
                node.start_point[0] + LINE_INDEX_OFFSET,
                exc_info=True,
            )
            return None

    def _extract_type_alias(
        self, node: Node, source_code: str
    ) -> TypeDefinitionModel | None:
        """Extract type alias information."""
        try:
            name = self._get_type_name(node, source_code)
            docstring_text = get_docstring(node, source_code)

            return TypeDefinitionModel(
                name=name,
                kind="type_alias",
                line_start=node.start_point[0] + LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + LINE_INDEX_OFFSET,
                docstring=docstring_text,
            )
        except Exception:
            logger.debug(
                "Failed to extract TypeScript type alias at line %d",
                node.start_point[0] + LINE_INDEX_OFFSET,
                exc_info=True,
            )
            return None

    def _extract_enum(self, node: Node, source_code: str) -> TypeDefinitionModel | None:
        """Extract enum information."""
        try:
            name = self._get_type_name(node, source_code)
            docstring_text = get_docstring(node, source_code)
            members = self._get_enum_members(node, source_code)

            return TypeDefinitionModel(
                name=name,
                kind="enum",
                line_start=node.start_point[0] + LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + LINE_INDEX_OFFSET,
                members=members,
                docstring=docstring_text,
            )
        except Exception:
            logger.debug(
                "Failed to extract TypeScript enum at line %d",
                node.start_point[0] + LINE_INDEX_OFFSET,
                exc_info=True,
            )
            return None

    def _get_type_name(self, node: Node, source_code: str) -> str:
        """Extract class/interface/enum/type name."""
        name_node = find_child_by_type(node, "type_identifier")
        if name_node:
            return get_node_text(name_node, source_code)

        name_node = find_child_by_type(node, "identifier")
        if name_node:
            return get_node_text(name_node, source_code)

        return "<anonymous>"

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
                        MemberModel(name=name, kind="enum_variant", default_value=value)
                    )
            elif child.type == "property_identifier":
                name = get_node_text(child, source_code)
                members.append(MemberModel(name=name, kind="enum_variant"))

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
            visibility_mod = get_visibility(node, source_code)

            # Check static
            is_static_prop = is_static(node)

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
                visibility=visibility_mod,
                is_static=is_static_prop,
                default_value=default_value,
            )
        except Exception:
            logger.debug(
                "Failed to extract TypeScript class property at line %d",
                node.start_point[0] + LINE_INDEX_OFFSET,
                exc_info=True,
            )
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

            return MemberModel(name=name, kind="property", type=prop_type)
        except Exception:
            logger.debug(
                "Failed to extract TypeScript interface property at line %d",
                node.start_point[0] + LINE_INDEX_OFFSET,
                exc_info=True,
            )
            return None

    def _get_class_methods(self, node: Node, source_code: str) -> list[CallableModel]:
        """Extract class methods."""
        methods: list[CallableModel] = []
        body = find_child_by_type(node, "class_body")
        if not body:
            return methods

        for method_node in find_nodes_by_type(body, METHOD_TYPE):
            method = self._callable_extractor.extract_callable(
                method_node, source_code, kind="method"
            )
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

            # Use callable extractor for parameters and return type
            parameters = self._callable_extractor.get_parameters(node, source_code)
            return_type = self._callable_extractor.get_return_type(node, source_code)

            return CallableModel(
                name=name,
                kind="method",
                line_start=node.start_point[0] + LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + LINE_INDEX_OFFSET,
                parameters=parameters,
                return_type=return_type,
            )
        except Exception:
            logger.debug(
                "Failed to extract TypeScript method signature at line %d",
                node.start_point[0] + LINE_INDEX_OFFSET,
                exc_info=True,
            )
            return None
