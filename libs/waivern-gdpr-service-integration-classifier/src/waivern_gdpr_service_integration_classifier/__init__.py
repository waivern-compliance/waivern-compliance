"""GDPR service integration classifier for Waivern Compliance Framework."""

from importlib.resources import files
from pathlib import Path

from waivern_core.schemas import SchemaRegistry

from .classifier import GDPRServiceIntegrationClassifier
from .factory import GDPRServiceIntegrationClassifierFactory
from .schemas import (
    GDPRServiceIntegrationFindingModel,
    GDPRServiceIntegrationFindingOutput,
)

__all__ = [
    "GDPRServiceIntegrationClassifier",
    "GDPRServiceIntegrationClassifierFactory",
    "GDPRServiceIntegrationFindingModel",
    "GDPRServiceIntegrationFindingOutput",
    "register_schemas",
]


def register_schemas() -> None:
    """Register schemas with SchemaRegistry.

    Called explicitly by WCF framework during initialisation.
    This function is referenced in pyproject.toml entry points.

    NO import-time side effects - registration is explicit.
    """
    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(Path(str(schema_dir)))
