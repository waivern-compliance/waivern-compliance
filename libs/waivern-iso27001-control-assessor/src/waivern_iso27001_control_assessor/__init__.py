"""ISO 27001 control assessor for Waivern Compliance Framework."""

from importlib.resources import files
from pathlib import Path

from waivern_core.schemas import SchemaRegistry

from .analyser import ISO27001Assessor
from .factory import ISO27001AssessorFactory
from .schemas import ISO27001AssessmentModel
from .types import ISO27001AssessorConfig


def register_schemas() -> None:
    """Register schemas with SchemaRegistry.

    Called explicitly by WCF framework during initialisation.
    This function is referenced in pyproject.toml entry points.

    NO import-time side effects - registration is explicit.
    """
    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(Path(str(schema_dir)))


__all__ = [
    "ISO27001Assessor",
    "ISO27001AssessorConfig",
    "ISO27001AssessorFactory",
    "ISO27001AssessmentModel",
    "register_schemas",
]
