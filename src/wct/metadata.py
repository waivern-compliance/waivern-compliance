"""Metadata classes for WCT."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AnalysisMetadata(BaseModel):
    """Metadata for analysis results.

    This model provides a extensible structure for metadata that can be
    extended in the future for specific metadata types.
    """

    model_config = ConfigDict(extra="allow")
