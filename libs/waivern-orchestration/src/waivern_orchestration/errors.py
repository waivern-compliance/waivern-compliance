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


class InvalidPathError(OrchestrationError):
    """Raised when a child runbook path is invalid (absolute or contains '..')."""


class ChildRunbookNotFoundError(OrchestrationError):
    """Raised when a child runbook file cannot be found."""


class CircularRunbookError(OrchestrationError):
    """Raised when circular runbook references are detected (A → B → A)."""


class MissingInputMappingError(OrchestrationError):
    """Raised when required child runbook inputs are not mapped."""


class InvalidOutputMappingError(OrchestrationError):
    """Raised when output mapping references non-existent child artifact."""


class RunNotFoundError(OrchestrationError):
    """Raised when attempting to resume a non-existent run."""


class RunbookChangedError(OrchestrationError):
    """Raised when runbook has changed since the original run."""


class RunAlreadyActiveError(OrchestrationError):
    """Raised when attempting to resume a run that is already executing."""
