"""WCT analysers.

This package provides the core analyser system and built-in analysers
for the Waivern Compliance Tool (WCT).
"""

from wct.analysers.base import (
    Analyser,
    AnalyserConfig,
    AnalyserError,
    AnalyserInputError,
    AnalyserProcessingError,
)
from wct.analysers.file_content_analyser import FileContentAnalyser
from wct.analysers.personal_data_analyser import (
    PersonalDataAnalyser,
    PersonalDataFinding,
    PersonalDataPattern,
)
from wct.schema import WctSchema

__all__ = (
    "Analyser",
    "AnalyserConfig",
    "AnalyserError",
    "AnalyserInputError",
    "AnalyserProcessingError",
    "WctSchema",
    "FileContentAnalyser",
    "PersonalDataAnalyser",
    "PersonalDataFinding",
    "PersonalDataPattern",
    "BUILTIN_ANALYSERS",
)

BUILTIN_ANALYSERS = (FileContentAnalyser, PersonalDataAnalyser)
