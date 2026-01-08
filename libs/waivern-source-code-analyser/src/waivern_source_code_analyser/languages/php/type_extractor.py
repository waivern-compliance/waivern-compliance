"""PHP type definition extraction.

This module handles extraction of classes from PHP source code.
"""

import logging
from typing import TYPE_CHECKING

from tree_sitter import Node

from waivern_source_code_analyser.languages.base import (
    find_child_by_type,
    find_children_by_type,
    find_nodes_by_type,
    get_node_text,
)
from waivern_source_code_analyser.languages.models import (
    CallableModel,
    TypeDefinitionModel,
)
from waivern_source_code_analyser.languages.php.helpers import (
    CLASS_TYPE,
    LINE_INDEX_OFFSET,
    METHOD_TYPE,
    get_docstring,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from waivern_source_code_analyser.languages.php.callable_extractor import (
        PHPCallableExtractor,
    )


class PHPTypeExtractor:
    """Extracts type definitions from PHP source code.

    Handles extraction of:
    - Classes
    """

    def __init__(self, callable_extractor: "PHPCallableExtractor") -> None:
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
            List of TypeDefinitionModel for classes

        """
        type_definitions: list[TypeDefinitionModel] = []

        # Extract classes
        for class_node in find_nodes_by_type(root_node, CLASS_TYPE):
            type_def = self._extract_class(class_node, source_code)
            if type_def:
                type_definitions.append(type_def)

        return type_definitions

    def _extract_class(
        self, node: Node, source_code: str
    ) -> TypeDefinitionModel | None:
        """Extract class information from a class declaration node."""
        try:
            name = self._get_class_name(node, source_code)
            docstring_text = get_docstring(node, source_code)
            extends = self._get_extends(node, source_code)
            implements = self._get_implements(node, source_code)
            methods = self._get_class_methods(node, source_code)

            return TypeDefinitionModel(
                name=name,
                kind="class",
                line_start=node.start_point[0] + LINE_INDEX_OFFSET,
                line_end=node.end_point[0] + LINE_INDEX_OFFSET,
                extends=extends,
                implements=implements,
                methods=methods,
                docstring=docstring_text,
            )
        except Exception:
            logger.debug(
                "Failed to extract PHP class at line %d",
                node.start_point[0] + LINE_INDEX_OFFSET,
                exc_info=True,
            )
            return None

    def _get_class_name(self, node: Node, source_code: str) -> str:
        """Extract class name."""
        name_node = find_child_by_type(node, "name")
        if name_node:
            return get_node_text(name_node, source_code)
        return "<anonymous>"

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
        for method_node in find_nodes_by_type(node, METHOD_TYPE):
            method = self._callable_extractor.extract_callable(
                method_node, source_code, kind="method"
            )
            if method:
                methods.append(method)
        return methods
