"""Tests for SourceCodeAnalyser."""

import tempfile
from pathlib import Path

from waivern_core.message import Message
from waivern_core.schemas import (
    FilesystemMetadata,
    Schema,
    StandardInputDataItemModel,
    StandardInputDataModel,
)

from waivern_source_code_analyser.analyser import SourceCodeAnalyser
from waivern_source_code_analyser.analyser_config import SourceCodeAnalyserConfig


class TestSourceCodeAnalyserInitialisation:
    """Test analyser initialisation and configuration."""

    def test_init_creates_analyser_with_valid_configuration(self):
        """Test that __init__ creates analyser with valid configuration."""
        # Arrange
        config = SourceCodeAnalyserConfig.from_properties({})

        # Act
        analyser = SourceCodeAnalyser(config)

        # Assert - only verify object creation and public method availability
        assert analyser is not None
        assert hasattr(analyser, "process")
        assert callable(getattr(analyser, "process"))
        assert hasattr(analyser, "get_name")
        assert callable(getattr(analyser, "get_name"))

    def test_get_name_returns_correct_analyser_name(self):
        """Test that get_name returns correct analyser name."""
        # Act
        name = SourceCodeAnalyser.get_name()

        # Assert
        assert name == "source_code_analyser"
        assert isinstance(name, str)

    def test_get_input_requirements_returns_standard_input(self):
        """Test that analyser supports standard_input schema."""
        # Act
        requirements = SourceCodeAnalyser.get_input_requirements()

        # Assert
        assert isinstance(requirements, list)
        assert len(requirements) == 1  # One valid combination
        assert len(requirements[0]) == 1  # One requirement in that combination
        assert requirements[0][0].schema_name == "standard_input"
        assert requirements[0][0].version == "1.0.0"

    def test_get_supported_output_schemas_returns_source_code(self):
        """Test that analyser supports source_code schema."""
        # Act
        schemas = SourceCodeAnalyser.get_supported_output_schemas()

        # Assert
        assert isinstance(schemas, list)
        assert len(schemas) == 1
        assert schemas[0].name == "source_code"
        assert schemas[0].version == "1.0.0"


