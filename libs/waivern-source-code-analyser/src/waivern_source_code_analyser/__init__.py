"""Source code analyser for WCF.

This package provides SourceCodeAnalyser, which transforms file content
from standard_input schema to source_code schema with parsed code structure.

Use in pipeline: FilesystemConnector → SourceCodeAnalyser → ProcessingPurposeAnalyser
"""

from importlib.resources import files
from pathlib import Path

from waivern_core.schemas import SchemaRegistry

from .analyser import SourceCodeAnalyser
from .analyser_config import SourceCodeAnalyserConfig
from .analyser_factory import SourceCodeAnalyserFactory
from .schemas import (
    SourceCodeClassModel,
    SourceCodeDataModel,
    SourceCodeFunctionModel,
)


def register_schemas() -> None:
    """Register schemas with SchemaRegistry.

    Called explicitly by WCF framework during initialisation.
    This function is referenced in pyproject.toml entry points.

    NO import-time side effects - registration is explicit.
    """
    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(Path(str(schema_dir)))


__all__ = [
    "SourceCodeAnalyser",
    "SourceCodeAnalyserConfig",
    "SourceCodeAnalyserFactory",
    "SourceCodeDataModel",
    "SourceCodeFunctionModel",
    "SourceCodeClassModel",
    "register_schemas",
]
