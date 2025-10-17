# waivern-connectors-database

Shared database connector utilities for SQL databases in Waivern Compliance Framework.

## Overview

This package provides common utilities and base classes for implementing SQL database connectors in the Waivern Compliance Framework. It follows Apache Airflow's `common-sql` pattern for shared database functionality.

## Components

- **DatabaseConnector** - Abstract base class for SQL database connectors
- **DatabaseExtractionUtils** - Utilities for cell filtering and data item creation
- **DatabaseSchemaUtils** - Schema validation utilities

## Usage

This package is typically used as a dependency for specific database connector packages:

```python
from waivern_connectors_database import (
    DatabaseConnector,
    DatabaseExtractionUtils,
    DatabaseSchemaUtils,
)

class MyDatabaseConnector(DatabaseConnector):
    # Implement your database-specific connector
    pass
```

## Database Connectors Using This Package

- `waivern-mysql` - MySQL connector
- `waivern-community` - Includes SQLite connector

## Installation

```bash
pip install waivern-connectors-database
```

This package is automatically installed as a dependency when you install database connector packages.

## License

See LICENSE file in the repository root.
