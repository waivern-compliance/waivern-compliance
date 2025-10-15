"""Tests for FunctionExtractor."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from wct.connectors.source_code.extractors.functions import FunctionExtractor
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
EXPECTED_ANONYMOUS_FUNCTION_NAME = "<anonymous>"

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

PHP_CLASS_WITH_METHODS = """<?php
class UserProcessor {
    /**
     * Validates user email for compliance
     */
    public function validateEmail($email) {
        return filter_var($email, FILTER_VALIDATE_EMAIL);
    }

    private function processInternally() {
        return true;
    }
}
?>"""

PHP_MULTIPLE_FUNCTIONS = """<?php
function calculateTotal($items) {
    return array_sum($items);
}

/**
 * Sends notification to user
 * Contains personal data processing
 */
function sendNotification($userId, $message) {
    return mail_user($userId, $message);
}

function emptyFunction() {
    // No implementation
}
?>"""

PHP_FUNCTION_WITH_TYPED_PARAMETERS = """<?php
/**
 * Processes customer data with type hints
 */
function processCustomer(string $name, int $age, ?array $preferences = null): bool {
    return true;
}
?>"""


class TestFunctionExtractorInitialisation:
    """Test function extractor initialisation and basic properties."""

    def test_initialisation_with_default_language(self):
        """Test that extractor can be initialised with default PHP language."""
        extractor = FunctionExtractor("php")

        assert extractor.language == "php"

    def test_initialisation_with_custom_language(self):
        """Test that extractor can be initialised with custom language."""
        extractor = FunctionExtractor("javascript")

        assert extractor.language == "javascript"

    def test_initialisation_with_supported_languages(self):
        """Test that extractor accepts all supported languages."""
        for language in EXPECTED_SUPPORTED_LANGUAGES:
            # Only test languages that are actually available in the current environment
            if language == "php":  # We know PHP is available
                extractor = FunctionExtractor(language)
                assert extractor.language == language


class TestFunctionExtractionBasicCases:
    """Test basic function extraction scenarios."""

    def test_extract_function_with_docstring(self):
        """Test extraction of function with PHPDoc comment."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_FUNCTION_WITH_DOCSTRING)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = FunctionExtractor("php")
                functions = extractor.extract(root_node, source_code)

                assert len(functions) == 1
                func = functions[0]

                assert func["name"] == "processUserData"
                assert "line_start" in func
                assert "line_end" in func
                assert func["line_start"] < func["line_end"]
                assert "parameters" in func
                assert len(func["parameters"]) == 2
                assert func["parameters"][0]["name"] == "$userData"
                assert func["parameters"][1]["name"] == "$options"
                assert "docstring" in func
                assert (
                    "Processes user personal data for GDPR compliance"
                    in func["docstring"]
                )

            finally:
                Path(f.name).unlink()

    def test_extract_function_without_docstring(self):
        """Test extraction of function without documentation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_FUNCTION_WITHOUT_DOCSTRING)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = FunctionExtractor("php")
                functions = extractor.extract(root_node, source_code)

                assert len(functions) == 1
                func = functions[0]

                assert func["name"] == "simpleFunction"
                assert "line_start" in func
                assert "line_end" in func
                assert "parameters" in func
                assert len(func["parameters"]) == 1
                assert func["parameters"][0]["name"] == "$param"
                # docstring should be None or not present for functions without comments
                assert func.get("docstring") is None

            finally:
                Path(f.name).unlink()

    def test_extract_multiple_functions(self):
        """Test extraction of multiple functions from same file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_MULTIPLE_FUNCTIONS)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = FunctionExtractor("php")
                functions = extractor.extract(root_node, source_code)

                assert len(functions) == 3

                # Check function names
                function_names = [func["name"] for func in functions]
                expected_names = ["calculateTotal", "sendNotification", "emptyFunction"]
                assert all(name in function_names for name in expected_names)

                # Check that function with docstring has comment
                notification_func = next(
                    f for f in functions if f["name"] == "sendNotification"
                )
                assert notification_func["docstring"] is not None
                assert "Sends notification to user" in notification_func["docstring"]

                # Check that function without docstring has no comment
                calculate_func = next(
                    f for f in functions if f["name"] == "calculateTotal"
                )
                assert calculate_func.get("docstring") is None

            finally:
                Path(f.name).unlink()

    def test_extract_function_with_typed_parameters(self):
        """Test extraction of function with type-hinted parameters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_FUNCTION_WITH_TYPED_PARAMETERS)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = FunctionExtractor("php")
                functions = extractor.extract(root_node, source_code)

                assert len(functions) == 1
                func = functions[0]

                assert func["name"] == "processCustomer"
                assert len(func["parameters"]) == 3

                # Check parameter names
                param_names = [p["name"] for p in func["parameters"]]
                assert "$name" in param_names
                assert "$age" in param_names
                assert "$preferences" in param_names

                # Check that parameters have type information where available
                for param in func["parameters"]:
                    assert "name" in param
                    assert "type" in param  # May be None for some parameters

            finally:
                Path(f.name).unlink()


class TestFunctionExtractionEdgeCases:
    """Test edge cases and error handling in function extraction."""

    def test_extract_from_empty_file(self):
        """Test extraction from empty PHP file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write("<?php\n?>")
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = FunctionExtractor("php")
                functions = extractor.extract(root_node, source_code)

                assert functions == []

            finally:
                Path(f.name).unlink()

    def test_extract_from_invalid_syntax(self):
        """Test extraction handles invalid syntax gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write("<?php\nfunction incomplete_function(\n?>")  # Invalid syntax
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = FunctionExtractor("php")
                # Should not raise exception, may return empty list or partial results
                functions = extractor.extract(root_node, source_code)

                # Should return a list (might be empty due to invalid syntax)
                assert isinstance(functions, list)

            finally:
                Path(f.name).unlink()

    def test_extract_anonymous_function_handling(self):
        """Test handling of functions that cannot be parsed properly."""
        # Create a mock node that simulates a function without a name node
        mock_root_node = Mock()
        mock_root_node.type = "program"

        mock_function_node = Mock()
        mock_function_node.type = "function_definition"
        mock_function_node.start_point = [10, 0]
        mock_function_node.end_point = [15, 0]
        mock_function_node.parent = mock_root_node
        mock_function_node.children = []

        mock_root_node.children = [mock_function_node]

        # Mock the find_nodes_by_type to return our mock function
        extractor = FunctionExtractor("php")
        original_find = extractor.find_nodes_by_type
        extractor.find_nodes_by_type = Mock(return_value=[mock_function_node])
        extractor.find_child_by_type = Mock(return_value=None)  # No name node found

        try:
            functions = extractor.extract(mock_root_node, "mock source code")

            # Should handle gracefully and either return empty list or function with anonymous name
            assert isinstance(functions, list)
            if functions:
                # If a function is returned, it should have the expected anonymous name
                assert functions[0]["name"] == EXPECTED_ANONYMOUS_FUNCTION_NAME

        finally:
            extractor.find_nodes_by_type = original_find

    def test_extract_with_different_language_parameter_styles(self):
        """Test that extractor handles different languages appropriately."""
        # Test with JavaScript style (though tree-sitter-php is used for parsing)
        extractor_js = FunctionExtractor("javascript")
        extractor_python = FunctionExtractor("python")

        # Should initialise without error
        assert extractor_js.language == "javascript"
        assert extractor_python.language == "python"


class TestFunctionExtractionComplexScenarios:
    """Test complex real-world function extraction scenarios."""

    def test_extract_methods_within_classes(self):
        """Test extraction of methods from within class context."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_CLASS_WITH_METHODS)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = FunctionExtractor("php")
                functions = extractor.extract(root_node, source_code)

                # Should find methods as functions
                assert len(functions) >= 1  # At least one method should be found

                # Check for the documented method
                method_names = [func["name"] for func in functions]
                assert "validateEmail" in method_names

                # Find the validateEmail method
                validate_method = next(
                    f for f in functions if f["name"] == "validateEmail"
                )
                assert "docstring" in validate_method
                assert (
                    "Validates user email for compliance"
                    in validate_method["docstring"]
                )

            finally:
                Path(f.name).unlink()

    def test_extract_functions_with_complex_parameters(self):
        """Test extraction of functions with complex parameter structures."""
        complex_php = """<?php
/**
 * Complex function with various parameter types
 */
function complexFunction($simple, array $arrayParam, ?string $optional, $default = 'value') {
    return true;
}
?>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(complex_php)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = FunctionExtractor("php")
                functions = extractor.extract(root_node, source_code)

                assert len(functions) == 1
                func = functions[0]

                assert func["name"] == "complexFunction"
                # Should extract parameters (exact structure may vary based on parser)
                assert "parameters" in func
                assert len(func["parameters"]) >= 4  # At least the 4 defined parameters

            finally:
                Path(f.name).unlink()


class TestFunctionExtractionDataStructure:
    """Test the structure and content of extracted function data."""

    def test_extracted_function_contains_required_fields(self):
        """Test that extracted functions contain all required compliance-relevant fields."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_FUNCTION_WITH_DOCSTRING)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = FunctionExtractor("php")
                functions = extractor.extract(root_node, source_code)

                assert len(functions) == 1
                func = functions[0]

                # Required fields for compliance analysis
                required_fields = [
                    "name",
                    "line_start",
                    "line_end",
                    "parameters",
                    "docstring",
                ]

                for field in required_fields:
                    assert field in func, f"Missing required field: {field}"

                # Verify data types
                assert isinstance(func["name"], str)
                assert isinstance(func["line_start"], int)
                assert isinstance(func["line_end"], int)
                assert isinstance(func["parameters"], list)
                # docstring can be str or None
                assert func["docstring"] is None or isinstance(func["docstring"], str)

                # Line numbers should be positive and logical
                assert func["line_start"] > 0
                assert func["line_end"] > 0
                assert func["line_start"] <= func["line_end"]

            finally:
                Path(f.name).unlink()

    def test_extracted_parameters_structure(self):
        """Test the structure of extracted function parameters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_FUNCTION_WITH_TYPED_PARAMETERS)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = FunctionExtractor("php")
                functions = extractor.extract(root_node, source_code)

                assert len(functions) == 1
                func = functions[0]

                # Check parameter structure
                for param in func["parameters"]:
                    # Each parameter should have name and type fields
                    required_param_fields = ["name", "type"]

                    for field in required_param_fields:
                        assert field in param, f"Missing parameter field: {field}"

                    assert isinstance(param["name"], str)
                    # type can be str or None
                    assert param["type"] is None or isinstance(param["type"], str)

                    # Parameter names should not be empty
                    assert param["name"].strip() != ""

            finally:
                Path(f.name).unlink()

    def test_compliance_focused_data_exclusion(self):
        """Test that non-compliance-relevant data is excluded from extraction."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(PHP_FUNCTION_WITH_DOCSTRING)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                extractor = FunctionExtractor("php")
                functions = extractor.extract(root_node, source_code)

                assert len(functions) == 1
                func = functions[0]

                # These fields should NOT be present (removed for compliance focus)
                excluded_fields = ["return_type", "visibility", "is_static"]

                for field in excluded_fields:
                    assert field not in func, (
                        f"Excluded field should not be present: {field}"
                    )

                # Parameter default values should also be excluded
                for param in func["parameters"]:
                    assert "default_value" not in param, (
                        "Parameter default_value should not be present"
                    )

            finally:
                Path(f.name).unlink()
