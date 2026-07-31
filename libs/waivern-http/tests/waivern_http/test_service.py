"""Tests for HttpClientService."""

import logging

import httpx
import pytest

from waivern_http.configuration import HttpClientServiceConfiguration
from waivern_http.errors import HttpAuthError
from waivern_http.service import HttpClientService


class _RequestCapture:
    """A MockTransport handler that records every request it receives."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json={"ok": True})

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


def _make_service(
    capture: _RequestCapture,
    config: HttpClientServiceConfiguration | None = None,
) -> HttpClientService:
    """Build a service wired to a capturing in-process transport (no network)."""
    return HttpClientService(
        config or HttpClientServiceConfiguration(),
        transport=httpx.MockTransport(capture.handle),
    )


class TestAuthResolution:
    """Auth-reference resolution into request credentials."""

    async def test_auth_ref_resolves_secret_into_bearer_header(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A known auth_ref resolves its env secret into an Authorization header."""
        monkeypatch.setenv("WAIVERN_HTTP_AUTH_ACME_SAAS", "secret-123")
        capture = _RequestCapture()
        service = _make_service(capture)

        await service.request("GET", "https://example.com/x", auth_ref="acme_saas")

        assert capture.last.headers["Authorization"] == "Bearer secret-123"

    async def test_missing_secret_raises_http_auth_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An auth_ref whose env var is unset raises HttpAuthError."""
        monkeypatch.delenv("WAIVERN_HTTP_AUTH_ACME_SAAS", raising=False)
        capture = _RequestCapture()
        service = _make_service(capture)

        with pytest.raises(HttpAuthError):
            await service.request("GET", "https://example.com/x", auth_ref="acme_saas")

    async def test_malformed_auth_ref_raises_http_auth_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An auth_ref that cannot form an env var name raises HttpAuthError."""
        monkeypatch.setenv("WAIVERN_HTTP_AUTH_ACME_SAAS", "secret-123")
        capture = _RequestCapture()
        service = _make_service(capture)

        with pytest.raises(HttpAuthError):
            await service.request("GET", "https://example.com/x", auth_ref="acme.saas")

    async def test_no_auth_ref_sends_no_authorization_header(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With auth_ref=None, no Authorization header is sent."""
        capture = _RequestCapture()
        service = _make_service(capture)

        await service.request("GET", "https://example.com/x")

        assert "Authorization" not in capture.last.headers


class TestRequestBehaviour:
    """Transport, timeout, and logging behaviour of issued requests."""

    async def test_configured_timeout_applied_to_request(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The configured connect/read timeouts are applied to outgoing requests."""
        capture = _RequestCapture()
        config = HttpClientServiceConfiguration(
            connect_timeout_seconds=5.0, read_timeout_seconds=10.0
        )
        service = _make_service(capture, config)

        await service.request("GET", "https://example.com/x")

        timeout = capture.last.extensions["timeout"]
        assert timeout["connect"] == 5.0
        assert timeout["read"] == 10.0

    async def test_request_returns_response_from_transport(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """request() returns the response produced by the transport."""
        capture = _RequestCapture()
        service = _make_service(capture)

        response = await service.request("GET", "https://example.com/x")

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    async def test_secret_never_appears_in_logs(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """The resolved secret is never written to logs."""
        monkeypatch.setenv("WAIVERN_HTTP_AUTH_ACME_SAAS", "super-secret-value")
        capture = _RequestCapture()
        service = _make_service(capture)

        with caplog.at_level(logging.DEBUG):
            await service.request("GET", "https://example.com/x", auth_ref="acme_saas")

        assert "super-secret-value" not in caplog.text
