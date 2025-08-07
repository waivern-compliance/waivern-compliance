"""Filesystem connector for WCT - handles files and directories."""

import fnmatch
from pathlib import Path
from typing import Any

from typing_extensions import Self, override

from wct.connectors.base import (
    Connector,
    ConnectorConfigError,
    ConnectorExtractionError,
)
from wct.message import Message
from wct.schema import WctSchema

SUPPORTED_OUTPUT_SCHEMAS = {
    "text": WctSchema(name="text", type=dict[str, Any]),
}


class FilesystemConnector(Connector):
    """Filesystem connector that reads file or directory content for analysis.

    This connector can handle:
    - Single files: Reads the file content
    - Directories: Recursively reads all files in the directory
    - Pattern exclusion: Skip files/directories matching exclusion patterns

    Memory-efficient for large files by reading content in configurable chunks.
    """

    def __init__(
        self,
        path: str | Path,
        chunk_size: int = 8192,
        encoding: str = "utf-8",
        errors: str = "strict",
        exclude_patterns: list[str] | None = None,
        max_files: int = 1000,
    ):
        """Initialize the filesystem connector.

        Args:
            path: Path to the file or directory to read
            chunk_size: Size of chunks to read at a time (bytes)
            encoding: Text encoding to use
            errors: How to handle encoding errors (strict=skip binary files, replace=convert to garbled text)
            exclude_patterns: List of glob patterns to exclude (e.g., ['*.log', '__pycache__'])
            max_files: Maximum number of files to process (safety limit)
        """
        super().__init__()  # Initialize logger from base class
        self.path = Path(path)
        self.chunk_size = chunk_size
        self.encoding = encoding
        self.errors = errors
        self.exclude_patterns = exclude_patterns or []
        self.max_files = max_files

        if not self.path.exists():
            raise ConnectorConfigError(f"Path does not exist: {self.path}")

        # Both files and directories are now supported
        if not (self.path.is_file() or self.path.is_dir()):
            raise ConnectorConfigError(f"Path must be a file or directory: {self.path}")

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the connector."""
        return "filesystem"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create a filesystem connector instance from configuration properties.

        This factory method creates a FilesystemConnector instance using configuration
        properties typically loaded from a YAML configuration file.

        Args:
            properties (dict[str, Any]): Configuration properties dictionary containing:
                - path (str): Required. The file or directory path to read from.
                - chunk_size (int, optional): Size of chunks to read at a time.
                Defaults to 8192 bytes.
                - encoding (str, optional): Text encoding to use when reading files.
                Defaults to "utf-8".
                - errors (str, optional): How to handle encoding errors.
                "strict" (default) skips binary files, "replace" converts to garbled text.
                - exclude_patterns (list[str], optional): Glob patterns to exclude.
                Defaults to empty list.
                - max_files (int, optional): Maximum number of files to process.
                Defaults to 1000.

        Returns:
            Self: A new FilesystemConnector instance configured with the provided properties.

        Raises:
            ConnectorConfigError: If the required 'path' property is missing from
                the properties dictionary.

        Example:
            >>> properties = {
            ...     "path": "/path/to/directory",
            ...     "chunk_size": 4096,
            ...     "encoding": "utf-8",
            ...     "exclude_patterns": ["*.log", "__pycache__"]
            ... }
            >>> connector = FilesystemConnector.from_properties(properties)
        """
        path = properties.get("path")
        if not path:
            raise ConnectorConfigError("path property is required")

        chunk_size = properties.get("chunk_size", 8192)
        encoding = properties.get("encoding", "utf-8")
        errors = properties.get("errors", "strict")
        exclude_patterns = properties.get("exclude_patterns", [])
        max_files = properties.get("max_files", 1000)

        return cls(
            path=path,
            chunk_size=chunk_size,
            encoding=encoding,
            errors=errors,
            exclude_patterns=exclude_patterns,
            max_files=max_files,
        )

    @override
    def extract(
        self,
        output_schema: WctSchema[dict[str, Any]] | None = None,
    ) -> Message:
        """Extract file content and metadata.

        Args:
            output_schema: Optional schema to use and validate against. Use the default
            schema of the current analyser if not provided.

        Returns:
            Dictionary containing file content and metadata in WCF schema format
        """
        try:
            # Check if a supported schema is provided
            if output_schema and output_schema.name not in SUPPORTED_OUTPUT_SCHEMAS:
                raise ConnectorConfigError(
                    f"Unsupported output schema: {output_schema.name}. Supported schemas: {SUPPORTED_OUTPUT_SCHEMAS.keys()}"
                )

            if not output_schema:
                self.logger.warning("No schema provided, using default text schema")
                raise ConnectorConfigError(
                    "No schema provided for data extraction. Please specify a valid WCT schema."
                )

            # Collect all files to process
            files_to_process = self._collect_files()
            self.logger.info(f"Found {len(files_to_process)} files to process")

            # Read all file contents
            all_file_data = []
            for file_path in files_to_process:
                try:
                    stat = file_path.stat()
                    file_content = self._read_file_content(file_path)
                    all_file_data.append(
                        {"path": file_path, "content": file_content, "stat": stat}
                    )
                    self.logger.debug(f"File {file_path} read successfully")
                except Exception as e:
                    self.logger.warning(f"Skipping file {file_path}: {e}")
                    continue

            if not all_file_data:
                raise ConnectorExtractionError(
                    f"No readable files found in {self.path}"
                )

            # Transform content based on schema type
            wct_schema_transformed_content = self._transform_for_schema(
                output_schema, all_file_data
            )

            message = Message(
                id=f"Content from {self.path.name}",
                content=wct_schema_transformed_content,
                schema=output_schema,
            )

            message.validate()

            return message

        except Exception as e:
            self.logger.error(f"Failed to extract from path {self.path}: {e}")
            raise ConnectorExtractionError(
                f"Failed to read from path {self.path}: {e}"
            ) from e

    def _transform_for_schema(
        self, schema: WctSchema[dict[str, Any]], all_file_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Transform file content(s) based on the requested schema.

        Args:
            schema: The schema to transform content for
            all_file_data: List of file data dictionaries with 'path', 'content', 'stat' keys

        Returns:
            Schema-compliant transformed content
        """
        if schema.name == "text":
            return self._transform_for_text_schema(schema, all_file_data)
        else:
            raise ConnectorConfigError(
                f"Unsupported schema transformation: {schema.name}"
            )

    def _transform_for_text_schema(
        self, schema: WctSchema[dict[str, Any]], all_file_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Transform file content(s) for the 'text' schema.

        The text schema supports multiple content pieces, making it perfect for
        aggregating multiple files from a directory into a single schema.

        Schema Structure:
        - schemaVersion: Version identifier for schema compatibility
        - name: Human-readable identifier for this content source
        - description: Brief description of the content
        - contentEncoding: Text encoding used (e.g., utf-8)
        - source: Original path for traceability
        - metadata: Overall metadata (file count, total size, etc.)
        - data: Array of content pieces, one per file

        Args:
            schema: The text schema to transform content for
            all_file_data: List of file data with 'path', 'content', 'stat' keys

        Returns:
            Dictionary conforming to the text schema structure
        """
        # Calculate aggregate metadata
        total_size = sum(file_data["stat"].st_size for file_data in all_file_data)
        file_count = len(all_file_data)

        # Build data array with one entry per file
        data_entries = []
        for file_data in all_file_data:
            file_path = file_data["path"]
            content = file_data["content"]
            stat = file_data["stat"]

            data_entries.append(
                {
                    "content": content,
                    "metadata": {
                        "source": str(file_path),
                        "description": f"Content of {file_path.relative_to(self.path) if file_path != self.path else file_path.name}",
                        "file_size": stat.st_size,
                        "modified_time": stat.st_mtime,
                        "created_time": stat.st_ctime,
                        "permissions": oct(stat.st_mode)[-3:],
                    },
                }
            )

        # Determine source description
        if self.path.is_file():
            source_desc = f"Content from file {self.path.name}"
            name_suffix = self.path.name
        else:
            source_desc = (
                f"Content from directory {self.path.name} ({file_count} files)"
            )
            name_suffix = f"{self.path.name}_directory"

        return schema.type(
            schemaVersion="1.0.0",
            name=f"text_from_{name_suffix}",
            description=source_desc,
            contentEncoding=self.encoding,
            source=str(self.path),
            metadata={
                "file_count": file_count,
                "total_size_bytes": total_size,
                "exclude_patterns": self.exclude_patterns,
                "source_type": "file" if self.path.is_file() else "directory",
            },
            data=data_entries,
        )

    def _collect_files(self) -> list[Path]:
        """Collect all files to process, handling both single files and directories.

        Returns:
            List of Path objects for files to process

        Raises:
            ConnectorExtractionError: If too many files are found or no files are found
        """
        if self.path.is_file():
            return [self.path]

        # Directory processing with recursive traversal
        files = []

        def should_exclude_path(path: Path) -> bool:
            """Check if a path should be excluded based on patterns."""
            path_str = str(path)
            relative_path = str(path.relative_to(self.path))

            for pattern in self.exclude_patterns:
                if (
                    fnmatch.fnmatch(path.name, pattern)
                    or fnmatch.fnmatch(relative_path, pattern)
                    or fnmatch.fnmatch(path_str, pattern)
                ):
                    return True
            return False

        # Recursively collect files
        for file_path in self.path.rglob("*"):
            if not file_path.is_file():
                continue

            if should_exclude_path(file_path):
                self.logger.debug(f"Excluding file: {file_path}")
                continue

            files.append(file_path)

            # Safety check
            if len(files) >= self.max_files:
                self.logger.warning(
                    f"Reached maximum file limit ({self.max_files}), stopping collection"
                )
                break

        if not files:
            raise ConnectorExtractionError(f"No files found in directory {self.path}")

        self.logger.info(f"Collected {len(files)} files from {self.path}")
        return files

    def _read_file_content(self, file_path: Path | None = None) -> str:
        """Read file content efficiently for large files.

        Args:
            file_path: Path to file to read. If None, uses self.path (for backward compatibility)
        """
        target_path = file_path or self.path
        try:
            # For small files, read all at once
            if target_path.stat().st_size <= self.chunk_size:
                return target_path.read_text(encoding=self.encoding, errors=self.errors)

            # For large files, read in chunks
            self.logger.debug(
                f"Reading large file in chunks of {self.chunk_size} bytes"
            )
            content_parts = []

            with open(target_path, encoding=self.encoding, errors=self.errors) as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    content_parts.append(chunk)

            return "".join(content_parts)

        except UnicodeDecodeError as e:
            self.logger.info(f"Skipping binary file {target_path}: {e}")
            # Skip binary files as they're not suitable for text-based analysis
            raise ConnectorExtractionError(
                f"Binary file not suitable for text analysis: {target_path}"
            ) from e
