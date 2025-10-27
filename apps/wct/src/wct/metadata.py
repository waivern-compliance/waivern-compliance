"""Metadata classes for WCT."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AnalysisMetadata(BaseModel):
    """Metadata for analysis results.

    This model provides a extensible structure for metadata that can be
    extended in the future for specific metadata types.

    For additional fields beyond those defined, use model_validate():
        metadata = AnalysisMetadata.model_validate({"description": "...", "custom": "value"})
    """

    description: str | None = Field(
        default=None, description="Description of the analysis or metadata context"
    )

    model_config = ConfigDict(extra="allow")
