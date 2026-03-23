"""GDPR data collection classification schema types.

Re-exports from the current version (v1).
"""

from waivern_schemas.gdpr_data_collection.v1 import (
    GDPRDataCollectionFindingMetadata,
    GDPRDataCollectionFindingModel,
    GDPRDataCollectionFindingOutput,
    GDPRDataCollectionSummary,
)

__all__ = [
    "GDPRDataCollectionFindingMetadata",
    "GDPRDataCollectionFindingModel",
    "GDPRDataCollectionFindingOutput",
    "GDPRDataCollectionSummary",
]
