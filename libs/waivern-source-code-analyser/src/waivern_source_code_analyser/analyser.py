"""Source code analyser for WCF."""

import importlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any, override

from waivern_core import Analyser
from waivern_core.errors import AnalyserProcessingError
from waivern_core.message import Message
from waivern_core.schemas import Schema

from waivern_source_code_analyser.analyser_config import SourceCodeAnalyserConfig
from waivern_source_code_analyser.extractors import ClassExtractor, FunctionExtractor
from waivern_source_code_analyser.parser import SourceCodeParser

logger = logging.getLogger(__name__)


class SourceCodeAnalyser(Analyser):
    """Analyser that transforms file content to parsed source code structure.

    This analyser accepts standard_input schema (file content) and produces
    source_code schema (parsed code structure with functions, classes, etc.).
    """

    def __init__(self, config: SourceCodeAnalyserConfig) -> None:
        """Initialise the source code analyser with validated configuration.

        Args:
            config: Validated source code analyser configuration

        """
        self._config = config

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "source_code_analyser"

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[Schema]:
        """Return the input schemas supported by this analyser."""
        return [Schema("standard_input", "1.0.0")]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this analyser."""
        return [Schema("source_code", "1.0.0")]

    def _load_producer(self, schema: Schema) -> ModuleType:
        """Dynamically import producer module.

        Args:
            schema: The schema to load producer for

        Returns:
            Producer module with produce() function

        Raises:
            ModuleNotFoundError: If producer module doesn't exist for this version

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(
            f"waivern_source_code_analyser.schema_producers.{module_name}"
        )

    @override
    def process(
        self,
        input_schema: Schema,
        output_schema: Schema,
        message: Message,
    ) -> Message:
        """Process standard_input data to produce source_code output.

        Args:
            input_schema: Input schema (standard_input)
            output_schema: Output schema (source_code)
            message: Input message with file content

        Returns:
            Message containing parsed source code structure

        Raises:
            AnalyserProcessingError: If processing fails

        """
        try:
            # Validate input message
            Analyser.validate_input_message(message, input_schema)

            # Extract file data from standard_input
            input_data = message.content
            files_list = input_data.get("data", [])

            # Parse each file
            parsed_files: list[dict[str, Any]] = []
            total_files = 0
            total_lines = 0

            for file_entry in files_list:
                source_code = file_entry["content"]
                file_metadata = file_entry["metadata"]
                file_path_str = file_metadata.get(
                    "file_path", file_metadata.get("source", "unknown")
                )

                # Check source code size
                code_size = len(source_code.encode("utf-8"))
                if code_size > self._config.max_file_size:
                    logger.warning(
                        f"Skipping large source: {file_path_str} ({code_size} bytes)"
                    )
                    continue

                # Detect language or use config override
                file_path = Path(file_path_str)
                language = self._config.language or self._detect_language(file_path)

                if not language:
                    logger.warning(f"Could not detect language for: {file_path_str}")
                    continue

                try:
                    # Parse source code with tree-sitter
                    parser = SourceCodeParser(language)
                    root_node = parser.parse(source_code)

                    # Extract structural information
                    file_data = self._extract_file_data(
                        file_path, language, root_node, source_code
                    )
                    parsed_files.append(file_data)

                    total_files += 1
                    total_lines += source_code.count("\n") + 1

                except Exception as e:
                    logger.error(f"Failed to parse source: {file_path_str}: {e}")
                    continue

            # Determine source and language for output
            source_str = input_data.get("source", "standard_input")
            detected_language = self._config.language or (
                parsed_files[0]["language"] if parsed_files else "unknown"
            )

            # Load producer and transform to wire format
            producer = self._load_producer(output_schema)
            output_data = producer.produce(
                schema_version=output_schema.version,
                source_config={
                    "path_name": Path(source_str).name
                    if source_str != "standard_input"
                    else "analysed_files",
                    "path_str": source_str,
                    "language": detected_language,
                },
                analysis_summary={
                    "total_files": total_files,
                    "total_lines": total_lines,
                },
                files_data=parsed_files,
            )

            return Message(
                id="Source code analysis",
                content=output_data,
                schema=output_schema,
            )

        except Exception as e:
            logger.error(f"Failed to process source code: {e}")
            raise AnalyserProcessingError(f"Failed to analyse source code: {e}") from e

    def _detect_language(self, file_path: Path) -> str | None:
        """Detect programming language from file extension.

        Args:
            file_path: Path to the file

        Returns:
            Detected language or None if unsupported

        """
        try:
            return SourceCodeParser.detect_language_from_file(file_path)
        except Exception:
            # Unsupported language - return None to skip gracefully
            return None

    def _extract_file_data(
        self,
        file_path: Path,
        language: str,
        root_node: Any,  # noqa: ANN401  # Tree-sitter AST nodes are C bindings
        source_code: str,
    ) -> dict[str, Any]:
        """Extract analysis data from a parsed file.

        Args:
            file_path: Path to the source file
            language: Programming language
            root_node: Parsed AST root node
            source_code: Original source code

        Returns:
            File analysis data dictionary

        """
        # Initialise extractors
        function_extractor = FunctionExtractor(language)
        class_extractor = ClassExtractor(language)

        # Calculate line count
        line_count = source_code.count("\n") + 1

        # Get last modified timestamp if file exists on disk
        last_modified: str | None = None
        if file_path.exists():
            mtime = file_path.stat().st_mtime
            last_modified = datetime.fromtimestamp(mtime, tz=UTC).isoformat()

        # Extract pure structural information
        file_data = {
            "file_path": str(file_path),
            "language": language,
            "raw_content": source_code,
            "functions": function_extractor.extract(root_node, source_code),
            "classes": class_extractor.extract(root_node, source_code),
            "imports": [],  # TODO: Implement import extractor
            "metadata": {
                "file_size": len(source_code.encode("utf-8")),
                "line_count": line_count,
                "last_modified": last_modified,
            },
        }

        return file_data
