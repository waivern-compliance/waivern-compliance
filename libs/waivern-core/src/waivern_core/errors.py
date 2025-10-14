"""Error classes for the Waivern Compliance Framework.

This module provides:
- WaivernError: Base exception class for all framework errors
- ConnectorError, ConnectorConfigError, ConnectorExtractionError: Connector exceptions
- MessageValidationError: Message validation exception
"""


class WaivernError(Exception):
    """Base exception for all Waivern Compliance Framework errors."""

    pass


class ConnectorError(WaivernError):
    """Base exception for connector-related errors."""

    pass


class ConnectorConfigError(ConnectorError):
    """Raised when connector configuration is invalid."""

    pass


class ConnectorExtractionError(ConnectorError):
    """Raised when data extraction fails."""

    pass


class MessageValidationError(WaivernError):
    """Raised when message validation fails."""

    pass
