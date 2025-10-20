# waivern-mysql

MySQL connector for Waivern Compliance Framework.

## Installation

```bash
pip install waivern-mysql
```

## Usage

```python
from waivern_mysql import MySQLConnector, MySQLConnectorConfig

# Configure connector
config = MySQLConnectorConfig(
    host="localhost",
    port=3306,
    user="root",
    password="password",
    database="mydb"
)

# Create connector
connector = MySQLConnector(config)

# Extract data
message = connector.extract()
```

## Dependencies

- waivern-core - Core framework abstractions
- waivern-connectors-database - Shared SQL utilities
- pymysql - MySQL database adapter
- cryptography - Secure password handling
- pydantic - Configuration validation

## License

See repository root for license information.
