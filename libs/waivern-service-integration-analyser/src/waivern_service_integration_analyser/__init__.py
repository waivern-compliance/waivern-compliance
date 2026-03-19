"""Service integration analyser for detecting third-party service usage."""

from importlib.resources import files
from pathlib import Path

from waivern_core.schemas import SchemaRegistry

from .analyser import ServiceIntegrationAnalyser
from .factory import ServiceIntegrationAnalyserFactory
from .schemas import ServiceIntegrationIndicatorModel
from .types import ServiceIntegrationAnalyserConfig


def register_schemas() -> None:
    """Register schemas with SchemaRegistry.

    Called explicitly by WCF framework during initialisation.
    This function is referenced in pyproject.toml entry points.

    NO import-time side effects - registration is explicit.
    """
    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(Path(str(schema_dir)))


__all__ = [
    "ServiceIntegrationAnalyser",
    "ServiceIntegrationAnalyserConfig",
    "ServiceIntegrationAnalyserFactory",
    "ServiceIntegrationIndicatorModel",
    "register_schemas",
]
