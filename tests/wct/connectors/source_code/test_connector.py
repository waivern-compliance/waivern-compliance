"""Tests for SourceCodeConnector."""

import tempfile
from pathlib import Path

import pytest

from wct.connectors.base import ConnectorConfigError, ConnectorExtractionError
from wct.connectors.source_code.connector import SourceCodeConnector
from wct.message import Message
from wct.schemas import SourceCodeSchema, StandardInputSchema


class TestSourceCodeConnectorInitialisation:
    """Test connector initialisation with different configurations."""

    def test_initialisation_with_valid_php_file(self):
        """Test that connector can be initialised with a valid PHP file."""
        php_content = "<?php function test() { return true; } ?>"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(php_content)
            f.flush()

            try:
                connector = SourceCodeConnector(path=f.name)

                assert connector.path == Path(f.name)
                assert connector.language is None  # Auto-detected
                assert connector.max_file_size == 10 * 1024 * 1024  # 10MB default
                assert connector.max_files == 4000  # Default

            finally:
                Path(f.name).unlink()

    def test_initialisation_with_valid_directory(self):
        """Test that connector can be initialised with a directory containing PHP files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create PHP files in directory
            php_file = Path(temp_dir) / "test.php"
            php_file.write_text("<?php echo 'test'; ?>")

            connector = SourceCodeConnector(path=temp_dir)

            assert connector.path == Path(temp_dir)
            assert connector.language is None
            assert connector.parser is None  # Created on demand for directories

    def test_initialisation_with_custom_parameters(self):
        """Test initialisation with custom configuration parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            php_file = Path(temp_dir) / "test.php"
            php_file.write_text("<?php echo 'test'; ?>")

            connector = SourceCodeConnector(
                path=temp_dir,
                language="php",
                file_patterns=["*.php", "*.phtml"],
                max_file_size=5 * 1024 * 1024,  # 5MB
                max_files=1000,
            )

            assert connector.path == Path(temp_dir)
            assert connector.language == "php"
            assert connector.file_patterns == ["*.php", "*.phtml"]
            assert connector.max_file_size == 5 * 1024 * 1024
            assert connector.max_files == 1000

    def test_initialisation_with_nonexistent_path(self):
        """Test error handling for nonexistent paths."""
        nonexistent_path = "/nonexistent/path/file.php"

        with pytest.raises(ConnectorConfigError, match="Path does not exist"):
            SourceCodeConnector(path=nonexistent_path)

    def test_initialisation_with_path_object(self):
        """Test that connector accepts Path objects as well as strings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            php_file = Path(temp_dir) / "test.php"
            php_file.write_text("<?php echo 'test'; ?>")

            connector = SourceCodeConnector(path=Path(temp_dir))

            assert connector.path == Path(temp_dir)


class TestSourceCodeConnectorClassMethods:
    """Test connector class methods."""

    def test_get_name(self):
        """Test that get_name returns correct connector name."""
        name = SourceCodeConnector.get_name()

        assert name == "source_code"
        assert isinstance(name, str)

    def test_get_supported_output_schemas_returns_source_code(self):
        """Test that the connector supports source_code schema."""
        output_schemas = SourceCodeConnector.get_supported_output_schemas()

        assert len(output_schemas) == 1
        assert output_schemas[0].name == "source_code"
        assert output_schemas[0].version == "1.0.0"

    def test_from_properties_with_minimal_config(self):
        """Test creating connector from properties with minimal configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            php_file = Path(temp_dir) / "test.php"
            php_file.write_text("<?php echo 'test'; ?>")

            properties = {"path": temp_dir}

            connector = SourceCodeConnector.from_properties(properties)

            assert connector.path == Path(temp_dir)
            assert connector.language is None
            assert connector.max_file_size == 10 * 1024 * 1024  # Default
            assert connector.max_files == 4000  # Default

    def test_from_properties_with_full_config(self):
        """Test creating connector from properties with full configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            php_file = Path(temp_dir) / "test.php"
            php_file.write_text("<?php echo 'test'; ?>")

            properties = {
                "path": temp_dir,
                "language": "php",
                "file_patterns": ["*.php"],
                "max_file_size": 2 * 1024 * 1024,  # 2MB
                "max_files": 500,
            }

            connector = SourceCodeConnector.from_properties(properties)

            assert connector.path == Path(temp_dir)
            assert connector.language == "php"
            assert connector.file_patterns == ["*.php"]
            assert connector.max_file_size == 2 * 1024 * 1024
            assert connector.max_files == 500

    def test_from_properties_missing_path(self):
        """Test error handling when path property is missing."""
        properties = {"language": "php"}

        with pytest.raises(ConnectorConfigError, match="path property is required"):
            SourceCodeConnector.from_properties(properties)

    def test_from_properties_empty_path(self):
        """Test error handling when path property is empty."""
        properties = {"path": ""}

        with pytest.raises(ConnectorConfigError, match="path property is required"):
            SourceCodeConnector.from_properties(properties)

    def test_from_properties_none_path(self):
        """Test error handling when path property is None."""
        properties = {"path": None}

        with pytest.raises(ConnectorConfigError, match="path property is required"):
            SourceCodeConnector.from_properties(properties)


class TestSourceCodeConnectorExtraction:
    """Test source code extraction functionality."""

    def test_extract_from_single_php_file(self):
        """Test extraction from a single PHP file."""
        php_content = """<?php
