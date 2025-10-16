"""Waivern Community Schemas.

Schema organization after Phase 3 migration:

**Core shared schemas** (waivern-core):
- Import from: waivern_core.schemas
- Contains: StandardInputSchema, base types, validation utilities

**Component-specific schemas**:
- Analyser output schemas: Import from waivern_community.analysers.*.schemas
  - PersonalDataFindingSchema
  - ProcessingPurposeFindingSchema
  - DataSubjectFindingSchema

- Connector schemas: Import from waivern_community.connectors.*.schemas
  - SourceCodeSchema

This follows the principle: "components own their data contracts"
"""

__all__ = []
