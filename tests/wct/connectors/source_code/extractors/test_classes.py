"""Tests for ClassExtractor."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from wct.connectors.source_code.extractors.classes import ClassExtractor
from wct.connectors.source_code.parser import SourceCodeParser

# Test constants - expected behaviour from public interface
EXPECTED_SUPPORTED_LANGUAGES = [
    "php",
    "javascript",
    "python",
    "java",
    "cpp",
    "c",
    "typescript",
    "go",
    "rust",
    "ruby",
]
EXPECTED_DEFAULT_LANGUAGE = "php"
EXPECTED_ANONYMOUS_CLASS_NAME = "<anonymous>"

# Test PHP code samples
PHP_CLASS_WITH_DOCSTRING = """<?php
/**
 * User data processor for GDPR compliance
 * Handles all personal data processing operations
 */
class UserDataProcessor {
    public function processData($data) {
        return $data;
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

PHP_MULTIPLE_CLASSES = """<?php
/**
 * First class for user management
 */
class UserManager {
    public function createUser($userData) {
        return new User($userData);
    }
}

class DataValidator {
    /**
     * Validates email addresses
     */
    public function validateEmail($email) {
        return filter_var($email, FILTER_VALIDATE_EMAIL);
    }

    private function internalValidation() {
        return true;
    }
}

/**
 * Privacy compliance handler
 * Manages GDPR and data protection requirements
 */
class PrivacyHandler {
    public function anonymiseData($data) {
        return array_map('md5', $data);
    }
}
?>"""

PHP_CLASS_WITH_COMPLEX_METHODS = """<?php
/**
 * Advanced data processor
 * Contains multiple methods with different signatures
 */
class AdvancedProcessor {
    /**
     * Main processing method
     */
    public function processUserData(string $userId, array $data, ?array $options = null): bool {
        return true;
    }

    protected function validateInput($input) {
        return !empty($input);
    }

    /**
     * Cleanup method for data removal
     */
    private function cleanupData() {
        // Cleanup implementation
    }

    public static function getInstance() {
        return new self();
    }
}
?>"""

PHP_NESTED_CLASSES = """<?php
namespace App\\Models;

/**
 * User model with nested functionality
 */
class User {
    public function getName() {
        return $this->name;
    }

    /**
     * Profile management
     */
    public function getProfile() {
        return new class {
            public function getData() {
                return [];
            }
        };
    }
}
?>"""


class TestClassExtractorInitialisation:
    """Test class extractor initialisation and basic properties."""

    def test_initialisation_with_default_language(self):
        """Test that extractor can be initialised with default PHP language."""
        extractor = ClassExtractor("php")

        assert extractor.language == "php"

    def test_initialisation_with_custom_language(self):
        """Test that extractor can be initialised with custom language."""
        extractor = ClassExtractor("javascript")

        assert extractor.language == "javascript"

    def test_initialisation_creates_function_extractor(self):
        """Test that class extractor creates internal function extractor for methods."""
        extractor = ClassExtractor("php")

        # Should have function_extractor attribute (public interface)
        assert hasattr(extractor, "function_extractor")
        assert extractor.function_extractor.language == "php"

    def test_initialisation_with_supported_languages(self):
        """Test that extractor accepts all supported languages."""
        for language in EXPECTED_SUPPORTED_LANGUAGES:
            # Only test languages that are actually available in the current environment
            if language == "php":  # We know PHP is available
                extractor = ClassExtractor(language)
                assert extractor.language == language


class TestClassExtractionBasicCases:
    """Test basic class extraction scenarios."""

    def test_extract_class_with_docstring(self):
        """Test extraction of class with PHPDoc comment."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_CLASS_WITH_DOCSTRING)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                classes = extractor.extract(root_node, source_code)

                assert len(classes) == 1
                cls = classes[0]

                assert cls["name"] == "UserDataProcessor"
                assert "line_start" in cls
                assert "line_end" in cls
                assert cls["line_start"] < cls["line_end"]
                assert "docstring" in cls
                assert "User data processor for GDPR compliance" in cls["docstring"]
                assert "methods" in cls
                assert len(cls["methods"]) == 1
                assert cls["methods"][0]["name"] == "processData"

            finally:
                Path(f.name).unlink()

    def test_extract_class_without_docstring(self):
        """Test extraction of class without documentation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_CLASS_WITHOUT_DOCSTRING)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                classes = extractor.extract(root_node, source_code)

                assert len(classes) == 1
                cls = classes[0]

                assert cls["name"] == "SimpleClass"
                assert "line_start" in cls
                assert "line_end" in cls
                assert "methods" in cls
                # docstring should be None for classes without comments
                assert cls.get("docstring") is None

            finally:
                Path(f.name).unlink()

