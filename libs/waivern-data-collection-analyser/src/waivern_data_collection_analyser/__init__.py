"""Data collection analyser for detecting data collection mechanisms."""

from importlib.resources import files
from pathlib import Path

from waivern_core.schemas import SchemaRegistry

from .analyser import DataCollectionAnalyser
from .factory import DataCollectionAnalyserFactory
from .schemas import DataCollectionIndicatorModel
from .types import DataCollectionAnalyserConfig


def register_schemas() -> None:
    """Register schemas with SchemaRegistry.

    Called explicitly by WCF framework during initialisation.
    This function is referenced in pyproject.toml entry points.

    NO import-time side effects - registration is explicit.
    """
    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(Path(str(schema_dir)))


__all__ = [
    "DataCollectionAnalyser",
    "DataCollectionAnalyserConfig",
    "DataCollectionAnalyserFactory",
    "DataCollectionIndicatorModel",
    "register_schemas",
]
