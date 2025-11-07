# waivern-sqlite

SQLite connector for WCF

## Overview

The SQLite connector extracts database schema and data from SQLite databases for compliance analysis. It uses the shared database utilities from waivern-connectors-database.

Key features:
- Extract database schema (tables, columns, types)
- Extract sample data for analysis
- Configurable data sampling
- Supports SQLite 3.x databases

## Installation

```bash
pip install waivern-sqlite
```

## Usage

```python
from waivern_sqlite import SQLiteConnector, SQLiteConnectorConfig

# Extract from SQLite database
config = SQLiteConnectorConfig(
    database_path="/path/to/database.db",
    max_rows_per_table=100
)
connector = SQLiteConnector(config)
messages = connector.extract()
```

## Runbook Configuration

```yaml
connectors:
  - name: "compliance_sqlite_db"
    type: "sqlite_connector"
    properties:
      database_path: "./database.db"
      max_rows_per_table: 100
```

## Development

This package is part of the Waivern Compliance Framework monorepo. For development guidelines, testing, and contribution instructions, please refer to the main project documentation.