class TestSourceCodeAnalyserStandardInputProcessing:
    """Test standard_input schema processing path."""

    def test_process_single_php_file_with_functions_and_classes(self):
        """Test analysing a single PHP file with functions and classes."""
        # Arrange
        php_content = """<?php
/**
 * User data processing function
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

        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="PHP file analysis",
            description="Single PHP file for testing",
            source="/test/TestFile.php",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content=php_content,
                    metadata=FilesystemMetadata(
                        source="/test/TestFile.php",
                        connector_type="filesystem_connector",
                        file_path="/test/TestFile.php",
                    ),
                ),
            ],
        )

        message = Message(
            id="test_single_php",
            content=data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

        config = SourceCodeAnalyserConfig.from_properties({})
        analyser = SourceCodeAnalyser(config)

        # Act
        result = analyser.process(
            [message],
            Schema("source_code", "1.0.0"),
        )

        # Assert
        assert isinstance(result, Message)
        assert result.schema is not None
        assert result.schema.name == "source_code"
        assert result.schema.version == "1.0.0"

        content = result.content
        assert isinstance(content, dict)

        # Verify required top-level fields
        assert "schemaVersion" in content
        assert "name" in content
        assert "language" in content
        assert "data" in content
        assert "metadata" in content

        # Verify parsed data
        assert len(content["data"]) == 1
        file_data = content["data"][0]

        assert "file_path" in file_data
        assert "language" in file_data
        assert "functions" in file_data
        assert "classes" in file_data
        assert "raw_content" in file_data

        # Verify functions extracted
        assert len(file_data["functions"]) >= 1
        func = file_data["functions"][0]
        assert func["name"] == "processUserData"
        assert "line_start" in func
        assert "line_end" in func

        # Verify classes extracted
        assert len(file_data["classes"]) >= 1
        cls = file_data["classes"][0]
        assert cls["name"] == "UserManager"
        assert "line_start" in cls
        assert "line_end" in cls

    def test_process_multiple_php_files_in_single_message(self):
        """Test analysing multiple PHP files in a single message."""
        # Arrange
        php_content_1 = "<?php function func1() { return 1; } ?>"
        php_content_2 = (
            "<?php class Class1 { public function method1() { return true; } } ?>"
        )
        php_content_3 = "<?php $variable = 'test'; ?>"

        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Multi-file analysis",
            description="Multiple PHP files for testing",
            source="/test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content=php_content_1,
                    metadata=FilesystemMetadata(
                        source="/test/file1.php",
                        connector_type="filesystem_connector",
                        file_path="/test/file1.php",
                    ),
                ),
                StandardInputDataItemModel(
                    content=php_content_2,
                    metadata=FilesystemMetadata(
                        source="/test/file2.php",
                        connector_type="filesystem_connector",
                        file_path="/test/file2.php",
                    ),
                ),
                StandardInputDataItemModel(
                    content=php_content_3,
                    metadata=FilesystemMetadata(
                        source="/test/file3.php",
                        connector_type="filesystem_connector",
                        file_path="/test/file3.php",
                    ),
                ),
            ],
        )

        message = Message(
            id="test_multi_file",
            content=data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

        config = SourceCodeAnalyserConfig.from_properties({})
        analyser = SourceCodeAnalyser(config)

        # Act
        result = analyser.process(
            [message],
            Schema("source_code", "1.0.0"),
        )

        # Assert
        assert isinstance(result, Message)
        content = result.content

        # Verify all 3 files processed
        assert len(content["data"]) == 3
        assert content["metadata"]["total_files"] == 3

        # Verify each file has correct structure
        for file_data in content["data"]:
            assert "file_path" in file_data
            assert "language" in file_data
            assert file_data["language"] == "php"

    def test_process_with_language_override_from_config(self):
        """Test language override in config when file has no extension."""
        # Arrange
        php_content = "<?php function test() { return true; } ?>"

        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Language override test",
            description="Test with no extension",
            source="/test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content=php_content,
                    metadata=FilesystemMetadata(
                        source="/test/noextension",
                        connector_type="filesystem_connector",
                        file_path="/test/noextension",
                    ),
                ),
            ],
        )

        message = Message(
            id="test_lang_override",
            content=data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

        # Config specifies language explicitly
        config = SourceCodeAnalyserConfig.from_properties({"language": "php"})
        analyser = SourceCodeAnalyser(config)

        # Act
        result = analyser.process(
            [message],
            Schema("source_code", "1.0.0"),
        )

        # Assert
        content = result.content
        assert len(content["data"]) == 1
        assert content["data"][0]["language"] == "php"

    def test_process_skips_files_exceeding_max_file_size(self):
        """Test that files exceeding max_file_size are skipped."""
        # Arrange
        large_content = "<?php\n" + ("// " + ("x" * 1000) + "\n") + "?>"

        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Large file test",
            description="Test file size limit",
            source="/test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content=large_content,
                    metadata=FilesystemMetadata(
                        source="/test/large.php",
                        connector_type="filesystem_connector",
                        file_path="/test/large.php",
                    ),
                ),
            ],
        )

        message = Message(
            id="test_large",
            content=data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

        # Set very small max_file_size
        config = SourceCodeAnalyserConfig.from_properties({"max_file_size": 100})
        analyser = SourceCodeAnalyser(config)

        # Act
        result = analyser.process(
            [message],
            Schema("source_code", "1.0.0"),
        )

        # Assert - file should be skipped
        content = result.content
        assert len(content["data"]) == 0
        assert content["metadata"]["total_files"] == 0

    def test_process_handles_unsupported_language_gracefully(self):
        """Test graceful handling of unsupported language files."""
        # Arrange
        rust_content = 'fn main() { println!("Hello"); }'

        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Unsupported language test",
            description="Test with Rust file",
            source="/test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content=rust_content,
                    metadata=FilesystemMetadata(
                        source="/test/file.rs",
                        connector_type="filesystem_connector",
                        file_path="/test/file.rs",
                    ),
                ),
            ],
        )

        message = Message(
            id="test_unsupported",
            content=data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

        config = SourceCodeAnalyserConfig.from_properties({})
        analyser = SourceCodeAnalyser(config)

        # Act - should not raise exception
        result = analyser.process(
            [message],
            Schema("source_code", "1.0.0"),
        )

        # Assert - file skipped gracefully
        content = result.content
        assert isinstance(content, dict)
        assert len(content["data"]) == 0

    def test_process_empty_file_list_returns_valid_structure(self):
        """Test processing message with empty files array."""
        # Arrange
        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Empty test",
            description="Empty data array",
            source="/test",
            metadata={},
            data=[],
        )

        message = Message(
            id="test_empty",
            content=data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

        config = SourceCodeAnalyserConfig.from_properties({})
        analyser = SourceCodeAnalyser(config)

        # Act
        result = analyser.process(
            [message],
            Schema("source_code", "1.0.0"),
        )

        # Assert - valid structure with zero files
        content = result.content
        assert isinstance(content, dict)
        assert "data" in content
        assert len(content["data"]) == 0
        assert content["metadata"]["total_files"] == 0
        assert content["metadata"]["total_lines"] == 0

    def test_process_populates_last_modified_for_existing_files(self):
        """Test that last_modified timestamp is populated for files that exist on disk."""
        # Arrange - create a real temporary PHP file
        with tempfile.TemporaryDirectory() as tmpdir:
            php_file = Path(tmpdir) / "test.php"
            php_content = "<?php function testFunc() { return true; } ?>"
            php_file.write_text(php_content)

            # Ensure file exists before processing
            assert php_file.exists()

            data = StandardInputDataModel(
                schemaVersion="1.0.0",
                name="Last modified test",
                description="Test last_modified field population",
                source=str(tmpdir),
                metadata={},
                data=[
                    StandardInputDataItemModel(
                        content=php_content,
                        metadata=FilesystemMetadata(
                            source=str(php_file),
                            connector_type="filesystem_connector",
                            file_path=str(php_file),
                        ),
                    ),
                ],
            )

            message = Message(
                id="test_last_modified",
                content=data.model_dump(exclude_none=True),
                schema=Schema("standard_input", "1.0.0"),
            )

            config = SourceCodeAnalyserConfig.from_properties({})
            analyser = SourceCodeAnalyser(config)

            # Act
            result = analyser.process(
                [message],
                Schema("source_code", "1.0.0"),
            )

            # Assert
            content = result.content
            assert len(content["data"]) == 1

            parsed_file = content["data"][0]
            assert "metadata" in parsed_file

            file_metadata = parsed_file["metadata"]
            assert "last_modified" in file_metadata
            assert file_metadata["last_modified"] is not None
            assert isinstance(file_metadata["last_modified"], str)

            # Should be ISO 8601 format with timezone
            assert "T" in file_metadata["last_modified"]
            assert file_metadata["last_modified"].endswith("+00:00")
