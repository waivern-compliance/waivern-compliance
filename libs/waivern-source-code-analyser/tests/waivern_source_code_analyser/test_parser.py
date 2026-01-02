"""Tests for SourceCodeParser."""

import tempfile
from pathlib import Path

import pytest
from waivern_core.errors import ParserError

from waivern_source_code_analyser.parser import SourceCodeParser


class TestSourceCodeParserInitialisation:
    """Test parser initialisation with different languages."""

    def test_initialisation_with_default_language(self):
        """Test that parser can be initialised with default language."""
        parser = SourceCodeParser()

        assert parser.language == "php"

    @pytest.mark.parametrize(
        ("language",),
        [("php",), ("typescript",)],
        ids=["php", "typescript"],
    )
    def test_initialisation_with_supported_language(self, language: str) -> None:
        """Test that parser initialises correctly with supported languages."""
        parser = SourceCodeParser(language)

        assert parser.language == language

    def test_initialisation_with_unsupported_language(self):
        """Test that parser raises error for unsupported languages."""
        unsupported_languages = ["javascript", "python", "java", "unsupported_language"]

        for language in unsupported_languages:
            with pytest.raises(ParserError, match="Unsupported language"):
                SourceCodeParser(language)

    def test_initialisation_language_case_sensitivity(self):
        """Test that language names are case sensitive and must be lowercase."""
        case_variations = ["PHP", "Php", "pHP"]

        for variation in case_variations:
            with pytest.raises(ParserError, match="Unsupported language"):
                SourceCodeParser(variation)


