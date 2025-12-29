"""GitHub authentication strategies."""

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import override

import httpx
import jwt

from waivern_github.config import GitHubConnectorConfig


class GitHubAuth(ABC):
    """Abstract base class for GitHub authentication."""

    @abstractmethod
    def get_token(self) -> str:
        """Return token for Git clone URL."""


class PATAuth(GitHubAuth):
    """Personal Access Token authentication."""

    def __init__(self, token: str) -> None:
        """Initialise with PAT token."""
        self._token = token

    @override
    def get_token(self) -> str:
        """Return the stored token."""
        return self._token


class GitHubAppAuth(GitHubAuth):
    """GitHub App authentication (generates installation token)."""

    GITHUB_API_URL = "https://api.github.com"
    JWT_EXPIRY_SECONDS = 600  # 10 minutes (GitHub maximum)

    def __init__(
        self,
        app_id: int,
        private_key_path: Path,
        installation_id: int,
    ) -> None:
        """Initialise with GitHub App credentials."""
        self._app_id = app_id
        self._private_key = private_key_path.read_text()
        self._installation_id = installation_id

    @override
    def get_token(self) -> str:
        """Generate and return installation access token.

        Creates a JWT signed with the app's private key, then exchanges it
        for an installation access token via the GitHub API.

        Returns:
            Installation access token string.

        Raises:
            httpx.HTTPStatusError: If the GitHub API request fails.

        """
        jwt_token = self._create_jwt()
        return self._exchange_jwt_for_token(jwt_token)

    def _create_jwt(self) -> str:
        """Create a JWT for GitHub App authentication."""
        now = int(time.time())
        payload = {
            "iat": now,
            "exp": now + self.JWT_EXPIRY_SECONDS,
            "iss": self._app_id,
        }
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    def _exchange_jwt_for_token(self, jwt_token: str) -> str:
        """Exchange JWT for installation access token."""
        url = f"{self.GITHUB_API_URL}/app/installations/{self._installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
        }
        response = httpx.post(url, headers=headers)
        response.raise_for_status()
        return response.json()["token"]


def create_auth(config: GitHubConnectorConfig) -> GitHubAuth | None:
    """Create appropriate auth strategy based on config.

    Args:
        config: GitHub connector configuration.

    Returns:
        GitHubAuth instance or None if no authentication is needed.

    """
    if config.auth_method == "pat":
        if config.token:
            return PATAuth(config.token)
        return None

    if config.auth_method == "app":
        # Config validation ensures these are set when auth_method is "app"
        # We use explicit checks here for type safety (config already validated)
        if (
            config.app_id is None
            or config.private_key_path is None
            or config.installation_id is None
        ):
            msg = (
                "GitHub App auth requires app_id, private_key_path, and installation_id"
            )
            raise ValueError(msg)
        return GitHubAppAuth(
            app_id=config.app_id,
            private_key_path=config.private_key_path,
            installation_id=config.installation_id,
        )

    return None
