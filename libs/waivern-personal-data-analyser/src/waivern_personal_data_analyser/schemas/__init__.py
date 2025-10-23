"""Schema for personal data analyser output."""

from .personal_data_finding import PersonalDataFindingSchema
from .types import PersonalDataFindingModel

__all__ = [
    "PersonalDataFindingModel",
    "PersonalDataFindingSchema",
]
