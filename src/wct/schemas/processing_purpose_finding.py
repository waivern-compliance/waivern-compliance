"""Processing purpose finding schema for WCT.

This module defines the ProcessingPurposeFindingSchema class that represents
the output format for processing purpose analysis results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

from wct.schemas.base import BaseFindingSchema


@dataclass(frozen=True, slots=True, eq=False)
class ProcessingPurposeFindingSchema(BaseFindingSchema):
    """Schema for processing purpose finding results.

    This schema represents the structured format used by processing purpose
    analysers to report findings about GDPR processing purposes discovered
    in various data sources and code analysis.
    """

    _VERSION = "1.0.0"

    @property
    @override
    def name(self) -> str:
        """Return the schema name."""
        return "processing_purpose_finding"

    @property
    @override
    def version(self) -> str:
        """Return the schema version."""
        return self._VERSION
