"""Schema for data subject analyser output."""

from waivern_community.analysers.data_subject_analyser.schemas.data_subject_finding import (
    DataSubjectFindingSchema,
)
from waivern_community.analysers.data_subject_analyser.schemas.types import (
    DataSubjectFindingModel,
)

__all__ = [
    "DataSubjectFindingModel",
    "DataSubjectFindingSchema",
]
