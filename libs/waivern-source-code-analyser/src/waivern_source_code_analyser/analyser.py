"""Source code analyser for WCF."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override

from tree_sitter import Node
from waivern_core import Analyser, InputRequirement
from waivern_core.errors import AnalyserProcessingError
from waivern_core.message import Message
from waivern_core.schemas import Schema

from waivern_source_code_analyser.analyser_config import SourceCodeAnalyserConfig
from waivern_source_code_analyser.languages.models import (
    CallableModel,
    LanguageExtractionResult,
    TypeDefinitionModel,
)
from waivern_source_code_analyser.languages.registry import LanguageRegistry
from waivern_source_code_analyser.parser import SourceCodeParser
from waivern_source_code_analyser.schemas import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeClassModel,
    SourceCodeClassPropertyModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
    SourceCodeFunctionModel,
    SourceCodeFunctionParameterModel,
)

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
            Message containing parsed source code structure

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

            # Parse each file
            parsed_files: list[SourceCodeFileDataModel] = []
            total_files = 0
            total_lines = 0

            for file_entry in all_files:
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

                    # Extract structural information (returns typed model)
                    file_data = self._extract_file_data(
                        file_path, language, root_node, source_code
                    )
                    parsed_files.append(file_data)

                    total_files += 1
                    total_lines += source_code.count("\n") + 1

                except Exception as e:
                    logger.error(f"Failed to parse source: {file_path_str}: {e}")
                    continue

            # Determine language for output
            detected_language = self._config.language or (
                parsed_files[0].language if parsed_files else "unknown"
            )

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
                language=detected_language,
                source=source_str,
                metadata=SourceCodeAnalysisMetadataModel(
                    total_files=total_files,
                    total_lines=total_lines,
                    analysis_timestamp=datetime.now(UTC).isoformat(),
                ),
                data=parsed_files,  # Already typed as list[SourceCodeFileDataModel]
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
        try:
            return SourceCodeParser.detect_language_from_file(file_path)
        except Exception:
            # Unsupported language - return None to skip gracefully
            return None

    def _extract_file_data(
        self,
        file_path: Path,
        language: str,
        root_node: Node,
        source_code: str,
    ) -> SourceCodeFileDataModel:
        """Extract analysis data from a parsed file.

        Args:
            file_path: Path to the source file
            language: Programming language
            root_node: Parsed AST root node
            source_code: Original source code

        Returns:
            Strongly typed file data model

        """
        # Get language support from registry
        registry = LanguageRegistry()
        registry.discover()
        language_support = registry.get(language)

        # Extract using language-specific extractor
        extraction_result = language_support.extract(root_node, source_code)

        # Calculate line count
        line_count = source_code.count("\n") + 1

        # Get last modified timestamp if file exists on disk
        last_modified: str | None = None
        if file_path.exists():
            mtime = file_path.stat().st_mtime
            last_modified = datetime.fromtimestamp(mtime, tz=UTC).isoformat()

        # Convert extraction result to schema models
        functions = self._convert_callables_to_functions(extraction_result)
        classes = self._convert_type_definitions_to_classes(extraction_result)

        # Build strongly typed model
        return SourceCodeFileDataModel(
            file_path=str(file_path),
            language=language,
            raw_content=source_code,
            functions=functions,
            classes=classes,
            imports=[],  # TODO: Implement import extractor
            metadata=SourceCodeFileMetadataModel(
                file_size=len(source_code.encode("utf-8")),
                line_count=line_count,
                last_modified=last_modified,
            ),
        )

    def _convert_callables_to_functions(
        self, result: LanguageExtractionResult
    ) -> list[SourceCodeFunctionModel]:
        """Convert extracted callables to schema function models.

        Only includes standalone callables (functions, arrow functions), not methods.
        Methods are included within their containing class.

        Args:
            result: Language extraction result

        Returns:
            List of function models for the schema

        """
        functions: list[SourceCodeFunctionModel] = []

        # Include both regular functions and arrow functions (standalone callables)
        standalone_kinds = {"function", "arrow_function"}
        for callable_model in result.callables:
            if callable_model.kind in standalone_kinds:
                functions.append(self._callable_to_function_model(callable_model))

        return functions

    def _convert_type_definitions_to_classes(
        self, result: LanguageExtractionResult
    ) -> list[SourceCodeClassModel]:
        """Convert extracted type definitions to schema class models.

        Args:
            result: Language extraction result

        Returns:
            List of class models for the schema

        """
        classes: list[SourceCodeClassModel] = []

        for type_def in result.type_definitions:
            classes.append(self._type_def_to_class_model(type_def))

        return classes

    def _callable_to_function_model(
        self, callable_model: CallableModel
    ) -> SourceCodeFunctionModel:
        """Convert a CallableModel to SourceCodeFunctionModel.

        Args:
            callable_model: The callable model from extraction

        Returns:
            Schema-compatible function model

        """
        parameters = [
            SourceCodeFunctionParameterModel(
                name=p.name,
                type=p.type,
                default_value=p.default_value,
            )
            for p in callable_model.parameters
        ]

        return SourceCodeFunctionModel(
            name=callable_model.name,
            line_start=callable_model.line_start,
            line_end=callable_model.line_end,
            parameters=parameters,
            return_type=callable_model.return_type,
            visibility=callable_model.visibility,
            is_static=callable_model.is_static,
            docstring=callable_model.docstring,
        )

    def _type_def_to_class_model(
        self, type_def: TypeDefinitionModel
    ) -> SourceCodeClassModel:
        """Convert a TypeDefinitionModel to SourceCodeClassModel.

        Args:
            type_def: The type definition model from extraction

        Returns:
            Schema-compatible class model

        """
        # Convert members to properties
        properties = [
            SourceCodeClassPropertyModel(
                name=m.name,
                type=m.type,
                visibility=m.visibility or "public",
                is_static=m.is_static,
                default_value=m.default_value,
            )
            for m in type_def.members
        ]

        # Convert methods to function models
        methods = [self._callable_to_function_model(m) for m in type_def.methods]

        return SourceCodeClassModel(
            name=type_def.name,
            line_start=type_def.line_start,
            line_end=type_def.line_end,
            extends=type_def.extends,
            implements=type_def.implements,
            properties=properties,
            methods=methods,
        )
