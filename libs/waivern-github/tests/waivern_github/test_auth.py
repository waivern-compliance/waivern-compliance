"""Tests for GitHub authentication module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waivern_github.auth import GitHubAppAuth, PATAuth, create_auth
from waivern_github.config import GitHubConnectorConfig

# Test RSA private key (2048-bit, generated for testing only - not a real secret)
TEST_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAnJPOD+lZ1vOxefY4NDO62hr52X0+6Z1SmyPC6yGxWIjXNqEo
GXglKahILzYhlBbbynFd0T99ybykQxDHh5iytG9vdaEI5u+JQlTg4lAwgxeGwXib
50jTAVdqchco5DHTJZ1kKBfS9BiXPn1A8HRiHedbIv5gGt7Wtr1UZ8CCzlnsUPtB
HzQY7EDMxIzj7zRdHaoJFh32EWUAuDhJ9nU3C5k/reawQy5lpp5wJKWXfHLrjub5
bXFvS6jmsqIfnK04ihsGM0cbSt3BLaeYqxG6KM0Vu9g6pDmMvnqIS84QM3pLrpRt
0ncvekMlkqhZKzBXiMgUu1zFi9ncUCuu5ft1awIDAQABAoIBABaSmFpi4bjDWQqk
HGYqLv3SdcKM88zqCUakWS1cphyFXcFaalWBpJnk0MM9oome4gDFZykLZi73Kxcg
DCPYN6sbhY4HsSjZz4fohKMbvGKpuZuar58gOIsw9v+LpzF+nVoG3rGI/biC8wrn
M712ic6V0+WvlltJVNrzYH+0mSb2RgOGNoD3RgvTeHzkrCNwy5mEZqIhC6qWv6aL
OkAMUHtG5phumeWpfWU0+rlJMxzRUQk+OpYN6RhKhJ/231OECwGdBm3dyjtr1mTq
1o/nsY8aGaaSlRtU1n04g9thzoShbrHFrfo+OxwAgkwDpUIcoHw/Uf0Eh0HjyPmq
5XRAacECgYEAzeVANOr4qbiwj48NGwxUFFUmSeoMn9hWpVbLcgaEQtJYixy0YyFa
btWGaTjFlat2P/njYJKqMtrUIYXU7cBVhHEqOpOlr+UsOVlK5CVaIOInNxz/wKrH
PTWgp6511nm1r2LzH+bZM3r+GqIJJMaIjZIOPWuQfflFzkXmLAqUdV8CgYEAwq4p
woapy3Wiw5f81JaoYoQESNuoDGyUsNwJU58gaUm+YOnt9QKFoQNRsEMgDOzUaPc6
jT/+iMp5YPZMdI9MsEJXioP8rNPc1aC9Ek60vbmmt14igrOYaX2bM/a3HgWjI3hh
zIN0p2XrIZPm62dsG6khEbiJLud3zDZjA9sGz3UCgYBXyNSVO1GF2068BnvJ+nmm
qZ9HiFiVlkFrARSAqzKc4t4JgdWPJltOQg+qsR/c7lvebwZ42E9km1QybsMYExbi
/vTIQMc1tXojgWSi3SIOPx4FK4IHfUixWjoDBCkNpprGCmQqR9x3TIsmg8tuOI9j
/M/BdCkI7MzMY5T9Vg1x9QKBgDSk2BIMTDoCk4MExI/QNbR+MpJpI6ZIbmTs+3Cr
ZR5TnLGkUH6isfP6a8qYPECCgmXoBONRXMksx2na8I3MelZnejiwvFEX8W2rS7V5
pxJu85A+WmKxohNUrfV9T8NEjvr2gKvHGHJz8wNfdWBO1UMdlx2toxsV6KVGR7wx
LERJAoGAabcyAwMcOffiuPVXPp15NNwdoYPgjr+WA6jbJn7Xnqh8jsfhAEyP5svR
GNsXYeI9wGVTvqtTlM0mmW75I9X5oZJtzXyAwiSw8bQTW4PSLH89C5jCbKyLsJoB
etSwzDZ4IRDSvUTsYZ1wMJJdEUHZljj8iPpbiivcOXaKelu++So=
-----END RSA PRIVATE KEY-----"""


class TestPATAuth:
    """Tests for PATAuth class."""

    def test_get_token_returns_stored_token(self) -> None:
        """Test that get_token returns the token passed to constructor."""
        auth = PATAuth("ghp_test_token_12345")

        result = auth.get_token()

        assert result == "ghp_test_token_12345"


