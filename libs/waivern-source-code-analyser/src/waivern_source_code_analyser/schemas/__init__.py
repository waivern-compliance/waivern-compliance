"""Schema for source code connector output."""

from waivern_source_code_analyser.schemas.source_code import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeClassModel,
    SourceCodeClassPropertyModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
    SourceCodeFunctionModel,
    SourceCodeFunctionParameterModel,
    SourceCodeSchema,
)

__all__ = [
    "SourceCodeSchema",
    "SourceCodeDataModel",
    "SourceCodeFileDataModel",
    "SourceCodeFileMetadataModel",
    "SourceCodeFunctionModel",
    "SourceCodeFunctionParameterModel",
    "SourceCodeClassModel",
    "SourceCodeClassPropertyModel",
    "SourceCodeAnalysisMetadataModel",
]
