"""Tests for SourceCodeParser."""

import tempfile
from pathlib import Path

import pytest
from waivern_core.errors import ConnectorConfigError

from waivern_community.connectors.source_code.parser import SourceCodeParser


class TestSourceCodeParserInitialisation:
    """Test parser initialisation with different languages."""

    def test_initialisation_with_default_language(self):
        """Test that parser can be initialised with default language."""
        parser = SourceCodeParser()

        assert parser.language == "php"

    def test_initialisation_with_php_language(self):
        """Test that parser can be initialised with PHP language explicitly."""
        parser = SourceCodeParser("php")

        assert parser.language == "php"

    def test_initialisation_with_unsupported_language(self):
        """Test that parser raises error for unsupported languages."""
        unsupported_languages = ["javascript", "python", "java", "unsupported_language"]

        for language in unsupported_languages:
            with pytest.raises(ConnectorConfigError, match="Unsupported language"):
                SourceCodeParser(language)

    def test_initialisation_language_case_sensitivity(self):
        """Test that language names are case sensitive and must be lowercase."""
        case_variations = ["PHP", "Php", "pHP"]

        for variation in case_variations:
            with pytest.raises(ConnectorConfigError, match="Unsupported language"):
                SourceCodeParser(variation)


class TestLanguageDetection:
    """Test language detection from file extensions."""

    def test_detect_php_from_standard_extension(self):
        """Test detection of PHP from .php extension."""
        with tempfile.NamedTemporaryFile(suffix=".php", delete=False) as f:
            f.write(b"<?php echo 'test'; ?>")
            f.flush()

            try:
                parser = SourceCodeParser()
                detected_language = parser.detect_language_from_file(Path(f.name))

                assert detected_language == "php"

            finally:
                Path(f.name).unlink()

    def test_detect_php_from_alternative_extensions(self):
        """Test detection of PHP from alternative extensions."""
        php_extensions = [".php3", ".php4", ".php5", ".phtml"]

        for ext in php_extensions:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(b"<?php echo 'test'; ?>")
                f.flush()

                try:
                    parser = SourceCodeParser()
                    detected_language = parser.detect_language_from_file(Path(f.name))

                    assert detected_language == "php"

                finally:
                    Path(f.name).unlink()

    def test_detect_language_case_insensitive_extension(self):
        """Test that language detection handles case insensitive extensions."""
        with tempfile.NamedTemporaryFile(suffix=".PHP", delete=False) as f:
            f.write(b"<?php echo 'test'; ?>")
            f.flush()

            try:
                parser = SourceCodeParser()
                detected_language = parser.detect_language_from_file(Path(f.name))

                assert detected_language == "php"

            finally:
                Path(f.name).unlink()

    def test_detect_language_unsupported_extension(self):
        """Test error handling for unsupported file extensions."""
        with tempfile.NamedTemporaryFile(suffix=".unsupported", delete=False) as f:
            f.write(b"some content")
            f.flush()

            try:
                parser = SourceCodeParser()

                with pytest.raises(
                    ConnectorConfigError, match="Cannot detect language"
                ):
                    parser.detect_language_from_file(Path(f.name))

            finally:
                Path(f.name).unlink()

    def test_detect_language_no_extension(self):
        """Test error handling for files without extension."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"<?php echo 'test'; ?>")
            f.flush()

            try:
                parser = SourceCodeParser()

                with pytest.raises(
                    ConnectorConfigError, match="Cannot detect language"
                ):
                    parser.detect_language_from_file(Path(f.name))

            finally:
                Path(f.name).unlink()


class TestFileSupport:
    """Test file support checking functionality."""

    def test_is_supported_file_php_extensions(self):
        """Test that PHP extensions are recognised as supported."""
        parser = SourceCodeParser()
        php_extensions = [".php", ".php3", ".php4", ".php5", ".phtml"]

        for ext in php_extensions:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                try:
                    assert parser.is_supported_file(Path(f.name)) is True
                finally:
                    Path(f.name).unlink()

    def test_is_supported_file_case_insensitive(self):
        """Test that file support checking is case insensitive."""
        parser = SourceCodeParser()

        with tempfile.NamedTemporaryFile(suffix=".PHP", delete=False) as f:
            try:
                assert parser.is_supported_file(Path(f.name)) is True
            finally:
                Path(f.name).unlink()

    def test_is_supported_file_unsupported_extensions(self):
        """Test that unsupported extensions return False."""
        parser = SourceCodeParser()
        unsupported_extensions = [".txt", ".py", ".js", ".java", ".cpp"]

        for ext in unsupported_extensions:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                try:
                    assert parser.is_supported_file(Path(f.name)) is False
                finally:
                    Path(f.name).unlink()

    def test_is_supported_file_no_extension(self):
        """Test that files without extension are not supported."""
        parser = SourceCodeParser()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            try:
                assert parser.is_supported_file(Path(f.name)) is False
            finally:
                Path(f.name).unlink()


class TestFileParsing:
    """Test file parsing functionality."""

    def test_parse_valid_php_file(self):
        """Test parsing of valid PHP file."""
        php_content = """<?php
