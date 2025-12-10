"""Error classes for the Waivern Compliance Framework.

This module provides:
- WaivernError: Base exception class for all framework errors
- ConnectorError, ConnectorConfigError, ConnectorExtractionError: Connector exceptions
- ProcessorError: Base exception for processor-related errors
- AnalyserError, AnalyserConfigError, AnalyserInputError, AnalyserProcessingError: Analyser exceptions
- ParserError: Parser-related exception
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


class ProcessorError(WaivernError):
    """Base exception for processor-related errors."""

    pass


class ProcessorConfigError(ProcessorError):
    """Raised when processor configuration is invalid."""

    pass


class ProcessorInputError(ProcessorError):
    """Raised when processor input data is invalid."""

    pass


class ProcessorProcessingError(ProcessorError):
    """Raised when processor processing fails."""

    pass


# Analyser-specific errors (extend ProcessorError for backwards compatibility)
class AnalyserError(ProcessorError):
    """Base exception for analyser-related errors."""

    pass


class AnalyserConfigError(AnalyserError):
    """Raised when analyser configuration is invalid."""

    pass


class AnalyserInputError(AnalyserError):
    """Raised when analyser input data is invalid."""

    pass


class AnalyserProcessingError(AnalyserError):
    """Raised when analyser processing fails."""

    pass


class MessageValidationError(WaivernError):
    """Raised when message validation fails."""

    pass


class ParserError(WaivernError):
    """Base exception for parser-related errors."""

    pass
