"""Filesystem connector for WCT - handles files and directories."""

import importlib
import logging
from pathlib import Path
from types import ModuleType
from typing import Any, override

import pathspec
from waivern_core import validate_output_schema
from waivern_core.base_connector import Connector
from waivern_core.errors import (
    ConnectorConfigError,
    ConnectorExtractionError,
)
from waivern_core.message import Message
from waivern_core.schemas import Schema

from waivern_filesystem.config import FilesystemConnectorConfig

logger = logging.getLogger(__name__)

# Constants
_CONNECTOR_NAME = "filesystem_connector"


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

    def _load_producer(self, schema: Schema) -> ModuleType:
        """Dynamically import producer module.

        Python's import system automatically caches modules in sys.modules,
        so repeated imports are fast and don't require manual caching.

        Args:
            schema: The schema to load producer for

        Returns:
            Producer module with produce() function

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(
            f"waivern_filesystem.schema_producers.{module_name}"
        )

    @override
    def extract(self, output_schema: Schema) -> Message:
        """Extract file content and metadata.

        Args:
            output_schema: Schema to validate against and use for output transformation.

        Returns:
            Message containing file content and metadata in WCF schema format.

        Raises:
            ConnectorConfigError: If schema is not supported.
            ConnectorExtractionError: If extraction fails.

        """
        try:
            validate_output_schema(output_schema, self.get_supported_output_schemas())

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

            return message

        except (ConnectorConfigError, ConnectorExtractionError):
            # Re-raise connector errors as-is (don't wrap config errors)
            raise
        except Exception as e:
            logger.error(f"Failed to extract from path {self._config.path}: {e}")
            raise ConnectorExtractionError(
                f"Failed to read from path {self._config.path}: {e}"
            ) from e

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
        """Transform file content(s) for the 'standard_input' schema using producer module.

        Args:
            schema: The standard_input schema to transform content for
            all_file_data: List of file data with 'path', 'content', 'stat' keys

        Returns:
            Dictionary conforming to the standard_input schema structure

        """
        # Load the appropriate producer for this schema version
        producer = self._load_producer(schema)

        # Prepare config data for producer
        config_data = {
            "path": self._config.path,
            "encoding": self._config.encoding,
            "exclude_patterns": self._config.exclude_patterns,
            "is_file": self._config.path.is_file(),
        }

        # Delegate transformation to producer
        return producer.produce(
            schema_version=schema.version,
            all_file_data=all_file_data,
            config_data=config_data,
        )

    def _should_include_path(
        self,
        path: Path,
        include_spec: pathspec.PathSpec | None,
        exclude_spec: pathspec.PathSpec | None,
    ) -> bool:
        """Check if a path should be included based on patterns.

        Uses pathspec library for Git-style wildmatch semantics where
        **/*.php matches both root-level and nested PHP files.

        Supports layered filtering when both patterns are specified:
        1. Include patterns applied first (file must match to be considered)
        2. Exclude patterns applied second (file must NOT match to be included)

        Args:
            path: File path to check
            include_spec: Compiled include pattern spec (or None)
            exclude_spec: Compiled exclude pattern spec (or None)

        Returns:
            True if path should be included, False otherwise

        """
        relative_path = str(path.relative_to(self._config.path))

        # Layer 1: Include patterns (positive filtering) - file must match
        if include_spec is not None:
            if not include_spec.match_file(relative_path):
                return False

        # Layer 2: Exclude patterns (negative filtering) - file must NOT match
        if exclude_spec is not None:
            if exclude_spec.match_file(relative_path):
                return False

        return True  # Passed all filters (or no patterns specified)

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

        # Create PathSpec once before loop for performance
        # Both can be set for layered filtering (include first, then exclude)
        include_spec: pathspec.PathSpec | None = None
        exclude_spec: pathspec.PathSpec | None = None

        if self._config.include_patterns is not None:
            include_spec = pathspec.PathSpec.from_lines(
                "gitwildmatch", self._config.include_patterns
            )
        if self._config.exclude_patterns is not None:
            exclude_spec = pathspec.PathSpec.from_lines(
                "gitwildmatch", self._config.exclude_patterns
            )

        # Recursively collect files
        for file_path in self._config.path.rglob("*"):
            if not file_path.is_file():
                continue

            if not self._should_include_path(file_path, include_spec, exclude_spec):
                logger.debug(f"Filtering file: {file_path}")
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
