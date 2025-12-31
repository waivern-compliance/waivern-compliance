"""Tests for base AST utility functions."""

from unittest.mock import MagicMock

from waivern_source_code_analyser.languages.base import (
    find_child_by_type,
    find_children_by_type,
    find_nodes_by_type,
    get_node_text,
    is_trivial_node,
)


def _make_node(node_type: str, children: list[MagicMock] | None = None) -> MagicMock:
    """Create a mock tree-sitter Node for testing."""
    node = MagicMock()
    node.type = node_type
    node.children = children or []
    return node


class TestGetNodeText:
    """Tests for get_node_text function."""

    def test_get_node_text_simple(self) -> None:
        """Test extracting ASCII text from a node."""
        source = "function processData() {}"
        node = MagicMock()
        node.start_byte = 9  # "processData"
        node.end_byte = 20

        result = get_node_text(node, source)
        assert result == "processData"

    def test_get_node_text_unicode(self) -> None:
        """Test extracting unicode text from a node."""
        source = "const greeting = '你好世界';"
        node = MagicMock()
        # Unicode strings: byte positions differ from character positions
        # '你好世界' is 4 characters but 12 bytes in UTF-8
        node.start_byte = 18  # After "const greeting = '"
        node.end_byte = 30  # Before "'"

        result = get_node_text(node, source)
        assert result == "你好世界"


class TestFindNodesByType:
    """Tests for find_nodes_by_type function."""

    def test_find_nodes_by_type_single_match(self) -> None:
        """Test finding a single matching node."""
        # Tree: root -> function
        function_node = _make_node("function")
        root = _make_node("program", [function_node])

        result = find_nodes_by_type(root, "function")
        assert len(result) == 1
        assert result[0] is function_node

    def test_find_nodes_by_type_multiple_matches(self) -> None:
        """Test finding multiple matching nodes recursively."""
        # Tree: root -> [func1 -> [nested_func], func2]
        nested_func = _make_node("function")
        func1 = _make_node("function", [nested_func])
        func2 = _make_node("function")
        root = _make_node("program", [func1, func2])

        result = find_nodes_by_type(root, "function")
        assert len(result) == 3
        assert func1 in result
        assert func2 in result
        assert nested_func in result

    def test_find_nodes_by_type_no_matches(self) -> None:
        """Test returning empty list when no nodes match."""
        variable = _make_node("variable")
        root = _make_node("program", [variable])

        result = find_nodes_by_type(root, "function")
        assert result == []


class TestFindChildByType:
    """Tests for find_child_by_type function."""

    def test_find_child_by_type_exists(self) -> None:
        """Test finding the first matching direct child."""
        params = _make_node("parameters")
        body = _make_node("body")
        function = _make_node("function", [params, body])

        result = find_child_by_type(function, "body")
        assert result is body

    def test_find_child_by_type_not_exists(self) -> None:
        """Test returning None when no child matches."""
        params = _make_node("parameters")
        function = _make_node("function", [params])

        result = find_child_by_type(function, "return_type")
        assert result is None


class TestFindChildrenByType:
    """Tests for find_children_by_type function."""

    def test_find_children_by_type(self) -> None:
        """Test finding all matching direct children."""
        param1 = _make_node("parameter")
        param2 = _make_node("parameter")
        comma = _make_node(",")
        params = _make_node("parameters", [param1, comma, param2])

        result = find_children_by_type(params, "parameter")
        assert len(result) == 2
        assert param1 in result
        assert param2 in result


class TestIsTrivialNode:
    """Tests for is_trivial_node function."""

    def test_is_trivial_node_returns_true(self) -> None:
        """Test that whitespace and trivial nodes are identified."""
        trivial_types = ["whitespace", ";", "\n", " ", "\t", "text"]

        for node_type in trivial_types:
            node = _make_node(node_type)
            assert is_trivial_node(node) is True, f"Expected {node_type} to be trivial"

    def test_is_trivial_node_returns_false(self) -> None:
        """Test that meaningful nodes are not marked as trivial."""
        meaningful_types = ["function", "class", "variable", "string", "number"]

        for node_type in meaningful_types:
            node = _make_node(node_type)
            assert is_trivial_node(node) is False, (
                f"Expected {node_type} to not be trivial"
            )
