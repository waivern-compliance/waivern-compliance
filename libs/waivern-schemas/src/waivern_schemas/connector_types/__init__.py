"""Connector metadata types for Waivern Compliance Framework.

Re-exports from the current version (v1).
"""

from waivern_schemas.connector_types.v1 import (
    BaseMetadata,
    DocumentDatabaseMetadata,
    FilesystemMetadata,
    RelationalDatabaseMetadata,
)

__all__ = [
    "BaseMetadata",
    "DocumentDatabaseMetadata",
    "FilesystemMetadata",
    "RelationalDatabaseMetadata",
]
