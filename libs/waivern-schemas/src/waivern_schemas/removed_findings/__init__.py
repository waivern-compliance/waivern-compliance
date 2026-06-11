"""Removed findings audit-trail schema types.

Re-exports from the current version (v1).
"""

from waivern_schemas.removed_findings.v1 import (
    RemovedFinding,
    RemovedFindingsOutput,
)

__all__ = [
    "RemovedFinding",
    "RemovedFindingsOutput",
]
