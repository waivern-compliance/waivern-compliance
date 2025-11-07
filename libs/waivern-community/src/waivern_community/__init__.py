"""Community-contributed components for Waivern Compliance Framework."""

__version__ = "0.1.0"

# Connectors
from waivern_filesystem import FilesystemConnector, FilesystemConnectorFactory
from waivern_mysql import MySQLConnector, MySQLConnectorFactory

# Analysers - re-export from standalone packages and waivern_community
from waivern_personal_data_analyser import PersonalDataAnalyser

# Rulesets - re-export from waivern-rulesets for convenience
from waivern_rulesets import (
    PersonalDataRuleset,
    ProcessingPurposesRuleset,
    RulesetLoader,
)
from waivern_source_code import SourceCodeConnector, SourceCodeConnectorFactory
from waivern_sqlite import SQLiteConnector, SQLiteConnectorFactory

from waivern_community.analysers.processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
)

__all__ = [
    "__version__",
    # Connectors
    "FilesystemConnector",
    "FilesystemConnectorFactory",
    "MySQLConnector",
    "MySQLConnectorFactory",
    "SourceCodeConnector",
    "SourceCodeConnectorFactory",
    "SQLiteConnector",
    "SQLiteConnectorFactory",
    # Analysers
    "PersonalDataAnalyser",
    "ProcessingPurposeAnalyser",
    # Rulesets
    "PersonalDataRuleset",
    "ProcessingPurposesRuleset",
    "RulesetLoader",
]
