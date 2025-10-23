"""Schema for personal data analyser output."""

from ..types import PersonalDataFindingModel
from .personal_data_finding import PersonalDataFindingSchema

__all__ = [
    "PersonalDataFindingModel",
    "PersonalDataFindingSchema",
]
