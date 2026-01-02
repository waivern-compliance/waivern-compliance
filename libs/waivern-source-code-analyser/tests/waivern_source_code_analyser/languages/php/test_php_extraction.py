"""Tests for PHP extraction functionality."""

import pytest
from tree_sitter import Node, Parser

from waivern_source_code_analyser.languages.php import PHPLanguageSupport


def _parse_php(source_code: str) -> tuple[PHPLanguageSupport, Node, str]:
    """Parse PHP source code and return support instance, root node, and source.

    Returns:
        Tuple of (PHPLanguageSupport instance, root AST node, source code)

    """
    php = PHPLanguageSupport()
    parser = Parser()
    parser.language = php.get_tree_sitter_language()
    tree = parser.parse(source_code.encode("utf-8"))
    return php, tree.root_node, source_code


# Test PHP code samples
PHP_FUNCTION_WITH_DOCSTRING = """<?php
/**
 * Processes user personal data for GDPR compliance
 * This function handles sensitive user information
 */
function processUserData($userData, $options) {
    return processData($userData);
}
?>"""

PHP_FUNCTION_WITHOUT_DOCSTRING = """<?php
function simpleFunction($param) {
    return $param * 2;
}
?>"""

PHP_MULTIPLE_FUNCTIONS = """<?php
function calculateTotal($items) {
    return array_sum($items);
}

/**
 * Sends notification to user
 */
function sendNotification($userId, $message) {
    return mail_user($userId, $message);
}

function emptyFunction() {
    // No implementation
}
?>"""

PHP_FUNCTION_WITH_TYPED_PARAMETERS = """<?php
function processCustomer(string $name, int $age, ?array $preferences = null): bool {
    return true;
}
?>"""

PHP_CLASS_WITH_METHODS = """<?php
/**
 * User data processor for GDPR compliance
 */
class UserDataProcessor {
    /**
     * Validates email addresses
     */
    public function validateEmail($email) {
        return filter_var($email, FILTER_VALIDATE_EMAIL);
    }

    private function processInternally() {
        return true;
    }

    protected static function helper() {
        return null;
    }
}
?>"""

PHP_CLASS_WITHOUT_DOCSTRING = """<?php
class SimpleClass {
    public function simpleMethod() {
        return true;
    }
}
?>"""

PHP_CLASS_WITH_INHERITANCE = """<?php
/**
 * Base user class
 */
abstract class BaseUser {
    abstract public function authenticate();
}

/**
 * Admin user with elevated privileges
 */
class AdminUser extends BaseUser implements Authenticatable, Authorizable {
    public function authenticate() {
        return true;
    }
}
?>"""

PHP_EMPTY_FILE = """<?php
?>"""

PHP_NAMESPACED_CODE = """<?php
namespace App\\Controllers;

use App\\Models\\User;

/**
 * User controller
 */
class UserController {
    public function index() {
        return User::all();
    }
}
?>"""


class TestPHPCallableExtraction:
    """Tests for extracting callables (functions and methods) from PHP code."""

    @pytest.mark.parametrize(
        ("source", "expected_name", "has_docstring", "docstring_fragment"),
        [
            (
                PHP_FUNCTION_WITH_DOCSTRING,
                "processUserData",
                True,
                "Processes user personal data for GDPR compliance",
            ),
            (PHP_FUNCTION_WITHOUT_DOCSTRING, "simpleFunction", False, None),
        ],
        ids=["with_docstring", "without_docstring"],
    )
    def test_extract_function_docstring_handling(
        self,
        source: str,
        expected_name: str,
        has_docstring: bool,
        docstring_fragment: str | None,
    ) -> None:
        """Test extraction correctly handles presence/absence of docstrings."""
        php, root_node, source_code = _parse_php(source)

        result = php.extract(root_node, source_code)

        assert len(result.callables) == 1
        func = result.callables[0]
        assert func.name == expected_name
        assert func.kind == "function"

        if has_docstring:
            assert func.docstring is not None
            assert docstring_fragment is not None
            assert docstring_fragment in func.docstring
        else:
            assert func.docstring is None

    def test_extract_multiple_functions(self) -> None:
        """Test extraction of multiple functions from same file."""
        php, root_node, source_code = _parse_php(PHP_MULTIPLE_FUNCTIONS)

        result = php.extract(root_node, source_code)

        assert len(result.callables) == 3
        names = [f.name for f in result.callables]
        assert "calculateTotal" in names
        assert "sendNotification" in names
        assert "emptyFunction" in names

    def test_extract_function_parameters(self) -> None:
        """Test extraction of function parameters with types and defaults."""
        php, root_node, source_code = _parse_php(PHP_FUNCTION_WITH_TYPED_PARAMETERS)

        result = php.extract(root_node, source_code)

        assert len(result.callables) == 1
        func = result.callables[0]
        assert func.name == "processCustomer"
        assert len(func.parameters) == 3

        # Check parameter names
        param_names = [p.name for p in func.parameters]
        assert "$name" in param_names
        assert "$age" in param_names
        assert "$preferences" in param_names

        # Check default value extraction
        preferences_param = next(p for p in func.parameters if p.name == "$preferences")
        assert preferences_param.default_value == "null"

    def test_extract_function_return_type(self) -> None:
        """Test extraction of function return type declaration."""
        php, root_node, source_code = _parse_php(PHP_FUNCTION_WITH_TYPED_PARAMETERS)

        result = php.extract(root_node, source_code)

        func = result.callables[0]
        assert func.return_type == "bool"

    def test_extract_methods_from_class(self) -> None:
        """Test extraction of methods from within class context."""
        php, root_node, source_code = _parse_php(PHP_CLASS_WITH_METHODS)

        result = php.extract(root_node, source_code)

        assert len(result.type_definitions) == 1
        cls = result.type_definitions[0]
        assert len(cls.methods) == 3

        method_names = [m.name for m in cls.methods]
        assert "validateEmail" in method_names
        assert "processInternally" in method_names
        assert "helper" in method_names

        # All should have kind="method"
        for method in cls.methods:
            assert method.kind == "method"

    def test_extract_method_visibility(self) -> None:
        """Test extraction of method visibility modifiers."""
        php, root_node, source_code = _parse_php(PHP_CLASS_WITH_METHODS)

        result = php.extract(root_node, source_code)

        cls = result.type_definitions[0]
        methods_by_name = {m.name: m for m in cls.methods}

        assert methods_by_name["validateEmail"].visibility == "public"
        assert methods_by_name["processInternally"].visibility == "private"
        assert methods_by_name["helper"].visibility == "protected"

    def test_extract_static_method(self) -> None:
        """Test extraction of static method modifier."""
        php, root_node, source_code = _parse_php(PHP_CLASS_WITH_METHODS)

        result = php.extract(root_node, source_code)

        cls = result.type_definitions[0]
        methods_by_name = {m.name: m for m in cls.methods}

        assert methods_by_name["helper"].is_static is True
        assert methods_by_name["validateEmail"].is_static is False


