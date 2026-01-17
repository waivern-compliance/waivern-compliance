"""Data subject analyser for detecting data subject categories."""

from importlib.resources import files
from pathlib import Path

from waivern_core.schemas import SchemaRegistry

from .analyser import DataSubjectAnalyser
from .factory import DataSubjectAnalyserFactory
from .schemas import DataSubjectIndicatorModel
from .types import DataSubjectAnalyserConfig


def register_schemas() -> None:
    """Register schemas with SchemaRegistry.

    Called explicitly by WCF framework during initialisation.
    This function is referenced in pyproject.toml entry points.

    NO import-time side effects - registration is explicit.
    """
    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(Path(str(schema_dir)))


__all__ = [
    "DataSubjectAnalyser",
    "DataSubjectAnalyserConfig",
    "DataSubjectAnalyserFactory",
    "DataSubjectIndicatorModel",
    "register_schemas",
]
