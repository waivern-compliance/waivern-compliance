"""Shared helper functions for TypeScript extraction.

This module provides utility functions used by both callable and type
extractors to avoid code duplication.
"""

from tree_sitter import Node

from waivern_source_code_analyser.languages.base import (
    get_node_text,
    is_trivial_node,
)

# TypeScript file extensions
TS_EXTENSIONS = [".ts", ".tsx", ".mts", ".cts"]

# TypeScript AST node types for callables
FUNCTION_TYPES = ["function_declaration"]
ARROW_FUNCTION_TYPE = "arrow_function"
METHOD_TYPE = "method_definition"

# TypeScript AST node types for type definitions
CLASS_TYPES = ["class_declaration", "abstract_class_declaration"]
INTERFACE_TYPE = "interface_declaration"
TYPE_ALIAS_TYPE = "type_alias_declaration"
ENUM_TYPE = "enum_declaration"

# Line index offset (tree-sitter uses 0-based, we want 1-based)
LINE_INDEX_OFFSET = 1


def get_docstring(node: Node, source_code: str) -> str | None:
    """Extract preceding JSDoc comment for a node.

    Args:
        node: The AST node to find docstring for
        source_code: The full source code

    Returns:
        The docstring text or None if not found

    """
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


def get_visibility(node: Node, source_code: str) -> str | None:
    """Extract visibility modifier from a node.

    Args:
        node: The AST node to extract visibility from
        source_code: The full source code for text extraction

    Returns:
        Visibility string ('public', 'private', 'protected') or None

    """
    for child in node.children:
        if child.type == "accessibility_modifier":
            return get_node_text(child, source_code)
    return None


def is_static(node: Node) -> bool:
    """Check if a node has a static modifier.

    Args:
        node: The AST node to check

    Returns:
        True if the node has a static modifier

    """
    return any(child.type == "static" for child in node.children)


def is_async(node: Node) -> bool:
    """Check if a function/method is async.

    Args:
        node: The function/method AST node

    Returns:
        True if the function is async

    """
    return any(child.type == "async" for child in node.children)
