"""Base utility functions for AST traversal.

These functions are language-agnostic and can be used by all language
implementations for common tree-sitter operations.
"""

from tree_sitter import Node

_DEFAULT_ENCODING = "utf-8"

# Node types considered whitespace or trivial
_TRIVIAL_NODE_TYPES = frozenset(
    {
        "text",
        "whitespace",
        "\n",
        " ",
        "\t",
        "newline",
        "indent",
        "dedent",
        ";",
    }
)


def get_node_text(node: Node, source_code: str) -> str:
    """Get the text content of an AST node.

    Args:
        node: Tree-sitter node with start_byte and end_byte attributes
        source_code: Original source code string

    Returns:
        Text content of the node

    """
    source_bytes = source_code.encode(_DEFAULT_ENCODING)
    return source_bytes[node.start_byte : node.end_byte].decode(_DEFAULT_ENCODING)


def find_nodes_by_type(node: Node, node_type: str) -> list[Node]:
    """Find all descendant nodes of a specific type (recursive).

    Args:
        node: Root node to search from
        node_type: Type of nodes to find

    Returns:
        List of matching nodes (depth-first order)

    """
    results: list[Node] = []
    _collect_nodes_by_type(node, node_type, results)
    return results


def find_child_by_type(node: Node, child_type: str) -> Node | None:
    """Find the first direct child of a specific type.

    Args:
        node: Parent node to search in
        child_type: Type of child node to find

    Returns:
        First matching child node or None

    """
    for child in node.children:
        if child.type == child_type:
            return child
    return None


def find_children_by_type(node: Node, child_type: str) -> list[Node]:
    """Find all direct children of a specific type.

    Args:
        node: Parent node to search in
        child_type: Type of children to find

    Returns:
        List of matching child nodes

    """
    return [child for child in node.children if child.type == child_type]


def is_trivial_node(node: Node) -> bool:
    """Check if a node represents whitespace or trivial content.

    Args:
        node: Tree-sitter node to check

    Returns:
        True if node is whitespace or trivial

    """
    return node.type in _TRIVIAL_NODE_TYPES


def _collect_nodes_by_type(node: Node, node_type: str, results: list[Node]) -> None:
    """Recursively collect nodes of a specific type.

    Args:
        node: Current node to examine
        node_type: Type of nodes to collect
        results: List to append matching nodes to

    """
    if node.type == node_type:
        results.append(node)

    for child in node.children:
        _collect_nodes_by_type(child, node_type, results)
