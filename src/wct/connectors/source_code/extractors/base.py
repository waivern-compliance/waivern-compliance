"""Base extractor class for source code analysis."""

import abc
from typing import Any

from tree_sitter import Node


class BaseExtractor(abc.ABC):
    """Base class for source code extractors.

    Extractors analyse tree-sitter AST nodes to extract specific information
    for compliance analysis such as functions, classes, database interactions, etc.
    """

    def __init__(self, language: str):
        """Initialize the extractor.

        Args:
            language: Programming language (php, javascript, python, etc.)
        """
        self.language = language

    @abc.abstractmethod
    def extract(self, node: Node, source_code: str) -> list[dict[str, Any]]:
        """Extract information from an AST node.

        Args:
            node: Tree-sitter AST node to analyse
            source_code: Original source code (for getting text content)

        Returns:
            List of extracted information dictionaries
        """

    def get_node_text(self, node: Node, source_code: str) -> str:
        """Get the text content of a node.

        Args:
            node: Tree-sitter node
            source_code: Original source code

        Returns:
            Text content of the node
        """
        source_bytes = source_code.encode("utf-8")
        return source_bytes[node.start_byte : node.end_byte].decode("utf-8")

    def find_nodes_by_type(self, node: Node, node_type: str) -> list[Node]:
        """Find all nodes of a specific type in the tree.

        Args:
            node: Root node to search from
            node_type: Type of nodes to find

        Returns:
            List of matching nodes
        """
        results = []

        if node.type == node_type:
            results.append(node)

        for child in node.children:
            results.extend(self.find_nodes_by_type(child, node_type))

        return results

    def find_child_by_type(self, node: Node, child_type: str) -> Node | None:
        """Find the first child node of a specific type.

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

    def get_node_line_range(self, node: Node) -> tuple[int, int]:
        """Get the line range (start, end) for a node.

        Args:
            node: Tree-sitter node

        Returns:
            Tuple of (start_line, end_line) (1-indexed)
        """
        return (node.start_point[0] + 1, node.end_point[0] + 1)
