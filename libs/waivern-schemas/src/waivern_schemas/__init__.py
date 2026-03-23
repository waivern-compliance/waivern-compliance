"""Centralised schema definitions for Waivern Compliance Framework.

This package owns all analysis schema definitions (Pydantic models and
generated JSON schemas). Producers and consumers depend on this package
instead of importing types from each other.

Each schema is a sub-package with directory-based versioning:
    from waivern_schemas.personal_data_indicator import PersonalDataIndicatorModel
"""

from importlib.resources import files
from pathlib import Path

from waivern_core.schemas import SchemaRegistry


def register_schemas() -> None:
    """Register all schemas with SchemaRegistry.

    Called explicitly by WCF framework during initialisation.
    This function is referenced in pyproject.toml entry points.

    NO import-time side effects - registration is explicit.
    """
    schema_dir = files(__name__) / "json_schemas"
    SchemaRegistry.register_search_path(Path(str(schema_dir)))


__all__ = [
    "register_schemas",
]
