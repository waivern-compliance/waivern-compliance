import logging
from typing import Any
from contextlib import contextmanager

from typing_extensions import Self, override

from wct.connectors.base import (
    Connector,
    ConnectorConfigError,
    ConnectorExtractionError,
)
from wct.schema import WctSchema

logger = logging.getLogger(__name__)


class MySQLConnector(Connector[dict[str, Any]]):
    """MySQL database connector for extracting data and metadata.

    This connector connects to a MySQL database and can execute queries
    to extract data for compliance analysis.
    """

    def __init__(
        self,
        host: str,
        port: int = 3306,
        user: str = "",
        password: str | None = None,
        database: str = "",
        charset: str = "utf8mb4",
        autocommit: bool = True,
        connect_timeout: int = 10,
    ):
        """Initialize MySQL connector with connection parameters.

        Args:
            host: MySQL server hostname or IP address
            port: MySQL server port (default: 3306)
            user: Database username
            password: Database password
            database: Database name to connect to
            charset: Character set for the connection (default: utf8mb4)
            autocommit: Enable autocommit mode (default: True)
            connect_timeout: Connection timeout in seconds (default: 10)
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password or ""
        self.database = database
        self.charset = charset
        self.autocommit = autocommit
        self.connect_timeout = connect_timeout
        self._connection = None

        # Validate required parameters
        if not host:
            raise ConnectorConfigError("MySQL host is required")
        if not user:
            raise ConnectorConfigError("MySQL user is required")

    @classmethod
    @override
    def get_name(cls) -> str:
        """The name of the connector."""
        return "mysql"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create connector from configuration properties.

        Required properties:
        - host: MySQL server hostname
        - user: Database username

        Optional properties:
        - port: Server port (default: 3306)
        - password: Database password (default: "")
        - database: Database name (default: "")
        - charset: Character set (default: "utf8mb4")
        - autocommit: Enable autocommit (default: True)
        - connect_timeout: Connection timeout (default: 10)
        """
        host = properties.get("host")
        if not host:
            raise ConnectorConfigError("MySQL host info is required")

        user = properties.get("user")
        if not user:
            raise ConnectorConfigError("MySQL user info is required")

        return cls(
            host=host,
            port=properties.get("port", 3306),
            user=user,
            password=properties.get("password"),
            database=properties.get("database", ""),
            charset=properties.get("charset", "utf8mb4"),
            autocommit=properties.get("autocommit", True),
            connect_timeout=properties.get("connect_timeout", 10),
        )

    @contextmanager
    def get_connection(self):
        """Get a database connection context manager.

        This method creates a new connection each time it's called to ensure
        thread safety and avoid connection state issues.

        Yields:
            MySQL connection object

        Raises:
            ConnectorExtractionError: If connection fails
        """
        connection = None
        try:
            # Import pymysql here to make it an optional dependency
            try:
                import pymysql
            except ImportError as e:
                raise ConnectorExtractionError(
                    "pymysql is required for MySQL connector. Install with: uv add pymysql"
                ) from e

            logger.debug(f"Connecting to MySQL at {self.host}:{self.port}")

            connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=self.charset,
                autocommit=self.autocommit,
                connect_timeout=self.connect_timeout,
            )

            logger.debug("MySQL connection established")
            yield connection

        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            raise ConnectorExtractionError(f"MySQL connection failed: {e}") from e
        finally:
            if connection:
                connection.close()
                logger.debug("MySQL connection closed")

    def execute_query(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results.

        Args:
            query: SQL query to execute
            params: Optional query parameters for parameterized queries

        Returns:
            List of dictionaries representing query results

        Raises:
            ConnectorExtractionError: If query execution fails
        """
        try:
            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    logger.debug(f"Executing query: {query}")
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    # Get column names
                    columns = (
                        [desc[0] for desc in cursor.description]
                        if cursor.description
                        else []
                    )

                    # Fetch all results
                    rows = cursor.fetchall()

                    # Convert to list of dictionaries
                    results = []
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        results.append(row_dict)

                    logger.debug(f"Query returned {len(results)} rows")
                    return results

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise ConnectorExtractionError(f"Query execution failed: {e}") from e

    def get_database_metadata(self) -> dict[str, Any]:
        """Extract database metadata including tables, columns, and constraints.

        Returns:
            Dictionary containing database metadata
        """
        try:
            metadata: dict[str, Any] = {
                "database_name": self.database,
                "tables": [],
                "server_info": {},
            }

            with self.get_connection() as connection:
                # Get server information
                server_info = connection.get_server_info()
                metadata["server_info"] = {
                    "version": server_info,
                    "host": self.host,
                    "port": self.port,
                }

                # Get table information
                tables_query = """
                SELECT TABLE_NAME, TABLE_TYPE, TABLE_COMMENT, TABLE_ROWS
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME
                """

                tables = self.execute_query(tables_query, (self.database,))

                for table in tables:
                    table_info = {
                        "name": table["TABLE_NAME"],
                        "type": table["TABLE_TYPE"],
                        "comment": table["TABLE_COMMENT"],
                        "estimated_rows": table["TABLE_ROWS"],
                        "columns": [],
                    }

                    # Get column information for each table
                    columns_query = """
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT,
                           COLUMN_COMMENT, COLUMN_KEY, EXTRA
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                    """

                    columns = self.execute_query(
                        columns_query, (self.database, table["TABLE_NAME"])
                    )
                    table_info["columns"] = columns

                    metadata["tables"].append(table_info)

                return metadata

        except Exception as e:
            logger.error(f"Failed to extract database metadata: {e}")
            raise ConnectorExtractionError(
                f"Database metadata extraction failed: {e}"
            ) from e

    @override
    def extract(
        self, schema: WctSchema[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Extract data from MySQL database.

        This method extracts database metadata and can execute custom queries
        if specified in the configuration.

        Args:
            schema: Optional WCT schema for data validation

        Returns:
            Dictionary containing extracted data in WCF schema format
        """
        try:
            logger.info(f"Extracting data from MySQL database: {self.database}")

            # Test connection first
            with self.get_connection():
                logger.debug("MySQL connection test successful")

            # Extract database metadata
            metadata = self.get_database_metadata()

            return {
                "connection_info": {
                    "host": self.host,
                    "port": self.port,
                    "database": self.database,
                    "user": self.user,
                },
                "metadata": metadata,
                "extraction_timestamp": None,  # Could add timestamp here
            }

        except Exception as e:
            logger.error(f"MySQL extraction failed: {e}")
            raise ConnectorExtractionError(f"MySQL extraction failed: {e}") from e

    @override
    def get_output_schema(self) -> WctSchema[dict[str, Any]]:
        """Return the schema this connector produces."""
        return WctSchema(name="mysql_database", type=dict[str, Any])
