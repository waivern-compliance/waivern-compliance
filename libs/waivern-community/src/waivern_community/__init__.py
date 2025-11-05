"""Community-contributed components for Waivern Compliance Framework."""

from pathlib import Path

from waivern_core.schemas import SchemaRegistry

__version__ = "0.1.0"

# TODO: Remove these schema path registrations once components are extracted.
# Future architecture:
#   - Community packages: community-xxxx-connector/analyser/ruleset
#   - Waivern packages: waivern-xxxx-connector/analyser/ruleset
# Each standalone package will register its own schema paths in its __init__.py
# Register schema search paths for waivern-community analysers (temporary)
_PROCESSING_PURPOSE_SCHEMA_DIR = (
    Path(__file__).parent
    / "analysers"
    / "processing_purpose_analyser"
    / "schemas"
    / "json_schemas"
)
_DATA_SUBJECT_SCHEMA_DIR = (
    Path(__file__).parent
    / "analysers"
    / "data_subject_analyser"
    / "schemas"
    / "json_schemas"
)
_SOURCE_CODE_SCHEMA_DIR = (
    Path(__file__).parent / "connectors" / "source_code" / "schemas" / "json_schemas"
)
SchemaRegistry.register_search_path(_PROCESSING_PURPOSE_SCHEMA_DIR)
SchemaRegistry.register_search_path(_DATA_SUBJECT_SCHEMA_DIR)
SchemaRegistry.register_search_path(_SOURCE_CODE_SCHEMA_DIR)

# Connectors
from waivern_mysql import MySQLConnector, MySQLConnectorFactory

# Analysers - re-export from standalone packages and waivern_community
from waivern_personal_data_analyser import PersonalDataAnalyser

# Rulesets - re-export from waivern-rulesets for convenience
from waivern_rulesets import (
    PersonalDataRuleset,
    ProcessingPurposesRuleset,
    RulesetLoader,
)

from waivern_community.analysers.processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
)
from waivern_community.connectors.filesystem import (
    FilesystemConnector,
    FilesystemConnectorFactory,
)
from waivern_community.connectors.source_code import SourceCodeConnector
from waivern_community.connectors.sqlite import SQLiteConnector

__all__ = [
    "__version__",
    # Connectors
    "FilesystemConnector",
    "FilesystemConnectorFactory",
    "MySQLConnector",
    "MySQLConnectorFactory",
    "SourceCodeConnector",
    "SQLiteConnector",
    # Analysers
    "PersonalDataAnalyser",
    "ProcessingPurposeAnalyser",
    # Rulesets
    "PersonalDataRuleset",
    "ProcessingPurposesRuleset",
    "RulesetLoader",
]
