"""Integration tests for GitHub authentication methods."""

import os
import tempfile
from pathlib import Path

import pytest

from waivern_github.auth import GitHubAppAuth, PATAuth
from waivern_github.config import GitHubConnectorConfig
from waivern_github.git_operations import GitOperations

from .conftest import TEST_REPO


class TestPATAuth:
    """Integration tests for Personal Access Token authentication."""

    @pytest.mark.integration
    def test_pat_auth_can_clone_with_token(self, require_git_and_network):
        """Test PAT authentication works for cloning."""
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            pytest.skip("GITHUB_TOKEN not set")

        # PATAuth just stores the token - verify it works with a clone
        auth = PATAuth(token)
        retrieved_token = auth.get_token()

        assert retrieved_token == token
        assert len(retrieved_token) > 0

        # Test that the token can be used in a clone URL
        # GITHUB_TOKEN env var is already set, so from_properties will pick it up
        config = GitHubConnectorConfig.from_properties(
            {
                "repository": TEST_REPO,
                "clone_strategy": "minimal",
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = Path(tmpdir) / "repo"
            clone_path.mkdir()

            git_ops = GitOperations()
            # This will use the token in the URL (even for public repos it works)
            git_ops.clone(config, clone_path)

            assert (clone_path / "README").exists()


class TestGitHubAppAuth:
    """Integration tests for GitHub App authentication."""

    @pytest.mark.integration
    def test_github_app_auth_generates_token(self):
        """Test GitHub App authentication generates installation token."""
        app_id = os.getenv("GITHUB_APP_ID")
        private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
        installation_id = os.getenv("GITHUB_APP_INSTALLATION_ID")

        if not all([app_id, private_key_path, installation_id]):
            pytest.skip(
                "GitHub App credentials not configured "
                "(GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY_PATH, GITHUB_APP_INSTALLATION_ID)"
            )

        key_path = Path(private_key_path)  # type: ignore[arg-type]
        if not key_path.exists():
            pytest.skip(f"Private key file not found: {private_key_path}")

        auth = GitHubAppAuth(
            app_id=int(app_id),  # type: ignore[arg-type]
            private_key_path=key_path,
            installation_id=int(installation_id),  # type: ignore[arg-type]
        )

        # This makes a real API call to GitHub
        token = auth.get_token()

        # Installation tokens are typically 40+ characters
        assert isinstance(token, str)
        assert len(token) > 20
        # GitHub installation tokens start with specific prefixes
        assert token.startswith("ghs_") or token.startswith("v1.")
