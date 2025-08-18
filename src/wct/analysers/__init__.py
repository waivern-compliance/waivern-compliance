"""WCT analysers.

This package provides the core analyser system and built-in analysers
for the Waivern Compliance Tool (WCT).
"""

from wct.analysers.base import (
    Analyser,
    AnalyserError,
    AnalyserInputError,
    AnalyserProcessingError,
)
from wct.analysers.personal_data_analyser import (
    PersonalDataAnalyser,
    PersonalDataFindingModel,
)
from wct.analysers.processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
    ProcessingPurposeFindingModel,
)
from wct.analysers.types import LLMValidationConfig, PatternMatchingConfig

__all__ = (
    "Analyser",
    "AnalyserError",
    "AnalyserInputError",
    "AnalyserProcessingError",
    "PersonalDataAnalyser",
    "PersonalDataFindingModel",
    "ProcessingPurposeAnalyser",
    "ProcessingPurposeFindingModel",
    "LLMValidationConfig",
    "PatternMatchingConfig",
    "BUILTIN_ANALYSERS",
)

BUILTIN_ANALYSERS = (PersonalDataAnalyser, ProcessingPurposeAnalyser)
