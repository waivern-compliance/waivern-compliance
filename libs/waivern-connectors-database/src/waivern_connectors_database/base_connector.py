"""Base class for database connectors."""

import abc
from typing import override

from waivern_core.base_connector import Connector
from waivern_core.schemas import Schema


class DatabaseConnector(Connector, abc.ABC):
    """Abstract base class for all database connectors.

    Provides common functionality and interface for database connector types.
    Concrete implementations must provide database-specific connection and extraction logic.

    By default, all database connectors support the standard_input schema,
    but subclasses can override to support additional schemas.
    """

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by database connectors.

        Default implementation returns standard_input schema.
        Subclasses can override to support additional schemas.
        """
        return [Schema("standard_input", "1.0.0")]