/**
 * User data processing function for GDPR compliance
 */
function processUserData($userData, $options) {
    return sanitiseData($userData);
}

/**
 * User management class
 */
class UserManager {
    /**
     * Creates new user account
     */
    public function createUser($userData) {
        return $this->validateAndStore($userData);
    }
}
?>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(php_content)
            f.flush()

            try:
                connector = SourceCodeConnector(path=f.name)
                message = connector.extract()

                # Verify Message structure
                assert isinstance(message, Message)
                assert message.schema is not None
                assert message.schema.name == "source_code"

                # Verify content structure
                content = message.content
                assert isinstance(content, dict)

                # Check required top-level fields
                required_fields = [
                    "schemaVersion",
                    "name",
                    "description",
                    "language",
                    "source",
                    "metadata",
                    "data",
                ]
                for field in required_fields:
                    assert field in content, f"Missing required field: {field}"

                # Verify metadata
                metadata = content["metadata"]
                assert "total_files" in metadata
                assert "total_lines" in metadata
                assert "analysis_timestamp" in metadata
                assert "parser_version" in metadata
                assert metadata["total_files"] == 1

                # Verify data structure
                assert isinstance(content["data"], list)
                assert len(content["data"]) == 1

                file_data = content["data"][0]
                file_required_fields = [
                    "file_path",
                    "language",
                    "raw_content",
                    "functions",
                    "classes",
                    "imports",
                    "metadata",
                ]
                for field in file_required_fields:
                    assert field in file_data, f"Missing file field: {field}"

                # Verify extracted functions and classes
                assert (
                    len(file_data["functions"]) >= 1
                )  # Should find processUserData function
                assert len(file_data["classes"]) >= 1  # Should find UserManager class

                # Check function structure
                function = file_data["functions"][0]
                assert "name" in function
                assert "line_start" in function
                assert "line_end" in function
                assert "parameters" in function

                # Check class structure
                class_data = file_data["classes"][0]
                assert "name" in class_data
                assert "line_start" in class_data
                assert "line_end" in class_data
                assert "methods" in class_data

            finally:
                Path(f.name).unlink()

    def test_extract_from_directory_with_multiple_files(self):
        """Test extraction from directory containing multiple PHP files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple PHP files
            file1_content = "<?php function func1() { return 1; } ?>"
            file2_content = (
                "<?php class Class1 { public function method1() { return true; } } ?>"
            )
            file3_content = "<?php $variable = 'test'; echo $variable; ?>"

            (temp_path / "file1.php").write_text(file1_content)
            (temp_path / "file2.php").write_text(file2_content)
            (temp_path / "file3.php").write_text(file3_content)

            # Create non-PHP file (should be ignored)
            (temp_path / "readme.txt").write_text("This is not PHP")

            connector = SourceCodeConnector(path=temp_dir)
            message = connector.extract()

            # Verify Message structure
            assert isinstance(message, Message)
            content = message.content

            # Should process multiple files
            assert content["metadata"]["total_files"] >= 2  # At least 2 PHP files
            assert len(content["data"]) >= 2

            # Verify each file data structure
            for file_data in content["data"]:
                assert "file_path" in file_data
                assert "language" in file_data
                assert "raw_content" in file_data
                assert file_data["language"] == "php"

    def test_extract_with_explicit_source_code_schema(self):
        """Test extraction with explicitly provided SourceCodeSchema."""
        php_content = "<?php function test() { return true; } ?>"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(php_content)
            f.flush()

            try:
                connector = SourceCodeConnector(path=f.name)
                explicit_schema = SourceCodeSchema()

                message = connector.extract(output_schema=explicit_schema)

                assert isinstance(message, Message)
                assert message.schema == explicit_schema
                assert message.schema is not None
                assert message.schema.name == "source_code"

            finally:
                Path(f.name).unlink()

    def test_extract_with_file_size_limit(self):
        """Test extraction with file size limitations."""
        # Create a file that's larger than the limit
        large_content = (
            "<?php\n"
            + "// "
            + ("x" * 1000)
            + "\n"
            + "function test() { return true; }\n"
            + "?>"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(large_content)
            f.flush()

            try:
                # Set a very small max file size
                connector = SourceCodeConnector(
                    path=f.name, max_file_size=100
                )  # 100 bytes
                message = connector.extract()

                # Should handle gracefully (file may be skipped)
                assert isinstance(message, Message)
                content = message.content

                # Should return valid structure even if file is skipped
                assert "data" in content
                assert isinstance(content["data"], list)

            finally:
                Path(f.name).unlink()

    def test_extract_with_file_patterns(self):
        """Test extraction with custom file patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with different extensions
            (temp_path / "file1.php").write_text(
                "<?php function func1() { return 1; } ?>"
            )
            (temp_path / "file2.phtml").write_text(
                "<?php function func2() { return 2; } ?>"
            )
            (temp_path / "file3.php3").write_text(
                "<?php function func3() { return 3; } ?>"
            )

            # Test with specific pattern
            connector = SourceCodeConnector(
                path=temp_dir,
                file_patterns=["*.php"],  # Only .php files
            )
            message = connector.extract()

            assert isinstance(message, Message)
            content = message.content

            # Should only process .php files
            assert len(content["data"]) >= 1

            # Verify all processed files match pattern
            for file_data in content["data"]:
                assert file_data["file_path"].endswith(".php")

    def test_extract_excludes_common_file_types(self):
        """Test that common file types are excluded from source code analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create PHP files that should be processed
            (temp_path / "Controller.php").write_text("<?php class Controller {} ?>")
            (temp_path / "Model.php").write_text("<?php class Model {} ?>")

            # Create files that should be excluded based on common exclusions
            (temp_path / "compiled.pyc").write_text("compiled bytecode")
            (temp_path / "binary.class").write_text("java class file")
            (temp_path / "library.o").write_text("object file")
            (temp_path / "dynamic.so").write_text("shared object")
            (temp_path / "windows.dll").write_text("windows dll")
            (temp_path / "application.log").write_text("log file content")
            (temp_path / "temp.tmp").write_text("temporary file")
            (temp_path / "backup.bak").write_text("backup file")
            (temp_path / "vim.swp").write_text("vim swap file")
            (temp_path / "vim.swo").write_text("vim swap file")
            (temp_path / ".DS_Store").write_text("mac metadata")

            # Create directories that should be excluded
            (temp_path / "__pycache__").mkdir()
            (temp_path / "__pycache__" / "module.pyc").write_text("cached python")
            (temp_path / ".git").mkdir()
            (temp_path / ".git" / "config").write_text("git config")
            (temp_path / ".svn").mkdir()
            (temp_path / ".svn" / "entries").write_text("svn entries")
            (temp_path / "node_modules").mkdir()
            (temp_path / "node_modules" / "package.json").write_text("{}")

            connector = SourceCodeConnector(path=temp_dir)
            message = connector.extract()

            assert isinstance(message, Message)
            content = message.content

            # Should only process PHP files, not excluded files
            assert content["metadata"]["total_files"] == 2
            assert len(content["data"]) == 2

            # Verify only PHP files are processed
            processed_files = [file_data["file_path"] for file_data in content["data"]]
            assert "Controller.php" in str(processed_files)
            assert "Model.php" in str(processed_files)

            # Verify excluded files are not processed
            excluded_patterns = [
                ".pyc",
                ".class",
                ".o",
                ".so",
                ".dll",
                ".log",
                ".tmp",
                ".bak",
                ".swp",
                ".swo",
                ".DS_Store",
                "__pycache__",
                ".git",
                ".svn",
                "node_modules",
            ]
            for pattern in excluded_patterns:
                assert pattern not in str(processed_files)

    def test_extract_respects_custom_file_patterns_over_exclusions(self):
        """Test that custom file patterns work correctly with exclusion logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create various PHP files
            (temp_path / "include_me.php").write_text("<?php echo 'include'; ?>")
            (temp_path / "include_me.phtml").write_text("<?php echo 'phtml'; ?>")
            (temp_path / "exclude_me.php3").write_text("<?php echo 'php3'; ?>")

            # Create files that would normally be excluded
            (temp_path / "test.log").write_text("log content")  # Normally excluded

            # Test with patterns that only include specific files
            connector = SourceCodeConnector(
                path=temp_dir,
                file_patterns=["include_me.*"],  # Only files starting with "include_me"
            )
            message = connector.extract()

            assert isinstance(message, Message)
            content = message.content

            # Should only process files matching the include pattern
            processed_files = [file_data["file_path"] for file_data in content["data"]]

            # Should include files matching pattern (and supported by parser)
            assert any("include_me.php" in path for path in processed_files)

            # Should exclude files not matching pattern even if supported
            assert not any("exclude_me.php3" in path for path in processed_files)

            # Should exclude unsupported files regardless of pattern
            assert not any("test.log" in path for path in processed_files)

    def test_extract_handles_nested_excluded_directories(self):
        """Test that nested excluded directories are properly handled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create valid PHP files
            (temp_path / "main.php").write_text("<?php class Main {} ?>")

            # Create nested structures that should be excluded
            git_dir = temp_path / ".git" / "objects" / "ab"
            git_dir.mkdir(parents=True)
            (git_dir / "123456").write_text("git object")

            pycache_dir = temp_path / "src" / "__pycache__"
            pycache_dir.mkdir(parents=True)
            (pycache_dir / "module.cpython-310.pyc").write_text("compiled python")

            node_modules_dir = temp_path / "frontend" / "node_modules" / "package"
            node_modules_dir.mkdir(parents=True)
            (node_modules_dir / "index.js").write_text("javascript content")

            # Create PHP files in non-excluded nested directories
            src_dir = temp_path / "src" / "controllers"
            src_dir.mkdir(parents=True)
            (src_dir / "UserController.php").write_text(
                "<?php class UserController {} ?>"
            )

            connector = SourceCodeConnector(path=temp_dir)
            message = connector.extract()

            assert isinstance(message, Message)
            content = message.content

            # Should process PHP files but exclude entire excluded directories
            assert (
                content["metadata"]["total_files"] == 2
            )  # main.php + UserController.php

            processed_files = [file_data["file_path"] for file_data in content["data"]]
            processed_files_str = str(processed_files)

            # Should include valid PHP files
            assert "main.php" in processed_files_str
            assert "UserController.php" in processed_files_str

            # Should exclude entire excluded directories
            assert ".git" not in processed_files_str
            assert "__pycache__" not in processed_files_str
            assert "node_modules" not in processed_files_str


class TestSourceCodeConnectorEdgeCases:
    """Test edge cases and error handling."""

    def test_extract_from_empty_directory(self):
        """Test extraction from empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = SourceCodeConnector(path=temp_dir)

            # Empty directory should raise ConnectorExtractionError
            with pytest.raises(ConnectorExtractionError, match="No files found"):
                connector.extract()

    def test_extract_from_directory_with_no_php_files(self):
        """Test extraction from directory containing no PHP files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create non-PHP files
            (temp_path / "readme.txt").write_text("This is a readme")
            (temp_path / "config.json").write_text('{"key": "value"}')
            (temp_path / "script.py").write_text("print('hello')")

            connector = SourceCodeConnector(path=temp_dir)
            message = connector.extract()

            assert isinstance(message, Message)
            content = message.content

            # Should return valid structure with empty data
            assert content["metadata"]["total_files"] == 0
            assert content["data"] == []

    def test_extract_with_invalid_php_syntax(self):
        """Test extraction from files with invalid PHP syntax."""
        invalid_php = "<?php\nfunction incomplete(\n// missing closing brace and ?>"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(invalid_php)
            f.flush()

            try:
                connector = SourceCodeConnector(path=f.name)
                # Should not raise exception - tree-sitter handles invalid syntax
                message = connector.extract()

                assert isinstance(message, Message)
                content = message.content

                # Should return valid structure
                assert "data" in content
                assert len(content["data"]) >= 1

                file_data = content["data"][0]
                assert file_data["raw_content"] == invalid_php

            finally:
                Path(f.name).unlink()

    def test_extract_with_binary_file_having_php_extension(self):
        """Test extraction handles binary files with .php extension gracefully."""
        with tempfile.NamedTemporaryFile(suffix=".php", delete=False) as f:
            # Write binary data
            f.write(b"\x80\x81\x82\x83\x84\x85")
            f.flush()

            try:
                connector = SourceCodeConnector(path=f.name)

                # Should handle gracefully or raise appropriate exception
                try:
                    message = connector.extract()
                    # If it succeeds, verify structure
                    assert isinstance(message, Message)
                except ConnectorExtractionError:
                    # This is also acceptable - binary files can't be processed
                    pass

            finally:
                Path(f.name).unlink()

    def test_extract_with_unsupported_output_schema(self):
        """Test error handling with unsupported output schema."""
        php_content = "<?php function test() { return true; } ?>"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(php_content)
            f.flush()

            try:
                connector = SourceCodeConnector(path=f.name)
                unsupported_schema = StandardInputSchema()

                with pytest.raises(
                    ConnectorExtractionError, match="Unsupported output schema"
                ):
                    connector.extract(output_schema=unsupported_schema)

            finally:
                Path(f.name).unlink()


class TestSourceCodeConnectorPerformance:
    """Test performance and efficiency scenarios."""

    def test_extract_from_directory_with_many_files(self):
        """Test extraction from directory with many PHP files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple PHP files
            for i in range(10):  # Reasonable number for testing
                file_content = f"""<?php
/**
 * Test function {i}
 */
function testFunction{i}($param) {{
    return $param + {i};
}}

class TestClass{i} {{
    public function method{i}() {{
        return {i};
    }}
}}
?>"""
                (temp_path / f"file{i}.php").write_text(file_content)

            connector = SourceCodeConnector(path=temp_dir)
            message = connector.extract()

            assert isinstance(message, Message)
            content = message.content

            # Should process all files efficiently
            assert content["metadata"]["total_files"] == 10
            assert len(content["data"]) == 10

            # Verify each file was processed
            for file_data in content["data"]:
                assert len(file_data["functions"]) >= 1
                assert len(file_data["classes"]) >= 1

    def test_extract_with_max_files_limit(self):
        """Test extraction respects maximum files limit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create more files than the limit
            for i in range(10):
                file_content = f"<?php function func{i}() {{ return {i}; }} ?>"
                (temp_path / f"file{i}.php").write_text(file_content)

            # Set low max_files limit
            connector = SourceCodeConnector(path=temp_dir, max_files=5)
            message = connector.extract()

            assert isinstance(message, Message)
            content = message.content

            # Should respect the limit
            assert content["metadata"]["total_files"] <= 5
            assert len(content["data"]) <= 5


class TestSourceCodeConnectorDataStructure:
    """Test the structure and content of extracted data."""

    def test_extracted_data_compliance_focus(self):
        """Test that extracted data focuses on compliance-relevant information."""
        php_content = """<?php
