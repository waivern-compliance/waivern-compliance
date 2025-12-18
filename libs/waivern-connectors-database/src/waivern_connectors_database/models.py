"""Shared Pydantic models for database connectors.

This module provides typed models for both relational and document database
connectors, ensuring type safety throughout the extraction pipeline.
"""

from pydantic import BaseModel, Field

# =============================================================================
# Relational Database Models (MySQL, SQLite, PostgreSQL, etc.)
# =============================================================================


class ColumnMetadata(BaseModel):
    """Metadata for a database column."""

    name: str = Field(description="Column name")
    data_type: str = Field(description="SQL data type")
    is_nullable: bool = Field(description="Whether the column allows NULL")
    default: str | None = Field(default=None, description="Default value")
    comment: str | None = Field(default=None, description="Column comment")
    key: str | None = Field(default=None, description="Key type (PRI, UNI, MUL)")
    extra: str | None = Field(default=None, description="Extra info (auto_increment)")


class TableMetadata(BaseModel):
    """Metadata for a database table."""

    name: str = Field(description="Table name")
    table_type: str = Field(default="BASE TABLE", description="Table type")
    comment: str | None = Field(default=None, description="Table comment")
    estimated_rows: int | None = Field(default=None, description="Estimated row count")
    columns: list[ColumnMetadata] = Field(
        default_factory=list, description="Column metadata"
    )


class ServerInfo(BaseModel):
    """Database server connection information."""

    version: str = Field(description="Server version")
    host: str = Field(description="Server host")
    port: int = Field(description="Server port")


class RelationalExtractionMetadata(BaseModel):
    """Extraction metadata for relational databases."""

    database_name: str = Field(description="Database name")
    tables: list[TableMetadata] = Field(
        default_factory=list, description="Table metadata"
    )
    server_info: ServerInfo | None = Field(
        default=None, description="Server info (optional for embedded DBs)"
    )


class RelationalProducerConfig(BaseModel):
    """Configuration passed to relational database schema producers."""

    database: str = Field(description="Database name")
    max_rows_per_table: int = Field(description="Maximum rows extracted per table")
    host: str | None = Field(default=None, description="Database host")
    port: int | None = Field(default=None, description="Database port")
    user: str | None = Field(default=None, description="Database user")


# =============================================================================
# Document Database Models (MongoDB, AWS DocumentDB, etc.)
# =============================================================================


class CollectionMetadata(BaseModel):
    """Metadata for a document database collection."""

    name: str = Field(description="Collection name")
    document_count: int = Field(description="Estimated document count")


class DocumentExtractionMetadata(BaseModel):
    """Extraction metadata for document databases."""

    collections: list[CollectionMetadata] = Field(description="Collection metadata")


class DocumentProducerConfig(BaseModel):
    """Configuration passed to document database schema producers."""

    uri: str = Field(description="Database connection URI")
    database: str = Field(description="Database name")
    sample_size: int = Field(description="Sample size per collection")
