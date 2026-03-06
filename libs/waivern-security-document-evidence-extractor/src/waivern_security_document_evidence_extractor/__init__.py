"""Security document evidence extractor for Waivern Compliance Framework."""

from importlib.resources import files
from pathlib import Path

from waivern_core.schemas import SchemaRegistry

from .extractor import SecurityDocumentEvidenceExtractor
from .factory import SecurityDocumentEvidenceExtractorFactory
from .schemas import SecurityDocumentContextModel


def register_schemas() -> None:
    """Register schemas with SchemaRegistry.

    Called explicitly by WCF framework during initialisation.
    This function is referenced in pyproject.toml entry points.

    NO import-time side effects - registration is explicit.
    """
    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(Path(str(schema_dir)))


__all__ = [
    "SecurityDocumentContextModel",
    "SecurityDocumentEvidenceExtractor",
    "SecurityDocumentEvidenceExtractorFactory",
    "register_schemas",
]
