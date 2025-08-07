"""Source code connector for WCT."""

from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any

from typing_extensions import Self, override

from wct.connectors.base import (
    Connector,
    ConnectorConfigError,
    ConnectorExtractionError,
)
from wct.connectors.filesystem import FilesystemConnector
from wct.connectors.source_code.extractors import (
    ClassExtractor,
    FunctionExtractor,
)
from wct.connectors.source_code.parser import SourceCodeParser
from wct.message import Message
from wct.schema import WctSchema

SUPPORTED_OUTPUT_SCHEMAS = {
    "source_code": WctSchema(name="source_code", type=dict[str, Any]),
}

# Common file patterns to exclude from source code analysis
COMMON_EXCLUSIONS = [
    "*.pyc",
    "__pycache__",
    "*.class",
    "*.o",
    "*.so",
    "*.dll",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".DS_Store",
    "*.log",
    "*.tmp",
    "*.bak",
    "*.swp",
    "*.swo",
]


class SourceCodeConnector(Connector):
    """Connector that analyses source code for compliance information.

    This connector parses source code files using tree-sitter and extracts
    compliance-relevant information such as functions, classes, database
    interactions, data collection patterns, and AI/ML usage indicators.
    """

    def __init__(
        self,
        path: str | Path,
        language: str | None = None,
        file_patterns: list[str] | None = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB default
        max_files: int = 4000,  # Maximum number of files to process
    ):
        """Initialize the source code connector.

        Args:
            path: Path to source code file or directory
            language: Programming language (auto-detected if None)
            file_patterns: Glob patterns for file inclusion/exclusion
            max_file_size: Skip files larger than this size (bytes)
            max_files: Maximum number of files to process (default: 4000)
        """
        super().__init__()  # Initialize logger from base class
        self.path = Path(path)
        self.language = language
        self.file_patterns = file_patterns or ["**/*"]
        self.max_file_size = max_file_size
        self.max_files = max_files

        if not self.path.exists():
            raise ConnectorConfigError(f"Path does not exist: {self.path}")

        # Create filesystem connector for file collection with common exclusions
        self.file_collector = FilesystemConnector(
            path=path,
            exclude_patterns=COMMON_EXCLUSIONS,
            max_files=max_files,
            errors="strict",  # Skip binary files
        )

        # Initialize parser
        if self.path.is_file():
            detected_language = (
                language or SourceCodeParser().detect_language_from_file(self.path)
            )
            self.parser = SourceCodeParser(detected_language)
        else:
            # For directories, we'll create parsers as needed
            self.parser = None

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the connector."""
        return "source_code"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create a source code connector instance from configuration properties.

        Args:
            properties: Configuration properties dictionary containing:
                - path (str): Required. Path to source code file or directory.
                - language (str, optional): Programming language.
                - file_patterns (list[str], optional): File inclusion patterns.
                - max_file_size (int, optional): Maximum file size to process.
                - max_files (int, optional): Maximum number of files to process.

        Returns:
            Self: A new SourceCodeConnector instance.

        Raises:
            ConnectorConfigError: If required properties are missing.
        """
        path = properties.get("path")
        if not path:
            raise ConnectorConfigError("path property is required")

        return cls(
            path=path,
            language=properties.get("language"),
            file_patterns=properties.get("file_patterns"),
            max_file_size=properties.get("max_file_size", 10 * 1024 * 1024),
            max_files=properties.get("max_files", 4000),
        )

    @override
    def extract(
        self,
        output_schema: WctSchema[dict[str, Any]] | None = None,
    ) -> Message:
        """Extract source code analysis data.

        Args:
            output_schema: Optional schema to validate against

        Returns:
            Message containing source code analysis data

        Raises:
            ConnectorExtractionError: If extraction fails
        """
        try:
            # Validate schema
            if output_schema and output_schema.name not in SUPPORTED_OUTPUT_SCHEMAS:
                raise ConnectorConfigError(
                    f"Unsupported output schema: {output_schema.name}. "
                    f"Supported schemas: {list(SUPPORTED_OUTPUT_SCHEMAS.keys())}"
                )

            if not output_schema:
                self.logger.warning(
                    "No schema provided, using default source_code schema"
                )
                output_schema = SUPPORTED_OUTPUT_SCHEMAS["source_code"]

            # Analyze source code
            analysis_data = self._analyze_source_code()

            message = Message(
                id=f"Source code analysis from {self.path.name}",
                content=analysis_data,
                schema=output_schema,
            )

            message.validate()
            return message

        except Exception as e:
            self.logger.error(f"Failed to extract from source code {self.path}: {e}")
            raise ConnectorExtractionError(
                f"Failed to analyze source code {self.path}: {e}"
            ) from e

    def _analyze_source_code(self) -> dict[str, Any]:
        """Analyze source code and extract compliance information.

        Returns:
            Dictionary containing analysis results in schema format
        """
        if self.path.is_file():
            files_data, total_files, total_lines = self._analyze_single_file(self.path)
        else:
            files_data, total_files, total_lines = self._analyze_directory(self.path)

        return {
            "schemaVersion": "1.0.0",
            "name": f"source_code_analysis_{self.path.name}",
            "description": f"Source code analysis of {self.path}",
            "language": self.language or "auto-detected",
            "source": str(self.path),
            "metadata": {
                "total_files": total_files,
                "total_lines": total_lines,
                "analysis_timestamp": datetime.now().isoformat(),
                "parser_version": "tree-sitter-languages-1.15.0+",
            },
            "data": files_data,
        }

    def _analyze_single_file(
        self, file_path: Path
    ) -> tuple[list[dict[str, Any]], int, int]:
        """Analyze a single source code file.

        Args:
            file_path: Path to the file to analyze

        Returns:
            Tuple of (file data list, file count, total lines)
        """
        try:
            # Check file size
            if file_path.stat().st_size > self.max_file_size:
                self.logger.warning(f"Skipping large file: {file_path}")
                return [], 0, 0

            # Detect language if needed
            if not self.parser:
                language = SourceCodeParser().detect_language_from_file(file_path)
                self.parser = SourceCodeParser(language)

            # Parse file
            root_node, source_code = self.parser.parse_file(file_path)
            line_count = source_code.count("\n") + 1

            # Extract information
            file_data = self._extract_file_data(
                file_path, root_node, source_code, line_count
            )

            return [file_data], 1, line_count

        except Exception as e:
            self.logger.error(f"Failed to analyze file {file_path}: {e}")
            return [], 0, 0

    def _analyze_directory(
        self, dir_path: Path
    ) -> tuple[list[dict[str, Any]], int, int]:
        """Analyze all source code files in a directory.

        Args:
            dir_path: Path to the directory to analyze

        Returns:
            Tuple of (files data list, file count, total lines)
        """
        files_data = []
        total_files = 0
        total_lines = 0

        # File limits are now handled by the filesystem connector
        for file_path in self._get_source_files():
            file_data_list, file_count, line_count = self._analyze_single_file(
                file_path
            )
            files_data.extend(file_data_list)
            total_files += file_count
            total_lines += line_count

        self.logger.info(f"Processed {total_files} source code files")
        return files_data, total_files, total_lines

    def _get_source_files(self) -> Generator[Path, None, None]:
        """Get all source code files using filesystem connector with additional filtering.

        Yields:
            Source code file paths that are supported by the parser
        """
        # Use filesystem connector to collect files
        files_to_process = self.file_collector.collect_files()
        parser = SourceCodeParser()

        for file_path in files_to_process:
            # Apply source-code-specific filtering
            if parser.is_supported_file(file_path):
                # Apply file pattern matching if specified (inclusion patterns)
                if self.file_patterns != ["**/*"]:
                    # Check if file matches any of the inclusion patterns
                    matches_pattern = any(
                        file_path.match(pattern)
                        or file_path.name.endswith(pattern.replace("*", ""))
                        for pattern in self.file_patterns
                    )
                    if matches_pattern:
                        yield file_path
                else:
                    # No specific patterns, include all supported files
                    yield file_path

    def _extract_file_data(
        self, file_path: Path, root_node: Any, source_code: str, line_count: int
    ) -> dict[str, Any]:
        """Extract analysis data from a parsed file.

        Args:
            file_path: Path to the source file
            root_node: Parsed AST root node
            source_code: Original source code
            line_count: Number of lines in file

        Returns:
            File analysis data dictionary
        """
        # Detect language for this file
        language = (
            self.parser.language
            if self.parser
            else SourceCodeParser().detect_language_from_file(file_path)
        )

        # Initialize extractors
        function_extractor = FunctionExtractor(language)
        class_extractor = ClassExtractor(language)

        # Extract basic information
        file_data = {
            "file_path": str(
                file_path.relative_to(
                    self.path.parent if self.path.is_file() else self.path
                )
            ),
            "language": language,
            "functions": function_extractor.extract(root_node, source_code),
            "classes": class_extractor.extract(root_node, source_code),
            "imports": [],  # TODO: Implement import extractor
            "database_interactions": [],  # TODO: Implement database extractor
            "data_collection_indicators": [],  # TODO: Implement data collection extractor
            "ai_ml_indicators": [],  # TODO: Implement AI/ML extractor
            "security_patterns": [],  # TODO: Implement security extractor
            "third_party_integrations": [],  # TODO: Implement third-party extractor
            "metadata": {
                "file_size": file_path.stat().st_size,
                "line_count": line_count,
                "last_modified": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat(),
            },
        }

        return file_data
