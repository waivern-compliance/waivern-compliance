"""Shared database connector utilities for SQL databases."""

from .base_connector import DatabaseConnector
from .extraction_utils import DatabaseExtractionUtils
from .models import (
    CollectionMetadata,
    ColumnMetadata,
    DocumentExtractionMetadata,
    DocumentProducerConfig,
    RelationalExtractionMetadata,
    RelationalProducerConfig,
    ServerInfo,
    TableMetadata,
)

__all__ = [
    # Base utilities
    "DatabaseConnector",
    "DatabaseExtractionUtils",
    # Relational database models
    "ColumnMetadata",
    "TableMetadata",
    "ServerInfo",
    "RelationalExtractionMetadata",
    "RelationalProducerConfig",
    # Document database models
    "CollectionMetadata",
    "DocumentExtractionMetadata",
    "DocumentProducerConfig",
]
