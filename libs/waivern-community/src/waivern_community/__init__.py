"""Community-contributed components for Waivern Compliance Framework."""

__version__ = "0.1.0"

# Connectors
# Analysers - re-export from standalone packages
from waivern_data_subject_analyser import DataSubjectAnalyser
from waivern_filesystem import FilesystemConnector, FilesystemConnectorFactory
from waivern_mysql import MySQLConnector, MySQLConnectorFactory
from waivern_personal_data_analyser import PersonalDataAnalyser
from waivern_processing_purpose_analyser import ProcessingPurposeAnalyser

# Rulesets - re-export from waivern-rulesets for convenience
from waivern_rulesets import (
    PersonalDataRuleset,
    ProcessingPurposesRuleset,
    RulesetLoader,
)
from waivern_source_code import SourceCodeConnector, SourceCodeConnectorFactory
from waivern_sqlite import SQLiteConnector, SQLiteConnectorFactory

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
    "DataSubjectAnalyser",
    "PersonalDataAnalyser",
    "ProcessingPurposeAnalyser",
    # Rulesets
    "PersonalDataRuleset",
    "ProcessingPurposesRuleset",
    "RulesetLoader",
]
