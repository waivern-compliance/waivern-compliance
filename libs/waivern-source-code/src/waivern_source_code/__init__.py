"""Source code connector for WCF."""

from importlib.resources import files
from pathlib import Path

from waivern_core.schemas import SchemaRegistry

from .config import SourceCodeConnectorConfig
from .connector import SourceCodeConnector
from .factory import SourceCodeConnectorFactory
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
    "SourceCodeConnector",
    "SourceCodeConnectorConfig",
    "SourceCodeConnectorFactory",
    "SourceCodeDataModel",
    "SourceCodeFunctionModel",
    "SourceCodeClassModel",
    "register_schemas",
]
