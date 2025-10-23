"""Schema for processing purpose analyser output."""

from waivern_community.analysers.processing_purpose_analyser.schemas.processing_purpose_finding import (
    ProcessingPurposeFindingSchema,
)
from waivern_community.analysers.processing_purpose_analyser.schemas.types import (
    ProcessingPurposeFindingModel,
)

__all__ = [
    "ProcessingPurposeFindingModel",
    "ProcessingPurposeFindingSchema",
]
