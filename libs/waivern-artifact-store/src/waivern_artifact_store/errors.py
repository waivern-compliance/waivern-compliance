"""Artifact store exceptions."""

from waivern_core.errors import WaivernError


class ArtifactStoreError(WaivernError):
    """Base exception for artifact store related errors."""

    pass


class ArtifactNotFoundError(ArtifactStoreError):
    """Exception raised when requested artifact does not exist."""

    pass