/**
 * Test function for parsing
 */
function testFunction($param) {
    return $param * 2;
}

class TestClass {
    public function testMethod() {
        return true;
    }
}
?>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(php_content)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                # Verify return types
                assert root_node is not None
                assert isinstance(source_code, str)
                assert source_code == php_content

                # Verify AST structure basics (tree-sitter Node has these attributes)
                assert hasattr(root_node, "type")
                assert hasattr(root_node, "children")
                assert root_node.type == "program"

            finally:
                Path(f.name).unlink()

    def test_parse_empty_php_file(self):
        """Test parsing of empty PHP file."""
        php_content = "<?php\n?>"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(php_content)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                assert root_node is not None
                assert source_code == php_content
                assert root_node.type == "program"

            finally:
                Path(f.name).unlink()

    def test_parse_php_file_with_syntax_errors(self):
        """Test parsing of PHP file with syntax errors."""
        invalid_php = "<?php\nfunction incomplete_function(\n?>"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(invalid_php)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                # Should not raise exception - tree-sitter handles invalid syntax gracefully
                root_node, source_code = parser.parse_file(Path(f.name))

                assert root_node is not None
                assert source_code == invalid_php
                # Tree-sitter should still create a program node
                assert root_node.type == "program"

            finally:
                Path(f.name).unlink()

    def test_parse_nonexistent_file(self):
        """Test error handling for nonexistent files."""
        parser = SourceCodeParser("php")
        nonexistent_path = Path("/nonexistent/file.php")

        with pytest.raises(ConnectorConfigError, match="Cannot parse file"):
            parser.parse_file(nonexistent_path)

    def test_parse_binary_file(self):
        """Test error handling for binary files that cannot be decoded."""
        with tempfile.NamedTemporaryFile(suffix=".php", delete=False) as f:
            # Write binary data that cannot be decoded as UTF-8
            f.write(b"\x80\x81\x82\x83")
            f.flush()

            try:
                parser = SourceCodeParser("php")

                with pytest.raises(ConnectorConfigError, match="Cannot parse file"):
                    parser.parse_file(Path(f.name))

            finally:
                Path(f.name).unlink()

    def test_parse_large_php_file(self):
        """Test parsing of large PHP file."""
        # Generate a large but valid PHP file
        large_php_content = "<?php\n"
        for i in range(100):
            large_php_content += f"""
function func{i}($param) {{
    return $param + {i};
}}
"""
        large_php_content += "\n?>"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(large_php_content)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                assert root_node is not None
                assert source_code == large_php_content
                assert root_node.type == "program"
                # Should have many child nodes for all the functions
                assert len(root_node.children) > 50

            finally:
                Path(f.name).unlink()


class TestParserComplexScenarios:
    """Test parser with complex real-world scenarios."""

    def test_parse_php_with_mixed_content(self):
        """Test parsing PHP file with HTML and mixed content."""
        mixed_content = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<?php
/**
 * User authentication function
 */
function authenticateUser($username, $password) {
    // Simulate authentication logic
    return validateCredentials($username, $password);
}

