"""Artifact store exceptions."""

from waivern_core.errors import ServiceConfigError, WaivernError


class ArtifactStoreError(WaivernError):
    """Base exception for artifact store related errors."""

    pass


class ArtifactStoreConfigError(ArtifactStoreError, ServiceConfigError):
    """Raised when artifact store configuration is invalid.

    An artifact-store-domain error (``ArtifactStoreError``) that also participates
    in the cross-service configuration category (``ServiceConfigError``), so callers
    can catch any service misconfiguration uniformly.
    """

    pass


class ArtifactNotFoundError(ArtifactStoreError):
    """Exception raised when requested artifact does not exist."""

    pass
