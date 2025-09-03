"""Personal data finding schema for WCT.

This module defines the PersonalDataFindingSchema class that represents
the output format for personal data analysis results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

from .base import BaseFindingSchema


@dataclass(frozen=True, slots=True, eq=False)
class PersonalDataFindingSchema(BaseFindingSchema):
    """Schema for personal data finding results.

    This schema represents the structured format used by personal data
    analysers to report findings about personal data discovered in
    various data sources.
    """

    _VERSION = "1.0.0"

    @property
    @override
    def name(self) -> str:
        """Return the schema name."""
        return "personal_data_finding"

    @property
    @override
    def version(self) -> str:
        """Return the schema version."""
        return self._VERSION
