"""HTTP client service exceptions."""

from waivern_core.errors import ServiceConfigError, WaivernError


class HttpServiceError(WaivernError):
    """Base exception for HTTP client service related errors."""

    pass


class HttpConfigError(HttpServiceError, ServiceConfigError):
    """Exception raised when the HTTP client service is misconfigured.

    An HTTP-domain error (``HttpServiceError``) that also participates in the
    cross-service configuration category (``ServiceConfigError``), so callers can
    catch any service misconfiguration uniformly.
    """

    pass


class HttpAuthError(HttpServiceError):
    """Raised when an auth reference cannot be resolved to a secret.

    Covers both a malformed reference (a name that cannot form an environment
    variable) and a reference whose environment variable is unset.
    """

    pass
