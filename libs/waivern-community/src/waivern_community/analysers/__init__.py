"""WCT analysers.

This package provides the core analyser system and built-in analysers
for the Waivern Compliance Tool (WCT).
"""

# Re-export shared types for convenience
from waivern_analysers_shared import LLMValidationConfig, PatternMatchingConfig
from waivern_core import (
    Analyser,
    AnalyserError,
    AnalyserInputError,
    AnalyserProcessingError,
)

# Import from standalone packages
from waivern_personal_data_analyser import (
    PersonalDataAnalyser,
    PersonalDataFindingModel,
)

# Import from waivern_community
from waivern_community.analysers.data_subject_analyser import (
    DataSubjectAnalyser,
    DataSubjectFindingModel,
)
from waivern_community.analysers.processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
    ProcessingPurposeFindingModel,
)

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
