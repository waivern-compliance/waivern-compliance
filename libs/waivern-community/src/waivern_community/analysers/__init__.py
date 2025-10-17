"""WCT analysers.

This package provides the core analyser system and built-in analysers
for the Waivern Compliance Tool (WCT).
"""

from waivern_core import (
    Analyser,
    AnalyserError,
    AnalyserInputError,
    AnalyserProcessingError,
)

from waivern_community.analysers.data_subject_analyser import (
    DataSubjectAnalyser,
    DataSubjectFindingModel,
)
from waivern_community.analysers.personal_data_analyser import (
    PersonalDataAnalyser,
    PersonalDataFindingModel,
)
from waivern_community.analysers.processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
    ProcessingPurposeFindingModel,
)
from waivern_community.analysers.types import LLMValidationConfig, PatternMatchingConfig

__all__ = (
    "Analyser",
    "AnalyserError",
    "AnalyserInputError",
    "AnalyserProcessingError",
    "DataSubjectAnalyser",
    "DataSubjectFindingModel",
    "PersonalDataAnalyser",
    "PersonalDataFindingModel",
    "ProcessingPurposeAnalyser",
    "ProcessingPurposeFindingModel",
    "LLMValidationConfig",
    "PatternMatchingConfig",
    "BUILTIN_ANALYSERS",
)

BUILTIN_ANALYSERS = (
    DataSubjectAnalyser,
    PersonalDataAnalyser,
    ProcessingPurposeAnalyser,
)
