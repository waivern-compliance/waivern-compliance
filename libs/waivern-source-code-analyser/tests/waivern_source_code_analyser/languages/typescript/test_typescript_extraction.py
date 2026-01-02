"""Tests for TypeScript extraction functionality."""

import pytest
from tree_sitter import Node, Parser

from waivern_source_code_analyser.languages.typescript import TypeScriptLanguageSupport


def _parse_ts(source_code: str) -> tuple[TypeScriptLanguageSupport, Node, str]:
    """Parse TypeScript source code and return support instance, root node, and source.

    Returns:
        Tuple of (TypeScriptLanguageSupport instance, root AST node, source code)

    """
    ts = TypeScriptLanguageSupport()
    parser = Parser()
    parser.language = ts.get_tree_sitter_language()
    tree = parser.parse(source_code.encode("utf-8"))
    return ts, tree.root_node, source_code


# Test TypeScript code samples
TS_FUNCTION_WITH_JSDOC = """
/**
 * Processes user personal data for GDPR compliance
 * This function handles sensitive user information
 */
function processUserData(userData: UserData, options: Options): boolean {
    return processData(userData);
}
"""

TS_FUNCTION_WITHOUT_JSDOC = """
function simpleFunction(param: number): number {
    return param * 2;
}
"""

TS_ARROW_FUNCTION = """
const processData = (data: string): string => {
    return data.toUpperCase();
};
"""

TS_ASYNC_ARROW_FUNCTION = """
const fetchUser = async (id: number): Promise<User> => {
    return await api.getUser(id);
};
"""

TS_MULTIPLE_FUNCTIONS = """
function calculateTotal(items: number[]): number {
    return items.reduce((a, b) => a + b, 0);
}

/**
 * Sends notification to user
 */
function sendNotification(userId: string, message: string): void {
    mailer.send(userId, message);
}

function emptyFunction(): void {
    // No implementation
}
"""

TS_FUNCTION_WITH_TYPED_PARAMETERS = """
function processCustomer(
    name: string,
    age: number,
    preferences?: string[]
): boolean {
    return true;
}
"""

TS_FUNCTION_WITH_DEFAULT_PARAMETER = """
function greet(name: string, greeting: string = "Hello"): string {
    return `${greeting}, ${name}!`;
}
"""

TS_CLASS_WITH_METHODS = """
/**
 * User data processor for GDPR compliance
 */
class UserDataProcessor {
    /**
     * Validates email addresses
     */
    public validateEmail(email: string): boolean {
        return email.includes("@");
    }

    private processInternally(): boolean {
        return true;
    }

    protected static helper(): null {
        return null;
    }
}
"""

TS_CLASS_WITHOUT_JSDOC = """
class SimpleClass {
    public simpleMethod(): boolean {
        return true;
    }
}
"""

TS_CLASS_WITH_INHERITANCE = """
/**
 * Base user class
 */
abstract class BaseUser {
    abstract authenticate(): boolean;
}

/**
 * Admin user with elevated privileges
 */
class AdminUser extends BaseUser implements Authenticatable {
    authenticate(): boolean {
        return true;
    }
}
"""

TS_INTERFACE = """
/**
 * User interface defining user structure
 */
interface User {
    id: number;
    name: string;
    email?: string;
    getFullName(): string;
}
"""

TS_TYPE_ALIAS = """
/**
 * Union type for API responses
 */
type ApiResponse = Success | Error | Loading;
"""

TS_ENUM = """
/**
 * User status enumeration
 */
enum UserStatus {
    Active = "active",
    Inactive = "inactive",
    Pending
}
"""

TS_EMPTY_FILE = ""

TS_CLASS_WITH_PROPERTIES = """
class Config {
    public readonly apiUrl: string = "https://api.example.com";
    private secretKey: string;
    protected timeout: number = 5000;
    static version: string = "1.0.0";
}
"""


