"""Schema for source code connector output."""

from waivern_community.connectors.source_code.schemas.source_code import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeClassModel,
    SourceCodeClassPropertyModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
    SourceCodeFunctionModel,
    SourceCodeFunctionParameterModel,
    SourceCodeImportModel,
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
    "SourceCodeImportModel",
    "SourceCodeAnalysisMetadataModel",
]
