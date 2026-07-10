"""Shared HTTP client service with authentication and resilience."""

from waivern_http.configuration import HttpClientServiceConfiguration
from waivern_http.errors import HttpAuthError, HttpConfigError, HttpServiceError
from waivern_http.service import HttpClientService

__all__ = [
    "HttpAuthError",
    "HttpClientService",
    "HttpClientServiceConfiguration",
    "HttpConfigError",
    "HttpServiceError",
]
