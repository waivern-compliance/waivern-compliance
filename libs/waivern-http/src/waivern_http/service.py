"""Shared HTTP client service.

Wraps a single pooled ``httpx.AsyncClient`` with timeout enforcement and
auth-reference resolution. Credentials travel as a *reference* (a name); the
concrete secret is resolved from the environment at call time and never
persisted or logged.
"""

from __future__ import annotations

import os
import re

import httpx
from waivern_core import JsonValue

from waivern_http.configuration import HttpClientServiceConfiguration
from waivern_http.errors import HttpAuthError

# An auth reference must map cleanly onto an environment variable name.
_AUTH_REF_PATTERN = re.compile(r"[A-Za-z0-9_]+")


class HttpClientService:
    """Pooled async HTTP client with auth-reference resolution.

    A single ``httpx.AsyncClient`` provides connection pooling across all calls.
    The configured timeouts are bound to the client, so every request carries
    them. Auth references are resolved per call via ``WAIVERN_HTTP_AUTH_<REF>``.
    """

    def __init__(
        self,
        config: HttpClientServiceConfiguration,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Initialise the service with a pooled client built from config.

        Args:
            config: Timeouts and circuit-breaker thresholds.
            transport: Optional transport override for testing (e.g. an
                ``httpx.MockTransport``); production uses httpx's default.

        """
        timeout = httpx.Timeout(
            config.read_timeout_seconds, connect=config.connect_timeout_seconds
        )
        self._client = httpx.AsyncClient(timeout=timeout, transport=transport)

    async def request(
        self,
        method: str,
        url: str,
        *,
        auth_ref: str | None = None,
        json: JsonValue | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Issue an HTTP request, applying the resolved credential if any.

        Args:
            method: HTTP method (e.g. ``"GET"``, ``"POST"``).
            url: Absolute request URL.
            auth_ref: Credential name resolved to a Bearer token at call time;
                ``None`` sends no ``Authorization`` header.
            json: Optional JSON request body.
            headers: Optional additional request headers.

        Returns:
            The HTTP response.

        Raises:
            HttpAuthError: If ``auth_ref`` is malformed or its secret is unset.

        """
        request_headers = dict(headers or {})
        if auth_ref is not None:
            # AI-DEV-NOTE: `request_headers` now holds the resolved secret in the
            # Authorization value. Never log the headers, the request, or the
            # resolved secret — doing so leaks the credential to logs/artifacts.
            # The reference (auth_ref) is safe to log; the secret is not.
            request_headers["Authorization"] = (
                f"Bearer {self._resolve_secret(auth_ref)}"
            )

        return await self._client.request(
            method, url, json=json, headers=request_headers
        )

    async def aclose(self) -> None:
        """Close the underlying pooled client and its connections."""
        await self._client.aclose()

    def _resolve_secret(self, auth_ref: str) -> str:
        """Resolve an auth reference to a secret from the environment.

        Args:
            auth_ref: Credential name; must match ``[A-Za-z0-9_]+``.

        Returns:
            The secret value.

        Raises:
            HttpAuthError: If the reference is malformed or its env var is unset.

        """
        if not _AUTH_REF_PATTERN.fullmatch(auth_ref):
            raise HttpAuthError(
                f"Auth reference {auth_ref!r} is not a valid credential name "
                "(expected characters in [A-Za-z0-9_])"
            )

        env_var = f"WAIVERN_HTTP_AUTH_{auth_ref.upper()}"
        secret = os.getenv(env_var)
        if not secret:
            raise HttpAuthError(
                f"No secret found for auth reference {auth_ref!r} "
                f"(expected environment variable {env_var})"
            )
        return secret
