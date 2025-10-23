"""Community-contributed components for Waivern Compliance Framework."""

__version__ = "0.1.0"

# Connectors
from waivern_mysql import MySQLConnector

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
from waivern_community.connectors.filesystem import FilesystemConnector
from waivern_community.connectors.source_code import SourceCodeConnector
from waivern_community.connectors.sqlite import SQLiteConnector

__all__ = [
    "__version__",
    # Connectors
    "FilesystemConnector",
    "MySQLConnector",
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
