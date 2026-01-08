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

    def test_process_single_php_file(self):
        """Test analysing a single PHP file."""
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
        assert "data" in content
        assert "metadata" in content

        # Verify parsed data
        assert len(content["data"]) == 1
        file_data = content["data"][0]

        assert file_data["file_path"] == "/test/TestFile.php"
        assert file_data["language"] == "php"
        assert "raw_content" in file_data
        assert php_content in file_data["raw_content"]
        assert "metadata" in file_data

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
            assert "raw_content" in file_data
            assert "metadata" in file_data

    def test_process_with_language_filter_from_config(self):
        """Test that language config filters to only that language."""
        # Arrange - mixed input with PHP and TypeScript files
        php_content = "<?php function test() { return true; } ?>"
        ts_content = "const x: number = 42;"

        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Language filter test",
            description="Test filtering to PHP only",
            source="/test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content=php_content,
                    metadata=FilesystemMetadata(
                        source="/test/app.php",
                        connector_type="filesystem_connector",
                        file_path="/test/app.php",
                    ),
                ),
                StandardInputDataItemModel(
                    content=ts_content,
                    metadata=FilesystemMetadata(
                        source="/test/utils.ts",
                        connector_type="filesystem_connector",
                        file_path="/test/utils.ts",
                    ),
                ),
            ],
        )

        message = Message(
            id="test_lang_filter",
            content=data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

        # Config filters to PHP only
        config = SourceCodeAnalyserConfig.from_properties({"language": "php"})
        analyser = SourceCodeAnalyser(config)

        # Act
        result = analyser.process(
            [message],
            Schema("source_code", "1.0.0"),
        )

        # Assert - only PHP file should be processed
        content = result.content
        assert len(content["data"]) == 1
        assert content["data"][0]["language"] == "php"
        assert content["data"][0]["file_path"] == "/test/app.php"

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

    def test_process_calculates_line_count_correctly(self):
        """Test that line count is calculated correctly."""
        # Arrange
        php_content = "<?php\nline2\nline3\nline4\n?>"  # 5 lines

        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Line count test",
            description="Test line count calculation",
            source="/test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content=php_content,
                    metadata=FilesystemMetadata(
                        source="/test/test.php",
                        connector_type="filesystem_connector",
                        file_path="/test/test.php",
                    ),
                ),
            ],
        )

        message = Message(
            id="test_line_count",
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
        file_data = content["data"][0]
        assert file_data["metadata"]["line_count"] == 5
        assert content["metadata"]["total_lines"] == 5

    def test_process_handles_empty_file(self):
        """Test that empty files are handled correctly."""
        # Arrange
        php_content = ""  # Empty file

        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Empty file test",
            description="Test empty file handling",
            source="/test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content=php_content,
                    metadata=FilesystemMetadata(
                        source="/test/empty.php",
                        connector_type="filesystem_connector",
                        file_path="/test/empty.php",
                    ),
                ),
            ],
        )

        message = Message(
            id="test_empty_file",
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

        # Assert - empty file should still be processed
        content = result.content
        assert len(content["data"]) == 1
        file_data = content["data"][0]
        assert file_data["metadata"]["line_count"] == 0
        assert file_data["raw_content"] == ""


class TestSourceCodeAnalyserTypeScriptProcessing:
    """Test TypeScript language processing through the full pipeline."""

    def test_process_single_typescript_file(self):
        """Test analysing a single TypeScript file."""
        # Arrange
        ts_content = """
/**
 * User data processing function
 */
function processUserData(userData: UserData, options: Options): boolean {
    return sanitiseData(userData);
}

/**
 * User management class
 */
class UserManager {
    private users: User[] = [];

    /**
     * Creates new user account
     */
    public createUser(userData: UserData): User {
        return this.validateAndStore(userData);
    }
}
"""

        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="TypeScript file analysis",
            description="Single TypeScript file for testing",
            source="/test/TestFile.ts",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content=ts_content,
                    metadata=FilesystemMetadata(
                        source="/test/TestFile.ts",
                        connector_type="filesystem_connector",
                        file_path="/test/TestFile.ts",
                    ),
                ),
            ],
        )

        message = Message(
            id="test_single_ts",
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
        assert result.schema.name == "source_code"

        content = result.content
        assert len(content["data"]) == 1

        file_data = content["data"][0]
        assert file_data["language"] == "typescript"
        assert "raw_content" in file_data
        assert "processUserData" in file_data["raw_content"]
        assert "UserManager" in file_data["raw_content"]

    def test_process_skips_files_with_encoding_errors(self):
        """Test that files with encoding issues are skipped gracefully.

        Uses a lone surrogate character (U+D800) which is valid in Python
        strings but cannot be encoded to UTF-8, triggering UnicodeEncodeError.
        """
        # Arrange - content with lone surrogate that fails UTF-8 encoding
        # Lone surrogates (U+D800-U+DFFF) are invalid in UTF-8
        invalid_content = "<?php // \ud800 invalid surrogate ?>"

        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Encoding error test",
            description="Test file with encoding issues",
            source="/test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content=invalid_content,
                    metadata=FilesystemMetadata(
                        source="/test/invalid_encoding.php",
                        connector_type="filesystem_connector",
                        file_path="/test/invalid_encoding.php",
                    ),
                ),
            ],
        )

        message = Message(
            id="test_encoding_error",
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

        # Assert - file should be skipped gracefully
        content = result.content
        assert len(content["data"]) == 0
        assert content["metadata"]["total_files"] == 0

    def test_process_tsx_file(self):
        """Test analysing TSX file with React components."""
        # Arrange
        tsx_content = """
import React from 'react';

interface GreetingProps {
    name: string;
    showIcon?: boolean;
}

/**
 * Greeting component for user display
 */
const Greeting: React.FC<GreetingProps> = ({ name, showIcon }) => {
    return <div>Hello, {name}!</div>;
};

export default Greeting;
"""

        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="TSX file analysis",
            description="React component file",
            source="/test/Greeting.tsx",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content=tsx_content,
                    metadata=FilesystemMetadata(
                        source="/test/Greeting.tsx",
                        connector_type="filesystem_connector",
                        file_path="/test/Greeting.tsx",
                    ),
                ),
            ],
        )

        message = Message(
            id="test_tsx",
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

        file_data = content["data"][0]
        assert file_data["language"] == "typescript"
        assert "raw_content" in file_data
        assert "GreetingProps" in file_data["raw_content"]
        assert "Greeting" in file_data["raw_content"]
