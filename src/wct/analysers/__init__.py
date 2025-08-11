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
from wct.analysers.personal_data_analyser import (
    PersonalDataAnalyser,
    PersonalDataFinding,
    PersonalDataPattern,
)
from wct.analysers.processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
)

__all__ = (
    "Analyser",
    "AnalyserConfig",
    "AnalyserError",
    "AnalyserInputError",
    "AnalyserProcessingError",
    "PersonalDataAnalyser",
    "PersonalDataFinding",
    "PersonalDataPattern",
    "ProcessingPurposeAnalyser",
    "BUILTIN_ANALYSERS",
)

BUILTIN_ANALYSERS = (PersonalDataAnalyser, ProcessingPurposeAnalyser)