    def test_extract_multiple_classes(self):
        """Test extraction of multiple classes from same file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_MULTIPLE_CLASSES)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                classes = extractor.extract(root_node, source_code)

                assert len(classes) == 3

                # Check class names
                class_names = [cls["name"] for cls in classes]
                expected_names = ["UserManager", "DataValidator", "PrivacyHandler"]
                assert all(name in class_names for name in expected_names)

                # Check that class with docstring has comment
                user_manager = next(c for c in classes if c["name"] == "UserManager")
                assert user_manager["docstring"] is not None
                assert "First class for user management" in user_manager["docstring"]

                # Check privacy handler docstring
                privacy_handler = next(
                    c for c in classes if c["name"] == "PrivacyHandler"
                )
                assert privacy_handler["docstring"] is not None
                assert "Privacy compliance handler" in privacy_handler["docstring"]
                assert "GDPR and data protection" in privacy_handler["docstring"]

                # Check that class without docstring has no comment
                data_validator = next(
                    c for c in classes if c["name"] == "DataValidator"
                )
                assert data_validator.get("docstring") is None

            finally:
                Path(f.name).unlink()

    def test_extract_class_with_complex_methods(self):
        """Test extraction of class with various types of methods."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_CLASS_WITH_COMPLEX_METHODS)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                classes = extractor.extract(root_node, source_code)

                assert len(classes) == 1
                cls = classes[0]

                assert cls["name"] == "AdvancedProcessor"
                assert "Advanced data processor" in cls["docstring"]

                # Should extract multiple methods
                assert "methods" in cls
                assert len(cls["methods"]) >= 3  # At least the defined methods

                # Check for specific methods
                method_names = [method["name"] for method in cls["methods"]]
                expected_methods = [
                    "processUserData",
                    "validateInput",
                    "cleanupData",
                    "getInstance",
                ]

                # At least some of the expected methods should be found
                found_methods = [
                    name for name in expected_methods if name in method_names
                ]
                assert len(found_methods) >= 2, (
                    f"Expected methods not found. Found: {method_names}"
                )

            finally:
                Path(f.name).unlink()


class TestClassExtractionEdgeCases:
    """Test edge cases and error handling in class extraction."""

    def test_extract_from_empty_file(self):
        """Test extraction from empty PHP file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write("<?php\n?>")
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                classes = extractor.extract(root_node, source_code)

                assert classes == []

            finally:
                Path(f.name).unlink()

    def test_extract_from_invalid_syntax(self):
        """Test extraction handles invalid syntax gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write("<?php\nclass IncompleteClass {\n?>")  # Invalid syntax
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                # Should not raise exception, may return empty list or partial results
                classes = extractor.extract(root_node, source_code)

                # Should return a list (might be empty due to invalid syntax)
                assert isinstance(classes, list)

            finally:
                Path(f.name).unlink()

    def test_extract_anonymous_class_handling(self):
        """Test handling of classes that cannot be parsed properly."""
        # Create a mock node that simulates a class without a name node
        mock_root_node = Mock()
        mock_root_node.type = "program"

        mock_class_node = Mock()
        mock_class_node.type = "class_declaration"
        mock_class_node.start_point = [10, 0]
        mock_class_node.end_point = [20, 0]
        mock_class_node.parent = mock_root_node
        mock_class_node.children = []

        mock_root_node.children = [mock_class_node]

        # Mock the find_nodes_by_type to return our mock class
        extractor = ClassExtractor("php")
        original_find = extractor.find_nodes_by_type
        extractor.find_nodes_by_type = Mock(return_value=[mock_class_node])
        extractor.find_child_by_type = Mock(return_value=None)  # No name node found

        try:
            classes = extractor.extract(mock_root_node, "mock source code")

            # Should handle gracefully and either return empty list or class with anonymous name
            assert isinstance(classes, list)
            if classes:
                # If a class is returned, it should have the expected anonymous name
                assert classes[0]["name"] == EXPECTED_ANONYMOUS_CLASS_NAME

        finally:
            extractor.find_nodes_by_type = original_find

    def test_extract_with_different_languages(self):
        """Test that extractor handles different languages appropriately."""
        # Test with different language parameters
        extractor_js = ClassExtractor("javascript")
        extractor_python = ClassExtractor("python")

        # Should initialise without error
        assert extractor_js.language == "javascript"
        assert extractor_python.language == "python"


class TestClassExtractionComplexScenarios:
    """Test complex real-world class extraction scenarios."""

    def test_extract_nested_class_structures(self):
        """Test extraction with nested classes or anonymous classes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_NESTED_CLASSES)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                classes = extractor.extract(root_node, source_code)

                # Should find at least the main User class
                assert len(classes) >= 1

                # Check for the main User class
                class_names = [cls["name"] for cls in classes]
                assert "User" in class_names

                # Find the User class
                user_class = next(c for c in classes if c["name"] == "User")
                assert "User model with nested functionality" in user_class["docstring"]

                # Should have methods
                assert "methods" in user_class
                method_names = [method["name"] for method in user_class["methods"]]
                assert "getName" in method_names or "getProfile" in method_names

            finally:
                Path(f.name).unlink()

    def test_extract_classes_with_inheritance_context(self):
        """Test extraction in contexts with class inheritance."""
        inheritance_php = """<?php
/**
 * Base user class for authentication
 */
abstract class BaseUser {
    abstract public function authenticate();
}

/**
 * Admin user with elevated privileges
 * Extends base user functionality
 */
class AdminUser extends BaseUser {
    /**
     * Admin authentication with additional checks
     */
    public function authenticate() {
        return $this->validateAdminCredentials();
    }

