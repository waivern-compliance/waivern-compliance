"""Source code connector for WCT."""

import math
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

MAX_NODE_TEXT_LENGTH = 100  # Limit text length for AST nodes


class SourceCodeConnector(Connector):
    """Connector that analyzes source code for compliance information.

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
        include_syntax_tree: bool = False,
        analysis_depth: str = "detailed",
    ):
        """Initialize the source code connector.

        Args:
            path: Path to source code file or directory
            language: Programming language (auto-detected if None)
            file_patterns: Glob patterns for file inclusion/exclusion
            max_file_size: Skip files larger than this size (bytes)
            max_files: Maximum number of files to process (default: 4000)
            include_syntax_tree: Whether to include full AST in output
            analysis_depth: Level of analysis (basic, detailed, comprehensive)
        """
        super().__init__()  # Initialize logger from base class
        self.path = Path(path)
        self.language = language
        self.file_patterns = file_patterns or ["**/*"]
        self.max_file_size = max_file_size
        self.max_files = max_files
        self.include_syntax_tree = include_syntax_tree
        self.analysis_depth = analysis_depth

        if not self.path.exists():
            raise ConnectorConfigError(f"Path does not exist: {self.path}")

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
                - include_syntax_tree (bool, optional): Include full AST.
                - analysis_depth (str, optional): Analysis detail level.

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
            include_syntax_tree=properties.get("include_syntax_tree", False),
            analysis_depth=properties.get("analysis_depth", "detailed"),
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
        processed_files = 0

        for file_path in self._get_source_files(dir_path):
            if processed_files >= self.max_files:
                self.logger.warning(
                    f"Reached maximum file limit ({self.max_files}). "
                    f"Skipping remaining files in {dir_path}"
                )
                break

            file_data_list, file_count, line_count = self._analyze_single_file(
                file_path
            )
            files_data.extend(file_data_list)
            total_files += file_count
            total_lines += line_count
            processed_files += file_count

        if processed_files >= self.max_files:
            self.logger.info(
                f"Processed {processed_files} files (limit: {self.max_files})"
            )

        return files_data, total_files, total_lines

    def _get_source_files(self, dir_path: Path) -> Generator[Path, None, None]:
        """Get all source code files in directory matching patterns.

        Args:
            dir_path: Directory to search

        Yields:
            Source code file paths
        """
        parser = SourceCodeParser()

        for pattern in self.file_patterns:
            for file_path in dir_path.glob(pattern):
                if (
                    file_path.is_file()
                    and parser.is_supported_file(file_path)
                    and file_path.stat().st_size <= self.max_file_size
                ):
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
                "complexity_score": self._calculate_complexity_score(root_node),
                "last_modified": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat(),
            },
        }

        # Include syntax tree if requested
        if self.include_syntax_tree:
            file_data["syntax_tree"] = self._serialize_ast(root_node, source_code)

        return file_data

    def _calculate_complexity_score(self, root_node: Any) -> float:
        """Calculate a simple complexity score for the file.

        Args:
            root_node: AST root node

        Returns:
            Complexity score (higher = more complex)
        """
        # Simple complexity based on node count and depth
        node_count = self._count_nodes(root_node)
        max_depth = self._calculate_max_depth(root_node)

        # Simple formula: log of nodes + depth factor
        return round(math.log(max(node_count, 1)) + (max_depth * 0.5), 2)

    def _count_nodes(self, node: Any) -> int:
        """Count total nodes in AST.

        Args:
            node: AST node

        Returns:
            Total node count
        """
        count = 1
        for child in getattr(node, "children", []):
            count += self._count_nodes(child)
        return count

    def _calculate_max_depth(self, node: Any, current_depth: int = 0) -> int:
        """Calculate maximum depth of AST.

        Args:
            node: AST node
            current_depth: Current recursion depth

        Returns:
            Maximum depth
        """
        if not hasattr(node, "children") or not node.children:
            return current_depth

        max_child_depth = current_depth
        for child in node.children:
            child_depth = self._calculate_max_depth(child, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth

    def _serialize_ast(
        self, node: Any, source_code: str, max_depth: int = 3
    ) -> dict[str, Any]:
        """Serialize AST node to dictionary (simplified).

        Args:
            node: AST node
            source_code: Original source code
            max_depth: Maximum recursion depth

        Returns:
            Serialized AST dictionary
        """
        if max_depth <= 0:
            return {"type": getattr(node, "type", "unknown"), "truncated": True}

        ast_dict = {
            "type": getattr(node, "type", "unknown"),
            "start_line": getattr(node, "start_point", [0])[0] + 1,
            "end_line": getattr(node, "end_point", [0])[0] + 1,
        }

        # Add text content for leaf nodes or small nodes
        if (
            not hasattr(node, "children")
            or len(getattr(node, "children", [])) == 0
            or (
                hasattr(node, "end_byte")
                and hasattr(node, "start_byte")
                and node.end_byte - node.start_byte < MAX_NODE_TEXT_LENGTH
            )
        ):
            try:
                if hasattr(node, "start_byte") and hasattr(node, "end_byte"):
                    text = source_code.encode("utf-8")[
                        node.start_byte : node.end_byte
                    ].decode("utf-8")
                    ast_dict["text"] = text[:200]  # Limit text length
            except Exception as e:
                self.logger.warning(f"Failed to extract text from AST node: {e}")

        # Recursively serialize children (limited depth)
        if hasattr(node, "children") and node.children and max_depth > 1:
            ast_dict["children"] = [
                self._serialize_ast(child, source_code, max_depth - 1)
                for child in node.children[:10]  # Limit children count
            ]

        return ast_dict
