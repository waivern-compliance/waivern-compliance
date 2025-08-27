"""Filesystem connector for WCT - handles files and directories."""

import fnmatch
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from typing_extensions import Self, override

from wct.connectors.base import (
    Connector,
    ConnectorConfigError,
    ConnectorExtractionError,
)
from wct.connectors.filesystem.config import FilesystemConnectorConfig
from wct.message import Message
from wct.schemas import Schema, StandardInputSchema

logger = logging.getLogger(__name__)

# Constants
_CONNECTOR_NAME = "filesystem"

_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [
    StandardInputSchema(),
]


class FilesystemConnector(Connector):
    """Filesystem connector that reads file or directory content for analysis.

    This connector can handle:
    - Single files: Reads the file content
    - Directories: Recursively reads all files in the directory
    - Pattern exclusion: Skip files/directories matching exclusion patterns

    Memory-efficient for large files by reading content in configurable chunks.
    """

    def __init__(self, config: FilesystemConnectorConfig) -> None:
        """Initialise the filesystem connector with validated configuration.

        Args:
            config: Validated filesystem connector configuration

        """
        self._config = config

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the connector."""
        return _CONNECTOR_NAME

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this connector."""
        return _SUPPORTED_OUTPUT_SCHEMAS

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
        config = FilesystemConnectorConfig.from_properties(properties)
        return cls(config)

    @override
    def extract(
        self,
        output_schema: Schema | None = None,
    ) -> Message:
        """Extract file content and metadata.

        Args:
            output_schema: Optional schema to use and validate against. Use the default
            schema of the current analyser if not provided.

        Returns:
            Dictionary containing file content and metadata in WCF schema format

        """
        try:
            output_schema = self._validate_is_supported_output_schema(output_schema)
            # After validation, we know output_schema is not None

            # Collect all files to process
            files_to_process = self.collect_files()
            logger.info(f"Found {len(files_to_process)} files to process")

            # Read all file contents
            all_file_data = self._collect_file_data(files_to_process)

            if not all_file_data:
                raise ConnectorExtractionError(
                    f"No readable files found in {self._config.path}"
                )

            # Transform content based on schema type
            wct_schema_transformed_content = self._transform_for_schema(
                output_schema, all_file_data
            )

            message = Message(
                id=f"Content from {self._config.path.name}",
                content=wct_schema_transformed_content,
                schema=output_schema,
            )

            message.validate()

            return message

        except Exception as e:
            logger.error(f"Failed to extract from path {self._config.path}: {e}")
            raise ConnectorExtractionError(
                f"Failed to read from path {self._config.path}: {e}"
            ) from e

    def _validate_is_supported_output_schema(
        self, output_schema: Schema | None
    ) -> Schema:
        """Validate that the provided schema is supported.

        Args:
            output_schema: The schema to validate

        Returns:
            The validated schema (or default if none provided)

        Raises:
            ConnectorConfigError: If schema is invalid or unsupported

        """
        if not output_schema:
            logger.warning("No schema provided, using default schema")
            output_schema = _SUPPORTED_OUTPUT_SCHEMAS[0]

        supported_schema_names = [schema.name for schema in _SUPPORTED_OUTPUT_SCHEMAS]
        if output_schema.name not in supported_schema_names:
            raise ConnectorConfigError(
                f"Unsupported output schema: {output_schema.name}. Supported schemas: {supported_schema_names}"
            )

        return output_schema

    def _collect_file_data(self, files_to_process: list[Path]) -> list[dict[str, Any]]:
        """Collect file content and metadata for all files.

        Args:
            files_to_process: List of file paths to process

        Returns:
            List of dictionaries containing file data with 'path', 'content', 'stat' keys

        """
        all_file_data: list[dict[str, Any]] = []

        for file_path in files_to_process:
            try:
                stat = file_path.stat()
                file_content = self._read_file_content(file_path)
                all_file_data.append(
                    {"path": file_path, "content": file_content, "stat": stat}
                )
                logger.debug(f"File {file_path} read successfully")
            except Exception as e:
                logger.warning(f"Skipping file {file_path}: {e}")
                continue

        return all_file_data

    def _transform_for_schema(
        self, schema: Schema, all_file_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Transform file content(s) based on the requested schema.

        Args:
            schema: The schema to transform content for
            all_file_data: List of file data dictionaries with 'path', 'content', 'stat' keys

        Returns:
            Schema-compliant transformed content

        """
        if schema.name == "standard_input":
            return self._transform_for_standard_input_schema(schema, all_file_data)

        raise ConnectorConfigError(f"Unsupported schema transformation: {schema.name}")

    def _transform_for_standard_input_schema(
        self, schema: Schema, all_file_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Transform file content(s) for the 'standard_input' schema.

        The standard_input schema supports multiple content pieces, making it perfect for
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
            schema: The standard_input schema to transform content for
            all_file_data: List of file data with 'path', 'content', 'stat' keys

        Returns:
            Dictionary conforming to the standard_input schema structure

        """
        # Calculate aggregate metadata
        total_size = sum(file_data["stat"].st_size for file_data in all_file_data)
        file_count = len(all_file_data)

        # Build data array with one entry per file
        data_entries: list[dict[str, Any]] = []
        for file_data in all_file_data:
            file_path = file_data["path"]
            content = file_data["content"]
            stat = file_data["stat"]

            data_entries.append(
                {
                    "content": content,
                    "metadata": {
                        "source": str(file_path),
                        "description": f"Content of {file_path.relative_to(self._config.path) if file_path != self._config.path else file_path.name}",
                        "file_size": stat.st_size,
                        "modified_time": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                        "created_time": datetime.fromtimestamp(
                            stat.st_ctime
                        ).isoformat(),
                        "permissions": oct(stat.st_mode)[-3:],
                    },
                }
            )

        # Determine source description
        if self._config.path.is_file():
            source_desc = f"Content from file {self._config.path.name}"
            name_suffix = self._config.path.name
        else:
            source_desc = (
                f"Content from directory {self._config.path.name} ({file_count} files)"
            )
            name_suffix = f"{self._config.path.name}_directory"

        return {
            "schemaVersion": schema.version,
            "name": f"standard_input_from_{name_suffix}",
            "description": source_desc,
            "contentEncoding": self._config.encoding,
            "source": str(self._config.path),
            "metadata": {
                "file_count": file_count,
                "total_size_bytes": total_size,
                "exclude_patterns": self._config.exclude_patterns,
                "source_type": "file" if self._config.path.is_file() else "directory",
            },
            "data": data_entries,
        }

    def collect_files(self) -> list[Path]:
        """Collect all files to process, handling both single files and directories.

        Returns:
            List of Path objects for files to process

        Raises:
            ConnectorExtractionError: If too many files are found or no files are found

        """
        if self._config.path.is_file():
            return [self._config.path]

        # Directory processing with recursive traversal
        files: list[Path] = []

        def should_exclude_path(path: Path) -> bool:
            """Check if a path should be excluded based on patterns."""
            path_str = str(path)
            relative_path = str(path.relative_to(self._config.path))

            for pattern in self._config.exclude_patterns:
                if (
                    fnmatch.fnmatch(path.name, pattern)
                    or fnmatch.fnmatch(relative_path, pattern)
                    or fnmatch.fnmatch(path_str, pattern)
                ):
                    return True
            return False

        # Recursively collect files
        for file_path in self._config.path.rglob("*"):
            if not file_path.is_file():
                continue

            if should_exclude_path(file_path):
                logger.debug(f"Excluding file: {file_path}")
                continue

            files.append(file_path)

            # Safety check
            if len(files) >= self._config.max_files:
                logger.warning(
                    f"Reached maximum file limit ({self._config.max_files}), stopping collection"
                )
                break

        if not files:
            raise ConnectorExtractionError(
                f"No files found in directory {self._config.path}"
            )

        logger.info(f"Collected {len(files)} files from {self._config.path}")
        return files

    def _read_file_content(self, file_path: Path | None = None) -> str:
        """Read file content efficiently for large files.

        Args:
            file_path: Path to file to read. If None, uses self._config.path

        """
        target_path = file_path or self._config.path
        try:
            # For small files, read all at once
            if target_path.stat().st_size <= self._config.chunk_size:
                return target_path.read_text(
                    encoding=self._config.encoding, errors=self._config.errors
                )

            # For large files, read in chunks
            logger.debug(
                f"Reading large file in chunks of {self._config.chunk_size} bytes"
            )
            content_parts: list[str] = []

            with open(
                target_path, encoding=self._config.encoding, errors=self._config.errors
            ) as f:
                while True:
                    chunk = f.read(self._config.chunk_size)
                    if not chunk:
                        break
                    content_parts.append(chunk)

            return "".join(content_parts)

        except UnicodeDecodeError as e:
            logger.info(f"Skipping binary file {target_path}: {e}")
            # Skip binary files as they're not suitable for text-based analysis
            raise ConnectorExtractionError(
                f"Binary file not suitable for text analysis: {target_path}"
            ) from e
