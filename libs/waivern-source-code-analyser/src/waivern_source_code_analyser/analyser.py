"""Source code analyser for WCF."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override

from waivern_core import Analyser, InputRequirement
from waivern_core.errors import AnalyserProcessingError
from waivern_core.message import Message
from waivern_core.schemas import Schema

from waivern_source_code_analyser.analyser_config import SourceCodeAnalyserConfig
from waivern_source_code_analyser.languages.registry import LanguageRegistry
from waivern_source_code_analyser.schemas import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
)

logger = logging.getLogger(__name__)


class SourceCodeAnalyser(Analyser):
    """Analyser that transforms file content to source code with language detection.

    This analyser accepts standard_input schema (file content) and produces
    source_code schema (raw content with language identification).

    Structural extraction (functions, classes) has been intentionally removed -
    LLMs understand code structure natively from raw content. This analyser
    focuses on language detection and can be extended with compliance-relevant
    metadata (dependencies, frameworks, security patterns) in the future.
    """

    def __init__(self, config: SourceCodeAnalyserConfig) -> None:
        """Initialise the source code analyser with validated configuration.

        Args:
            config: Validated source code analyser configuration

        """
        self._config = config
        self._registry = LanguageRegistry()
        self._registry.discover()

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "source_code_analyser"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations.

        SourceCodeAnalyser accepts standard_input schema (file content).
        Multiple messages of the same schema are supported (fan-in).
        """
        return [
            [InputRequirement("standard_input", "1.0.0")],
        ]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this analyser."""
        return [Schema("source_code", "1.0.0")]

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process standard_input data to produce source_code output.

        Supports same-schema fan-in: multiple standard_input messages are merged
        before processing. Each file entry retains its original metadata for tracing.

        Args:
            inputs: List of input messages (same schema, fan-in supported)
            output_schema: Output schema (source_code)

        Returns:
            Message containing source code with language detection

        Raises:
            AnalyserProcessingError: If processing fails

        """
        try:
            # Merge all input data items (same-schema fan-in)
            all_files: list[dict[str, Any]] = []
            source_str = "standard_input"

            for message in inputs:
                input_data = message.content
                files_list = input_data.get("data", [])
                all_files.extend(files_list)
                # Use first non-default source
                if source_str == "standard_input" and input_data.get("source"):
                    source_str = input_data["source"]

            # Process each file
            parsed_files: list[SourceCodeFileDataModel] = []
            total_files = 0
            total_lines = 0

            for file_entry in all_files:
                source_code = file_entry["content"]
                file_metadata = file_entry["metadata"]
                file_path_str = file_metadata.get(
                    "file_path", file_metadata.get("source", "unknown")
                )

                # Check source code size (with encoding error handling)
                try:
                    code_size = len(source_code.encode("utf-8"))
                except (UnicodeEncodeError, UnicodeDecodeError):
                    logger.warning(
                        f"Skipping file with encoding issues: {file_path_str}"
                    )
                    continue

                if code_size > self._config.max_file_size:
                    logger.warning(
                        f"Skipping large source: {file_path_str} ({code_size} bytes)"
                    )
                    continue

                # Detect language from file extension
                file_path = Path(file_path_str)
                detected_language = self._detect_language(file_path)

                # If config specifies a language, only process files of that language
                if self._config.language:
                    if detected_language != self._config.language:
                        logger.debug(
                            f"Skipping file (not {self._config.language}): {file_path_str}"
                        )
                        continue
                    language = self._config.language
                else:
                    # No config filter - process all supported languages
                    if not detected_language:
                        logger.debug(f"Skipping unsupported file: {file_path_str}")
                        continue
                    language = detected_language

                # Build file data model
                file_data = self._build_file_data(file_path, language, source_code)
                parsed_files.append(file_data)

                total_files += 1
                total_lines += len(source_code.splitlines())

            # Determine path name for output
            path_name = (
                Path(source_str).name
                if source_str != "standard_input"
                else "analysed_files"
            )

            # Create output model (Pydantic validates at construction)
            output_model = SourceCodeDataModel(
                schemaVersion=output_schema.version,
                name=f"source_code_analysis_{path_name}",
                description=f"Source code analysis of {source_str}",
                source=source_str,
                metadata=SourceCodeAnalysisMetadataModel(
                    total_files=total_files,
                    total_lines=total_lines,
                    analysis_timestamp=datetime.now(UTC).isoformat(),
                ),
                data=parsed_files,
            )

            # Convert to wire format
            result_data = output_model.model_dump(mode="json", exclude_none=True)

            output_message = Message(
                id="Source_code_analysis",
                content=result_data,
                schema=output_schema,
            )

            logger.info(
                f"SourceCodeAnalyser processed {total_files} files, {total_lines} lines"
            )

            return output_message

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
        extension = file_path.suffix.lower()
        if not extension:
            return None

        try:
            language_support = self._registry.get_by_extension(extension)
            return language_support.name
        except Exception:
            # Unsupported extension - return None to skip gracefully
            return None

    def _build_file_data(
        self,
        file_path: Path,
        language: str,
        source_code: str,
    ) -> SourceCodeFileDataModel:
        """Build file data model from source code.

        Args:
            file_path: Path to the source file
            language: Programming language
            source_code: Original source code

        Returns:
            File data model with raw content and metadata

        """
        # Calculate line count correctly
        line_count = len(source_code.splitlines())

        # Get last modified timestamp if file exists on disk
        last_modified: str | None = None
        if file_path.exists():
            mtime = file_path.stat().st_mtime
            last_modified = datetime.fromtimestamp(mtime, tz=UTC).isoformat()

        return SourceCodeFileDataModel(
            file_path=str(file_path),
            language=language,
            raw_content=source_code,
            metadata=SourceCodeFileMetadataModel(
                file_size=len(source_code.encode("utf-8")),
                line_count=line_count,
                last_modified=last_modified,
            ),
        )