class TestTypeScriptCallableExtraction:
    """Tests for extracting callables (functions and methods) from TypeScript code."""

    @pytest.mark.parametrize(
        ("source", "expected_name", "has_docstring", "docstring_fragment"),
        [
            (
                TS_FUNCTION_WITH_JSDOC,
                "processUserData",
                True,
                "Processes user personal data for GDPR compliance",
            ),
            (TS_FUNCTION_WITHOUT_JSDOC, "simpleFunction", False, None),
        ],
        ids=["with_jsdoc", "without_jsdoc"],
    )
    def test_extract_function_docstring_handling(
        self,
        source: str,
        expected_name: str,
        has_docstring: bool,
        docstring_fragment: str | None,
    ) -> None:
        """Test extraction correctly handles presence/absence of docstrings."""
        ts, root_node, source_code = _parse_ts(source)

        result = ts.extract(root_node, source_code)

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

    def test_extract_arrow_function(self) -> None:
        """Test extraction of arrow function assigned to const."""
        ts, root_node, source_code = _parse_ts(TS_ARROW_FUNCTION)

        result = ts.extract(root_node, source_code)

        assert len(result.callables) == 1
        func = result.callables[0]
        assert func.name == "processData"
        assert func.kind == "arrow_function"

    def test_extract_async_arrow_function(self) -> None:
        """Test extraction of async arrow function."""
        ts, root_node, source_code = _parse_ts(TS_ASYNC_ARROW_FUNCTION)

        result = ts.extract(root_node, source_code)

        assert len(result.callables) == 1
        func = result.callables[0]
        assert func.name == "fetchUser"
        assert func.is_async is True

    def test_extract_multiple_functions(self) -> None:
        """Test extraction of multiple functions from same file."""
        ts, root_node, source_code = _parse_ts(TS_MULTIPLE_FUNCTIONS)

        result = ts.extract(root_node, source_code)

        assert len(result.callables) == 3
        names = [f.name for f in result.callables]
        assert "calculateTotal" in names
        assert "sendNotification" in names
        assert "emptyFunction" in names

    def test_extract_function_parameters(self) -> None:
        """Test extraction of function parameters with types."""
        ts, root_node, source_code = _parse_ts(TS_FUNCTION_WITH_TYPED_PARAMETERS)

        result = ts.extract(root_node, source_code)

        assert len(result.callables) == 1
        func = result.callables[0]
        assert func.name == "processCustomer"
        assert len(func.parameters) == 3

        # Check parameter names
        param_names = [p.name for p in func.parameters]
        assert "name" in param_names
        assert "age" in param_names
        assert "preferences" in param_names

    def test_extract_function_default_parameter(self) -> None:
        """Test extraction of function with default parameter value."""
        ts, root_node, source_code = _parse_ts(TS_FUNCTION_WITH_DEFAULT_PARAMETER)

        result = ts.extract(root_node, source_code)

        func = result.callables[0]
        greeting_param = next(p for p in func.parameters if p.name == "greeting")
        assert greeting_param.default_value == '"Hello"'

    def test_extract_function_return_type(self) -> None:
        """Test extraction of function return type annotation."""
        ts, root_node, source_code = _parse_ts(TS_FUNCTION_WITH_TYPED_PARAMETERS)

        result = ts.extract(root_node, source_code)

        func = result.callables[0]
        assert func.return_type == "boolean"

    def test_extract_methods_from_class(self) -> None:
        """Test extraction of methods from within class context."""
        ts, root_node, source_code = _parse_ts(TS_CLASS_WITH_METHODS)

        result = ts.extract(root_node, source_code)

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


