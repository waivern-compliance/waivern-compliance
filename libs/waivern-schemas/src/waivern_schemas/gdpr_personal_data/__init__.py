"""GDPR personal data classification schema types.

Re-exports from the current version (v1).
"""

from waivern_schemas.gdpr_personal_data.v1 import (
    GDPRPersonalDataFindingMetadata,
    GDPRPersonalDataFindingModel,
    GDPRPersonalDataFindingOutput,
    GDPRPersonalDataSummary,
)

__all__ = [
    "GDPRPersonalDataFindingMetadata",
    "GDPRPersonalDataFindingModel",
    "GDPRPersonalDataFindingOutput",
    "GDPRPersonalDataSummary",
]