/**
 * User data processor for GDPR compliance
 * Handles personal data according to regulations
 */
function processPersonalData($userData, $purpose) {
    return validateAndProcess($userData, $purpose);
}

/**
 * Privacy compliance manager
 */
class PrivacyManager {
    /**
     * Anonymises user data for deletion requests
     */
    public function anonymiseUserData($userId) {
        return $this->removePersonalIdentifiers($userId);
    }
}
?>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(php_content)
            f.flush()

            try:
                connector = SourceCodeConnector(path=f.name)
                message = connector.extract()

                content = message.content
                file_data = content["data"][0]

                # Verify compliance-focused function data
                functions = file_data["functions"]
                assert len(functions) >= 1

                func = functions[0]
                compliance_fields = [
                    "name",
                    "line_start",
                    "line_end",
                    "parameters",
                    "docstring",
                ]
                for field in compliance_fields:
                    assert field in func

                # Verify compliance-focused class data
                classes = file_data["classes"]
                assert len(classes) >= 1

                cls = classes[0]
                compliance_fields = [
                    "name",
                    "line_start",
                    "line_end",
                    "methods",
                    "docstring",
                ]
                for field in compliance_fields:
                    assert field in cls

                # Verify raw content is included for pattern matching
                assert file_data["raw_content"] == php_content

            finally:
                Path(f.name).unlink()

    def test_extracted_message_validation(self):
        """Test that extracted messages pass schema validation."""
        php_content = "<?php function test() { return true; } ?>"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".php", delete=False) as f:
            f.write(php_content)
            f.flush()

            try:
                connector = SourceCodeConnector(path=f.name)
                message = connector.extract()

                # Message should be pre-validated by connector
                assert isinstance(message, Message)

                # Should be able to validate again without error
                message.validate()  # Should not raise exception

                # Verify schema compliance
                assert message.schema is not None
                assert message.schema.name == "source_code"
                assert message.schema.version == "1.0.0"

            finally:
                Path(f.name).unlink()

    def test_relative_path_handling(self):
        """Test that file paths are handled correctly for compliance reporting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested directory structure
            subdir = temp_path / "src" / "controllers"
            subdir.mkdir(parents=True)

            php_file = subdir / "UserController.php"
            php_file.write_text(
                "<?php class UserController { public function index() { return true; } } ?>"
            )

            connector = SourceCodeConnector(path=temp_dir)
            message = connector.extract()

            content = message.content
            file_data = content["data"][0]

            # Should use relative path from base directory
            assert "src/controllers/UserController.php" in file_data["file_path"]
            # Should not include the full temporary directory path
            assert temp_dir not in file_data["file_path"]
