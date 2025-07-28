"""File reader connector for WCT."""

from pathlib import Path
from collections.abc import Generator
from typing import Any

from typing_extensions import Self, override

from wct.connectors.base import (
    Connector,
    ConnectorConfigError,
    ConnectorExtractionError,
)
from wct.schema import WctSchema
from wct.message import Message

SUPPORTED_OUTPUT_SCHEMAS = {
    "text": WctSchema(name="text", type=dict[str, Any]),
}


class FileConnector(Connector):
    """Connector that reads file content for analysis.

    This connector is memory-efficient for large files by reading content
    in configurable chunks rather than loading the entire file into memory.
    """

    def __init__(
        self,
        file_path: str | Path,
        chunk_size: int = 8192,
        encoding: str = "utf-8",
        errors: str = "replace",
    ):
        """Initialize the file reader connector.

        Args:
            file_path: Path to the file to read
            chunk_size: Size of chunks to read at a time (bytes)
            encoding: Text encoding to use
            errors: How to handle encoding errors
        """
        super().__init__()  # Initialize logger from base class
        self.file_path = Path(file_path)
        self.chunk_size = chunk_size
        self.encoding = encoding
        self.errors = errors

        if not self.file_path.exists():
            raise ConnectorConfigError(f"File does not exist: {self.file_path}")

        if not self.file_path.is_file():
            raise ConnectorConfigError(f"Path is not a file: {self.file_path}")

    @classmethod
    @override
    def get_name(cls) -> str:
        """The name of the connector."""
        return "file_reader"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create a file connector instance from configuration properties.

        This factory method creates a FileConnector instance using configuration
        properties typically loaded from a YAML configuration file.

        Args:
            properties (dict[str, Any]): Configuration properties dictionary containing:
                - path (str): Required. The file path to read from.
                - chunk_size (int, optional): Size of chunks to read at a time.
                Defaults to 8192 bytes.
                - encoding (str, optional): Text encoding to use when reading the file.
                Defaults to "utf-8".
                - errors (str, optional): How to handle encoding errors.
                Defaults to "replace".

        Returns:
            Self: A new FileConnector instance configured with the provided properties.

        Raises:
            ConnectorConfigError: If the required 'path' property is missing from
                the properties dictionary.

        Example:
            >>> properties = {
            ...     "path": "/path/to/file.txt",
            ...     "chunk_size": 4096,
            ...     "encoding": "utf-8"
            ... }
            >>> connector = FileConnector.from_properties(properties)
        """

        file_path = properties.get("path")
        if not file_path:
            raise ConnectorConfigError("path property is required")

        chunk_size = properties.get("chunk_size", 8192)
        encoding = properties.get("encoding", "utf-8")
        errors = properties.get("errors", "replace")

        return cls(
            file_path=file_path, chunk_size=chunk_size, encoding=encoding, errors=errors
        )

    @override
    def extract(
        self, output_schema: WctSchema[dict[str, Any]] | None = None
    ) -> Message:
        """Extract file content and metadata.

        Args:
            schema: Optional schema to use and validate against. Use the default
            schema of the current plugin if not provided.

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

            # Get file metadata
            stat = self.file_path.stat()

            # Read file content efficiently
            file_content = self._read_file_content()
            self.logger.debug(f"File {self.file_path} read successfully")

            # Transform content based on schema type
            wct_schema_transformed_content = self._transform_for_schema(
                output_schema, file_content, stat
            )

            message = Message(
                id=f"Content from {self.file_path.name}",
                content=wct_schema_transformed_content,
                schema=output_schema,
            )

            message.validate()

            return message

        except Exception as e:
            self.logger.error(f"Failed to extract from file {self.file_path}: {e}")
            raise ConnectorExtractionError(
                f"Failed to read file {self.file_path}: {e}"
            ) from e

    def _transform_for_schema(
        self, schema: WctSchema[dict[str, Any]], file_content: str, stat: Any
    ) -> dict[str, Any]:
        """Transform file content based on the requested schema.

        Args:
            schema: The schema to transform content for
            file_content: Raw file content
            stat: File stat information

        Returns:
            Schema-compliant transformed content
        """
        if schema.name == "text":
            return self._transform_for_text_schema(schema, file_content, stat)
        else:
            raise ConnectorConfigError(
                f"Unsupported schema transformation: {schema.name}"
            )

    def _transform_for_text_schema(
        self, schema: WctSchema[dict[str, Any]], file_content: str, stat: Any
    ) -> dict[str, Any]:
        """Transform file content for the 'text' schema.

        Args:
            schema: The text schema
            file_content: Raw file content
            stat: File stat information

        Returns:
            Text schema compliant content
        """
        return schema.type(
            name=schema.name,
            description=f"Content from {self.file_path.name}",
            contentEncoding=self.encoding,
            source=str(self.file_path),
            metadata={
                "modified_time": stat.st_mtime,
                "created_time": stat.st_ctime,
                "permissions": oct(stat.st_mode)[-3:],
                "size_bytes": stat.st_size,
            },
            content=[{"text": file_content}],
        )

    def _read_file_content(self) -> str:
        """Read file content efficiently for large files."""
        try:
            # For small files, read all at once
            if self.file_path.stat().st_size <= self.chunk_size:
                return self.file_path.read_text(
                    encoding=self.encoding, errors=self.errors
                )

            # For large files, read in chunks
            self.logger.debug(
                f"Reading large file in chunks of {self.chunk_size} bytes"
            )
            content_parts = []

            with open(
                self.file_path, "r", encoding=self.encoding, errors=self.errors
            ) as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    content_parts.append(chunk)

            return "".join(content_parts)

        except UnicodeDecodeError as e:
            self.logger.warning(f"Unicode decode error in {self.file_path}: {e}")
            # Try reading as binary and decode with error handling
            return self._read_as_binary()

    def _read_as_binary(self) -> str:
        """Fallback method to read file as binary when text decoding fails."""
        self.logger.debug(f"Reading {self.file_path} as binary with error handling")

        content_parts = []
        with open(self.file_path, "rb") as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                # Decode chunk with error handling
                decoded_chunk = chunk.decode(self.encoding, errors=self.errors)
                content_parts.append(decoded_chunk)

        return "".join(content_parts)

    def read_streaming(self) -> Generator[str, None, None]:
        """Read file content as a generator for very large files.

        This method yields chunks of content without loading the entire file
        into memory, useful for extremely large files.

        Yields:
            String chunks from the file
        """
        self.logger.debug(f"Streaming file content from {self.file_path}")

        try:
            with open(
                self.file_path, "r", encoding=self.encoding, errors=self.errors
            ) as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    yield chunk

        except UnicodeDecodeError:
            # Fallback to binary reading
            with open(self.file_path, "rb") as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    yield chunk.decode(self.encoding, errors=self.errors)