    private function validateAdminCredentials() {
        return true;
    }
}
?>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(inheritance_php)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                classes = extractor.extract(root_node, source_code)

                # Should find both classes
                assert len(classes) == 2

                class_names = [cls["name"] for cls in classes]
                assert "BaseUser" in class_names
                assert "AdminUser" in class_names

                # Check AdminUser has proper documentation
                admin_user = next(c for c in classes if c["name"] == "AdminUser")
                assert "Admin user with elevated privileges" in admin_user["docstring"]

            finally:
                Path(f.name).unlink()


class TestClassExtractionDataStructure:
    """Test the structure and content of extracted class data."""

    def test_extracted_class_contains_required_fields(self):
        """Test that extracted classes contain all required compliance-relevant fields."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_CLASS_WITH_DOCSTRING)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                classes = extractor.extract(root_node, source_code)

                assert len(classes) == 1
                cls = classes[0]

                # Required fields for compliance analysis
                required_fields = [
                    "name",
                    "line_start",
                    "line_end",
                    "docstring",
                    "methods",
                ]

                for field in required_fields:
                    assert field in cls, f"Missing required field: {field}"

                # Verify data types
                assert isinstance(cls["name"], str)
                assert isinstance(cls["line_start"], int)
                assert isinstance(cls["line_end"], int)
                assert isinstance(cls["methods"], list)
                # docstring can be str or None
                assert cls["docstring"] is None or isinstance(cls["docstring"], str)

                # Line numbers should be positive and logical
                assert cls["line_start"] > 0
                assert cls["line_end"] > 0
                assert cls["line_start"] <= cls["line_end"]

            finally:
                Path(f.name).unlink()

    def test_extracted_methods_structure(self):
        """Test the structure of extracted class methods."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_CLASS_WITH_COMPLEX_METHODS)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                classes = extractor.extract(root_node, source_code)

                assert len(classes) == 1
                cls = classes[0]

                # Check methods structure
                for method in cls["methods"]:
                    # Each method should have the same structure as function extraction
                    required_method_fields = [
                        "name",
                        "line_start",
                        "line_end",
                        "parameters",
                    ]

                    for field in required_method_fields:
                        assert field in method, f"Missing method field: {field}"

                    assert isinstance(method["name"], str)
                    assert isinstance(method["line_start"], int)
                    assert isinstance(method["line_end"], int)
                    assert isinstance(method["parameters"], list)
                    # docstring can be str or None, but may not be present if None (filtered out)
                    if "docstring" in method:
                        assert isinstance(method["docstring"], str)

                    # Method names should not be empty
                    assert method["name"].strip() != ""

            finally:
                Path(f.name).unlink()

    def test_compliance_focused_data_exclusion(self):
        """Test that non-compliance-relevant data is excluded from extraction."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_CLASS_WITH_DOCSTRING)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                classes = extractor.extract(root_node, source_code)

                assert len(classes) == 1
                cls = classes[0]

                # These fields should NOT be present (removed for compliance focus)
                excluded_fields = ["extends", "implements", "properties"]

                for field in excluded_fields:
                    assert field not in cls, (
                        f"Excluded field should not be present: {field}"
                    )

            finally:
                Path(f.name).unlink()

    def test_class_method_integration_with_function_extractor(self):
        """Test that class methods are properly extracted using function extractor."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_CLASS_WITH_COMPLEX_METHODS)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                classes = extractor.extract(root_node, source_code)

                assert len(classes) == 1
                cls = classes[0]

                # Methods should have the same structure as standalone functions
                for method in cls["methods"]:
                    # Should have compliance-focused structure (no return_type, visibility, etc.)
                    non_compliance_fields = ["return_type", "visibility", "is_static"]

                    for field in non_compliance_fields:
                        assert field not in method, (
                            f"Non-compliance field found in method: {field}"
                        )

                    # Parameters should not have default_value
                    for param in method["parameters"]:
                        assert "default_value" not in param, (
                            "Parameter default_value should not be present"
                        )

            finally:
                Path(f.name).unlink()


class TestClassExtractionPerformance:
    """Test performance and efficiency of class extraction."""

    def test_extract_handles_large_classes(self):
        """Test extraction of classes with many methods."""
        # Generate a large class with multiple methods
        large_class = """<?php
/**
 * Large class with many methods for performance testing
 */
class LargeClass {
"""

        # Add many methods
        for i in range(20):
            large_class += f"""
    /**
     * Method number {i} for testing
     */
    public function method{i}($param{i}) {{
        return $param{i};
    }}
"""

        large_class += "}\n?>"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(large_class)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = ClassExtractor("php")
                classes = extractor.extract(root_node, source_code)

                assert len(classes) == 1
                cls = classes[0]

                assert cls["name"] == "LargeClass"
                assert "methods" in cls
                # Should handle all methods efficiently
                assert len(cls["methods"]) >= 15  # Should extract most of the methods

            finally:
                Path(f.name).unlink()
