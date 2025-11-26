"""Error types for orchestration failures."""


class OrchestrationError(Exception):
    """Base exception for all orchestration errors."""


class RunbookParseError(OrchestrationError):
    """Raised when runbook parsing fails."""


class CycleDetectedError(OrchestrationError):
    """Raised when a cycle is detected in the artifact dependency graph."""


class MissingArtifactError(OrchestrationError):
    """Raised when a referenced artifact does not exist."""


class SchemaCompatibilityError(OrchestrationError):
    """Raised when schemas are incompatible between connected artifacts."""


class ComponentNotFoundError(OrchestrationError):
    """Raised when a referenced component type is not found."""
