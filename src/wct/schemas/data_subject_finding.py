"""Data subject finding schema for WCT.

This module defines the DataSubjectFindingSchema class that represents
the output format for data subject analysis results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

from .base import BaseFindingSchema


@dataclass(frozen=True, slots=True, eq=False)
class DataSubjectFindingSchema(BaseFindingSchema):
    """Schema for data subject finding results.

    This schema represents the structured format used by data subject
    analysers to report findings about data subject categories discovered
    in various data sources for GDPR Article 30(1)(c) compliance.
    """

    _VERSION = "1.0.0"

    @property
    @override
    def name(self) -> str:
        """Return the schema name."""
        return "data_subject_finding"

    @property
    @override
    def version(self) -> str:
        """Return the schema version."""
        return self._VERSION
