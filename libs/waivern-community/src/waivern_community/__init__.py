"""Community-contributed components for Waivern Compliance Framework."""

__version__ = "0.1.0"

# Connectors
# Analysers
from waivern_community.analysers.personal_data_analyser import PersonalDataAnalyser
from waivern_community.analysers.processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
)
from waivern_community.connectors.filesystem import FilesystemConnector
from waivern_community.connectors.mysql import MySQLConnector
from waivern_community.connectors.source_code import SourceCodeConnector
from waivern_community.connectors.sqlite import SQLiteConnector

# Rulesets
from waivern_community.rulesets import (
    PersonalDataRuleset,
    ProcessingPurposesRuleset,
    RulesetLoader,
)

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