class TestTypeScriptTypeDefinitionExtraction:
    """Tests for extracting type definitions from TypeScript code."""

    @pytest.mark.parametrize(
        ("source", "expected_name", "has_docstring", "docstring_fragment"),
        [
            (
                TS_CLASS_WITH_METHODS,
                "UserDataProcessor",
                True,
                "User data processor for GDPR compliance",
            ),
            (TS_CLASS_WITHOUT_JSDOC, "SimpleClass", False, None),
        ],
        ids=["with_jsdoc", "without_jsdoc"],
    )
    def test_extract_class_docstring_handling(
        self,
        source: str,
        expected_name: str,
        has_docstring: bool,
        docstring_fragment: str | None,
    ) -> None:
        """Test extraction correctly handles presence/absence of class docstrings."""
        ts, root_node, source_code = _parse_ts(source)

        result = ts.extract(root_node, source_code)

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
        ts, root_node, source_code = _parse_ts(TS_CLASS_WITH_INHERITANCE)

        result = ts.extract(root_node, source_code)

        # Should have at least 2 classes
        class_types = [t for t in result.type_definitions if t.kind == "class"]
        assert len(class_types) == 2
        names = [c.name for c in class_types]
        assert "BaseUser" in names
        assert "AdminUser" in names

    def test_extract_class_inheritance(self) -> None:
        """Test extraction of class extends and implements clauses."""
        ts, root_node, source_code = _parse_ts(TS_CLASS_WITH_INHERITANCE)

        result = ts.extract(root_node, source_code)

        admin_user = next(c for c in result.type_definitions if c.name == "AdminUser")

        # Check extends
        assert admin_user.extends == "BaseUser"

        # Check implements
        assert "Authenticatable" in admin_user.implements

    def test_extract_interface(self) -> None:
        """Test extraction of interface declarations."""
        ts, root_node, source_code = _parse_ts(TS_INTERFACE)

        result = ts.extract(root_node, source_code)

        assert len(result.type_definitions) == 1
        interface = result.type_definitions[0]
        assert interface.name == "User"
        assert interface.kind == "interface"
        assert "User interface defining user structure" in (interface.docstring or "")

    def test_extract_interface_members(self) -> None:
        """Test extraction of interface property members."""
        ts, root_node, source_code = _parse_ts(TS_INTERFACE)

        result = ts.extract(root_node, source_code)

        interface = result.type_definitions[0]

        # Should have property members
        member_names = [m.name for m in interface.members]
        assert "id" in member_names
        assert "name" in member_names
        assert "email" in member_names

    def test_extract_interface_methods(self) -> None:
        """Test extraction of interface method signatures."""
        ts, root_node, source_code = _parse_ts(TS_INTERFACE)

        result = ts.extract(root_node, source_code)

        interface = result.type_definitions[0]

        # Should have method signature
        method_names = [m.name for m in interface.methods]
        assert "getFullName" in method_names

    def test_extract_type_alias(self) -> None:
        """Test extraction of type alias declarations."""
        ts, root_node, source_code = _parse_ts(TS_TYPE_ALIAS)

        result = ts.extract(root_node, source_code)

        assert len(result.type_definitions) == 1
        type_alias = result.type_definitions[0]
        assert type_alias.name == "ApiResponse"
        assert type_alias.kind == "type_alias"

    def test_extract_enum(self) -> None:
        """Test extraction of enum declarations."""
        ts, root_node, source_code = _parse_ts(TS_ENUM)

        result = ts.extract(root_node, source_code)

        assert len(result.type_definitions) == 1
        enum = result.type_definitions[0]
        assert enum.name == "UserStatus"
        assert enum.kind == "enum"

    def test_extract_enum_members(self) -> None:
        """Test extraction of enum members."""
        ts, root_node, source_code = _parse_ts(TS_ENUM)

        result = ts.extract(root_node, source_code)

        enum = result.type_definitions[0]
        member_names = [m.name for m in enum.members]
        assert "Active" in member_names
        assert "Inactive" in member_names
        assert "Pending" in member_names

        # Check enum values
        active_member = next(m for m in enum.members if m.name == "Active")
        assert active_member.default_value == '"active"'


class TestTypeScriptExtractionEdgeCases:
    """Tests for edge cases and error handling in TypeScript extraction."""

    def test_extract_from_empty_file_returns_empty_result(self) -> None:
        """Test extraction from empty TypeScript file returns empty result."""
        ts, root_node, source_code = _parse_ts(TS_EMPTY_FILE)

        result = ts.extract(root_node, source_code)

        assert len(result.callables) == 0
        assert len(result.type_definitions) == 0

    def test_extract_handles_invalid_syntax_gracefully(self) -> None:
        """Test extraction handles invalid syntax without crashing."""
        invalid_ts = "function incomplete_function(\n"
        ts, root_node, source_code = _parse_ts(invalid_ts)

        # Should not raise exception
        result = ts.extract(root_node, source_code)

        # Result should be valid (might be empty or partial)
        assert result is not None

    def test_extract_class_properties(self) -> None:
        """Test extraction of class properties as members."""
        ts, root_node, source_code = _parse_ts(TS_CLASS_WITH_PROPERTIES)

        result = ts.extract(root_node, source_code)

        assert len(result.type_definitions) == 1
        cls = result.type_definitions[0]

        # Should have property members
        member_names = [m.name for m in cls.members]
        assert "apiUrl" in member_names
        assert "secretKey" in member_names
        assert "timeout" in member_names
        assert "version" in member_names

    def test_extract_tsx_react_component(self) -> None:
        """Test extraction from TSX file with React component."""
        tsx_code = """
import React from 'react';

interface Props {
    name: string;
}

const Greeting: React.FC<Props> = ({ name }) => {
    return <div>Hello, {name}!</div>;
};

export default Greeting;
"""
        ts, root_node, source_code = _parse_ts(tsx_code)

        result = ts.extract(root_node, source_code)

        # Should extract the interface
        interface = next(
            (t for t in result.type_definitions if t.name == "Props"), None
        )
        assert interface is not None
        assert interface.kind == "interface"

        # Should extract the arrow function
        greeting_func = next(
            (c for c in result.callables if c.name == "Greeting"), None
        )
        assert greeting_func is not None
        assert greeting_func.kind == "arrow_function"