class UserManager {
    /**
     * Process user data for compliance
     */
    public function processUserData($userData) {
        return $this->sanitiseData($userData);
    }
}
?>
<p>Welcome to the application</p>
</body>
</html>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(mixed_content)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                assert root_node is not None
                assert source_code == mixed_content
                assert root_node.type == "program"

            finally:
                Path(f.name).unlink()

    def test_parse_php_with_namespaces_and_classes(self):
        """Test parsing PHP file with namespaces and complex structures."""
        namespace_php = """<?php
namespace App\\Controllers;

use App\\Models\\User;
use App\\Services\\DataProcessor;

/**
 * Controller for handling user data operations
 * Ensures GDPR compliance in all operations
 */
class UserController {

    /**
     * Process user registration data
     */
    public function register(array $userData): bool {
        $processor = new DataProcessor();
        return $processor->processRegistration($userData);
    }

    /**
     * Handle user data deletion requests
     */
    public function deleteUser(int $userId): void {
        $user = User::find($userId);
        $user->anonymise();
        $user->delete();
    }
}
?>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(namespace_php)
            f.flush()

            try:
                parser = SourceCodeParser("php")
                root_node, source_code = parser.parse_file(Path(f.name))

                assert root_node is not None
                assert source_code == namespace_php
                assert root_node.type == "program"

            finally:
                Path(f.name).unlink()

    def test_parse_multiple_php_files_with_same_parser(self):
        """Test that same parser instance can handle multiple files."""
        files_content = [
            "<?php function func1() { return 1; } ?>",
            "<?php class Class1 { public function method1() { return true; } } ?>",
            "<?php $var = 'test'; echo $var; ?>",
        ]

        parser = SourceCodeParser("php")
        temp_files = []

        try:
            for i, content in enumerate(files_content):
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_{i}.php", delete=False
                )
                temp_file.write(content)
                temp_file.flush()
                temp_files.append(temp_file.name)

            # Parse all files with same parser instance
            for i, file_path in enumerate(temp_files):
                root_node, source_code = parser.parse_file(Path(file_path))

                assert root_node is not None
                assert source_code == files_content[i]
                assert root_node.type == "program"

        finally:
            for file_path in temp_files:
                Path(file_path).unlink()


class TestParserErrorHandling:
    """Test parser error handling and edge cases."""

    def test_parse_file_with_permission_error(self):
        """Test handling of files that cannot be read due to permissions."""
        # This test may not work on all systems, but we can test the error path
        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write("<?php echo 'test'; ?>")
            f.flush()

            try:
                # Change permissions to make file unreadable (if possible)
                file_path = Path(f.name)
                try:
                    file_path.chmod(0o000)  # Remove all permissions

                    parser = SourceCodeParser("php")

                    with pytest.raises(ConnectorConfigError, match="Cannot parse file"):
                        parser.parse_file(file_path)

                except (OSError, PermissionError):
                    # If we can't change permissions, skip this specific test
                    # but verify the parser works normally
                    file_path.chmod(0o644)  # Restore permissions
                    parser = SourceCodeParser("php")
                    root_node, source_code = parser.parse_file(file_path)
                    assert root_node is not None

            finally:
                try:
                    Path(f.name).chmod(0o644)  # Restore permissions before cleanup
                    Path(f.name).unlink()
                except (OSError, PermissionError):
                    pass  # Ignore cleanup errors

    def test_parse_directory_instead_of_file(self):
        """Test error handling when trying to parse a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            parser = SourceCodeParser("php")

            with pytest.raises(ConnectorConfigError, match="Cannot parse file"):
                parser.parse_file(Path(temp_dir))

    def test_language_detection_with_symbolic_links(self):
        """Test language detection with symbolic links to PHP files."""
        original_content = "<?php echo 'original'; ?>"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".php", delete=False
        ) as original:
            original.write(original_content)
            original.flush()

            try:
                # Create symbolic link (if supported by the system)
                link_path = Path(original.name + "_link.php")
                try:
                    link_path.symlink_to(Path(original.name))

                    parser = SourceCodeParser()
                    detected_language = parser.detect_language_from_file(link_path)

                    assert detected_language == "php"

                except (OSError, NotImplementedError):
                    # Symbolic links not supported on this system
                    # Test normal file detection instead
                    parser = SourceCodeParser()
                    detected_language = parser.detect_language_from_file(
                        Path(original.name)
                    )
                    assert detected_language == "php"
                finally:
                    if link_path.exists():
                        link_path.unlink()

            finally:
                Path(original.name).unlink()