class TestLanguageDetection:
    """Test language detection from file extensions."""

    @pytest.mark.parametrize(
        ("language", "extensions"),
        [
            ("php", [".php", ".php3", ".php4", ".php5", ".phtml"]),
            ("typescript", [".ts", ".tsx", ".mts", ".cts"]),
        ],
        ids=["php", "typescript"],
    )
    def test_detect_language_from_extensions(
        self, language: str, extensions: list[str]
    ) -> None:
        """Test language detection from all supported extensions."""
        for ext in extensions:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(b"// sample code")
                f.flush()

                try:
                    parser = SourceCodeParser()
                    detected_language = parser.detect_language_from_file(Path(f.name))

                    assert detected_language == language, f"Failed for extension {ext}"

                finally:
                    Path(f.name).unlink()

    @pytest.mark.parametrize(
        ("language", "extension"),
        [
            ("php", ".PHP"),
            ("typescript", ".TS"),
        ],
        ids=["php_uppercase", "typescript_uppercase"],
    )
    def test_detect_language_case_insensitive_extension(
        self, language: str, extension: str
    ) -> None:
        """Test that language detection handles case insensitive extensions."""
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
            f.write(b"// sample code")
            f.flush()

            try:
                parser = SourceCodeParser()
                detected_language = parser.detect_language_from_file(Path(f.name))

                assert detected_language == language

            finally:
                Path(f.name).unlink()

    def test_detect_language_unsupported_extension(self) -> None:
        """Test error handling for unsupported file extensions."""
        with tempfile.NamedTemporaryFile(suffix=".unsupported", delete=False) as f:
            f.write(b"some content")
            f.flush()

            try:
                parser = SourceCodeParser()

                with pytest.raises(ParserError, match="Cannot detect language"):
                    parser.detect_language_from_file(Path(f.name))

            finally:
                Path(f.name).unlink()

    def test_detect_language_no_extension(self) -> None:
        """Test error handling for files without extension."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"<?php echo 'test'; ?>")
            f.flush()

            try:
                parser = SourceCodeParser()

                with pytest.raises(ParserError, match="Cannot detect language"):
                    parser.detect_language_from_file(Path(f.name))

            finally:
                Path(f.name).unlink()


class TestFileSupport:
    """Test file support checking functionality."""

    @pytest.mark.parametrize(
        ("language", "extensions"),
        [
            ("php", [".php", ".php3", ".php4", ".php5", ".phtml"]),
            ("typescript", [".ts", ".tsx", ".mts", ".cts"]),
        ],
        ids=["php", "typescript"],
    )
    def test_is_supported_file_language_extensions(
        self, language: str, extensions: list[str]
    ) -> None:
        """Test that language extensions are recognised as supported."""
        parser = SourceCodeParser()

        for ext in extensions:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                try:
                    assert parser.is_supported_file(Path(f.name)) is True, (
                        f"Expected {language} extension {ext} to be supported"
                    )
                finally:
                    Path(f.name).unlink()

    @pytest.mark.parametrize(
        ("extension",),
        [(".PHP",), (".TS",)],
        ids=["php_uppercase", "typescript_uppercase"],
    )
    def test_is_supported_file_case_insensitive(self, extension: str) -> None:
        """Test that file support checking is case insensitive."""
        parser = SourceCodeParser()

        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
            try:
                assert parser.is_supported_file(Path(f.name)) is True
            finally:
                Path(f.name).unlink()

    def test_is_supported_file_unsupported_extensions(self) -> None:
        """Test that unsupported extensions return False."""
        parser = SourceCodeParser()
        unsupported_extensions = [".txt", ".py", ".js", ".java", ".cpp"]

        for ext in unsupported_extensions:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                try:
                    assert parser.is_supported_file(Path(f.name)) is False
                finally:
                    Path(f.name).unlink()

    def test_is_supported_file_no_extension(self) -> None:
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
                source_code = Path(f.name).read_text(encoding="utf-8")
                root_node = parser.parse(source_code)

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
                source_code = Path(f.name).read_text(encoding="utf-8")
                root_node = parser.parse(source_code)

                assert root_node is not None
                assert source_code == php_content
                assert root_node.type == "program"

            finally:
                Path(f.name).unlink()

    @pytest.mark.parametrize(
        ("language", "invalid_content", "suffix"),
        [
            ("php", "<?php\nfunction incomplete_function(\n?>", ".php"),
            ("typescript", "function incomplete_function(\n", ".ts"),
        ],
        ids=["php", "typescript"],
    )
    def test_parse_file_with_syntax_errors(
        self, language: str, invalid_content: str, suffix: str
    ) -> None:
        """Test parsing of file with syntax errors handles gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
            f.write(invalid_content)
            f.flush()

            try:
                parser = SourceCodeParser(language)
                # Should not raise exception - tree-sitter handles invalid syntax gracefully
                source_code = Path(f.name).read_text(encoding="utf-8")
                root_node = parser.parse(source_code)

                assert root_node is not None
                assert source_code == invalid_content
                # Tree-sitter should still create a program node
                assert root_node.type == "program"

            finally:
                Path(f.name).unlink()

    # Note: File I/O error tests removed - parser no longer handles file I/O
    # File operations are now the responsibility of connectors/analysers

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
                source_code = Path(f.name).read_text(encoding="utf-8")
                root_node = parser.parse(source_code)

                assert root_node is not None
                assert source_code == large_php_content
                assert root_node.type == "program"
                # Should have many child nodes for all the functions
                assert len(root_node.children) > 50

            finally:
                Path(f.name).unlink()

    def test_parse_valid_typescript_file(self):
        """Test parsing of valid TypeScript file."""
        ts_content = """
/**
 * User interface for type definitions
 */
interface User {
    id: number;
    name: string;
}

function greet(user: User): string {
    return `Hello, ${user.name}!`;
}

class UserService {
    private users: User[] = [];

    public getUser(id: number): User | undefined {
        return this.users.find(u => u.id === id);
    }
}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
            f.write(ts_content)
            f.flush()

            try:
                parser = SourceCodeParser("typescript")
                source_code = Path(f.name).read_text(encoding="utf-8")
                root_node = parser.parse(source_code)

                # Verify return types
                assert root_node is not None
                assert isinstance(source_code, str)
                assert source_code == ts_content

                # Verify AST structure basics (tree-sitter Node has these attributes)
                assert hasattr(root_node, "type")
                assert hasattr(root_node, "children")
                assert root_node.type == "program"

            finally:
                Path(f.name).unlink()

    def test_parse_tsx_file_with_jsx(self):
        """Test parsing of TSX file with JSX syntax."""
        tsx_content = """
import React from 'react';

interface Props {
    name: string;
}

const Greeting: React.FC<Props> = ({ name }) => {
    return <div>Hello, {name}!</div>;
};

export default Greeting;
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsx", delete=False) as f:
            f.write(tsx_content)
            f.flush()

            try:
                parser = SourceCodeParser("typescript")
                source_code = Path(f.name).read_text(encoding="utf-8")
                root_node = parser.parse(source_code)

                assert root_node is not None
                assert source_code == tsx_content
                assert root_node.type == "program"

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
                source_code = Path(f.name).read_text(encoding="utf-8")
                root_node = parser.parse(source_code)

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
                source_code = Path(f.name).read_text(encoding="utf-8")
                root_node = parser.parse(source_code)

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
                source_code = Path(file_path).read_text(encoding="utf-8")
                root_node = parser.parse(source_code)

                assert root_node is not None
                assert source_code == files_content[i]
                assert root_node.type == "program"

        finally:
            for file_path in temp_files:
                Path(file_path).unlink()


class TestParserEdgeCases:
    """Test parser edge cases and language detection."""

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