class TestGitHubAppAuth:
    """Tests for GitHubAppAuth class."""

    def test_get_token_returns_installation_token(self, tmp_path: Path) -> None:
        """Test that get_token returns token from GitHub API response."""
        # Create a test private key file
        key_file = tmp_path / "test-key.pem"
        key_file.write_text(TEST_PRIVATE_KEY)

        auth = GitHubAppAuth(
            app_id=12345,
            private_key_path=key_file,
            installation_id=67890,
        )

        with patch("waivern_github.auth.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"token": "ghs_installation_token_abc"}
            mock_post.return_value = mock_response

            result = auth.get_token()

        assert result == "ghs_installation_token_abc"

    def test_get_token_sends_jwt_to_github_api(self, tmp_path: Path) -> None:
        """Test that get_token sends JWT to correct GitHub API endpoint."""
        key_file = tmp_path / "test-key.pem"
        key_file.write_text(TEST_PRIVATE_KEY)

        auth = GitHubAppAuth(
            app_id=12345,
            private_key_path=key_file,
            installation_id=67890,
        )

        with patch("waivern_github.auth.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"token": "ghs_token"}
            mock_post.return_value = mock_response

            auth.get_token()

        # Verify correct URL
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert (
            call_args[0][0]
            == "https://api.github.com/app/installations/67890/access_tokens"
        )

        # Verify Bearer token header
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")

    def test_get_token_raises_error_on_api_failure(self, tmp_path: Path) -> None:
        """Test that get_token raises exception when GitHub API returns error."""
        import httpx

        key_file = tmp_path / "test-key.pem"
        key_file.write_text(TEST_PRIVATE_KEY)

        auth = GitHubAppAuth(
            app_id=12345,
            private_key_path=key_file,
            installation_id=67890,
        )

        with patch("waivern_github.auth.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                auth.get_token()

    def test_jwt_contains_required_claims(self, tmp_path: Path) -> None:
        """Test that JWT sent to GitHub contains iss, iat, exp claims."""
        import jwt as pyjwt

        key_file = tmp_path / "test-key.pem"
        key_file.write_text(TEST_PRIVATE_KEY)

        auth = GitHubAppAuth(
            app_id=12345,
            private_key_path=key_file,
            installation_id=67890,
        )

        captured_jwt = None

        with patch("waivern_github.auth.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"token": "ghs_token"}
            mock_post.return_value = mock_response

            def capture_jwt(*args, **kwargs):
                nonlocal captured_jwt
                auth_header = kwargs["headers"]["Authorization"]
                captured_jwt = auth_header.replace("Bearer ", "")
                return mock_response

            mock_post.side_effect = capture_jwt
            auth.get_token()

        # Decode JWT (without verification since we don't have public key)
        assert captured_jwt is not None, "JWT was not captured from request"
        decoded = pyjwt.decode(captured_jwt, options={"verify_signature": False})

        assert "iss" in decoded
        assert decoded["iss"] == 12345
        assert "iat" in decoded
        assert "exp" in decoded
        assert decoded["exp"] > decoded["iat"]


class TestCreateAuth:
    """Tests for create_auth factory function."""

    def test_returns_pat_auth_when_pat_method_with_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that create_auth returns PATAuth when PAT method with token."""
        # Clear env vars and set token
        for var in [
            "GITHUB_TOKEN",
            "GITHUB_APP_ID",
            "GITHUB_PRIVATE_KEY_PATH",
            "GITHUB_INSTALLATION_ID",
        ]:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        config = GitHubConnectorConfig.from_properties(
            {
                "repository": "owner/repo",
                "auth_method": "pat",
            }
        )

        result = create_auth(config)

        assert isinstance(result, PATAuth)
        assert result.get_token() == "ghp_test_token"

    def test_returns_none_when_pat_method_without_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that create_auth returns None for PAT method without token."""
        # Clear all env vars
        for var in [
            "GITHUB_TOKEN",
            "GITHUB_APP_ID",
            "GITHUB_PRIVATE_KEY_PATH",
            "GITHUB_INSTALLATION_ID",
        ]:
            monkeypatch.delenv(var, raising=False)

        config = GitHubConnectorConfig.from_properties(
            {
                "repository": "owner/repo",
                "auth_method": "pat",
            }
        )

        result = create_auth(config)

        assert result is None

    def test_returns_github_app_auth_when_app_method(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that create_auth returns GitHubAppAuth when app method."""
        # Clear all env vars first
        for var in [
            "GITHUB_TOKEN",
            "GITHUB_APP_ID",
            "GITHUB_PRIVATE_KEY_PATH",
            "GITHUB_INSTALLATION_ID",
        ]:
            monkeypatch.delenv(var, raising=False)

        # Set up GitHub App credentials
        key_file = tmp_path / "test-key.pem"
        key_file.write_text(TEST_PRIVATE_KEY)

        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_PRIVATE_KEY_PATH", str(key_file))
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")

        config = GitHubConnectorConfig.from_properties(
            {
                "repository": "owner/repo",
                "auth_method": "app",
            }
        )

        result = create_auth(config)

        assert isinstance(result, GitHubAppAuth)
