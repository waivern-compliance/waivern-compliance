"""Personal data analyser for Waivern Compliance Framework."""

from pathlib import Path

from waivern_core.schemas import SchemaRegistry

from .analyser import PersonalDataAnalyser
from .factory import PersonalDataAnalyserFactory
from .schemas import PersonalDataFindingModel
from .types import PersonalDataAnalyserConfig

# Register package schema directory with SchemaRegistry
_SCHEMA_DIR = Path(__file__).parent / "schemas" / "json_schemas"
SchemaRegistry.register_search_path(_SCHEMA_DIR)

__all__ = [
    "PersonalDataAnalyser",
    "PersonalDataAnalyserFactory",
    "PersonalDataFindingModel",
    "PersonalDataAnalyserConfig",
]
