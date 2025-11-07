"""Data export analyser for Waivern Compliance Framework (work in progress).

This package hosts vendor database tooling for TCF compliance analysis.
The analyser implementation is currently under development.
"""

from importlib.resources import files
from pathlib import Path

from waivern_core.schemas import SchemaRegistry

from .analyser import DataExportAnalyser
from .factory import DataExportAnalyserFactory
from .types import DataExportAnalyserConfig


def register_schemas() -> None:
    """Register schemas with SchemaRegistry.

    Called explicitly by WCF framework during initialisation.
    This function is referenced in pyproject.toml entry points.

    NO import-time side effects - registration is explicit.
    """
    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(Path(str(schema_dir)))


__all__ = [
    "DataExportAnalyser",
    "DataExportAnalyserFactory",
    "DataExportAnalyserConfig",
    "register_schemas",
]