class TestPHPTypeDefinitionExtraction:
    """Tests for extracting type definitions (classes) from PHP code."""

    @pytest.mark.parametrize(
        ("source", "expected_name", "has_docstring", "docstring_fragment"),
        [
            (
                PHP_CLASS_WITH_METHODS,
                "UserDataProcessor",
                True,
                "User data processor for GDPR compliance",
            ),
            (PHP_CLASS_WITHOUT_DOCSTRING, "SimpleClass", False, None),
        ],
        ids=["with_docstring", "without_docstring"],
    )
    def test_extract_class_docstring_handling(
        self,
        source: str,
        expected_name: str,
        has_docstring: bool,
        docstring_fragment: str | None,
    ) -> None:
        """Test extraction correctly handles presence/absence of class docstrings."""
        php, root_node, source_code = _parse_php(source)

        result = php.extract(root_node, source_code)

        assert len(result.type_definitions) >= 1
        cls = next(c for c in result.type_definitions if c.name == expected_name)
        assert cls.kind == "class"

        if has_docstring:
            assert cls.docstring is not None
            assert docstring_fragment is not None
            assert docstring_fragment in cls.docstring
        else:
            assert cls.docstring is None

    def test_extract_multiple_classes(self) -> None:
        """Test extraction of multiple classes from same file."""
        php, root_node, source_code = _parse_php(PHP_CLASS_WITH_INHERITANCE)

        result = php.extract(root_node, source_code)

        assert len(result.type_definitions) == 2
        names = [c.name for c in result.type_definitions]
        assert "BaseUser" in names
        assert "AdminUser" in names

    def test_extract_class_inheritance(self) -> None:
        """Test extraction of class extends and implements clauses."""
        php, root_node, source_code = _parse_php(PHP_CLASS_WITH_INHERITANCE)

        result = php.extract(root_node, source_code)

        admin_user = next(c for c in result.type_definitions if c.name == "AdminUser")

        # Check extends
        assert admin_user.extends == "BaseUser"

        # Check implements
        assert "Authenticatable" in admin_user.implements
        assert "Authorizable" in admin_user.implements


class TestPHPExtractionEdgeCases:
    """Tests for edge cases and error handling in PHP extraction."""

    def test_extract_from_empty_file_returns_empty_result(self) -> None:
        """Test extraction from empty PHP file returns empty result."""
        php, root_node, source_code = _parse_php(PHP_EMPTY_FILE)

        result = php.extract(root_node, source_code)

        assert len(result.callables) == 0
        assert len(result.type_definitions) == 0

    def test_extract_handles_invalid_syntax_gracefully(self) -> None:
        """Test extraction handles invalid syntax without crashing."""
        invalid_php = "<?php\nfunction incomplete_function(\n?>"
        php, root_node, source_code = _parse_php(invalid_php)

        # Should not raise exception
        result = php.extract(root_node, source_code)

        # Result should be valid (might be empty or partial)
        assert result is not None

    def test_extract_nested_anonymous_class(self) -> None:
        """Test extraction handles nested anonymous classes."""
        php_code = """<?php
class User {
    public function getProfile() {
        return new class {
            public function getData() {
                return [];
            }
        };
    }
}
?>"""
        php, root_node, source_code = _parse_php(php_code)

        result = php.extract(root_node, source_code)

        # Should extract the main User class
        assert len(result.type_definitions) >= 1
        user_class = next(
            (c for c in result.type_definitions if c.name == "User"), None
        )
        assert user_class is not None

    def test_extract_namespaced_code(self) -> None:
        """Test extraction from namespaced PHP code."""
        php, root_node, source_code = _parse_php(PHP_NAMESPACED_CODE)

        result = php.extract(root_node, source_code)

        assert len(result.type_definitions) == 1
        cls = result.type_definitions[0]
        assert cls.name == "UserController"
