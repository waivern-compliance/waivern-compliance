"""Git operations for cloning repositories and collecting files."""

import subprocess
from pathlib import Path

import pathspec

from waivern_github.config import CloneStrategy, GitHubConnectorConfig

# Strategy -> git clone flags mapping (single source of truth)
CLONE_STRATEGY_FLAGS: dict[CloneStrategy, list[str]] = {
    "minimal": ["--depth", "1", "--filter=blob:none", "--sparse"],
    "shallow": ["--depth", "1"],
    "partial": ["--filter=blob:none", "--sparse"],
    "full": [],
}


class GitOperations:
    """Handles git clone, sparse checkout, and file collection operations."""

    GITHUB_URL = "https://github.com"

    def clone(
        self,
        config: GitHubConnectorConfig,
        target_dir: Path,
    ) -> None:
        """Clone a repository with the specified strategy.

        Args:
            config: GitHub connector configuration containing repository,
                ref, clone_strategy, clone_timeout, and token.
            target_dir: Directory to clone into.

        Raises:
            subprocess.CalledProcessError: If clone or checkout fails.
            subprocess.TimeoutExpired: If operation times out.

        """
        # Build clone URL
        clone_url = self._build_clone_url(config.repository, config.token)

        # Build clone command based on strategy and ref
        clone_cmd = self._build_clone_command(
            clone_url, target_dir, config.clone_strategy, config.ref
        )

        # Execute clone
        subprocess.run(  # noqa: S603 - git command with controlled inputs
            clone_cmd, check=True, timeout=config.clone_timeout, capture_output=True
        )

        # Checkout specified ref (only needed if ref wasn't specified in clone)
        # With --branch, git already checks out the specified ref
        if config.ref == "HEAD":
            # HEAD is the default, no checkout needed
            return

        # For non-HEAD refs that were cloned with --branch, verify we're on the right ref
        # This handles edge cases where the branch name differs from what was requested
        checkout_cmd = ["git", "-C", str(target_dir), "checkout", config.ref]
        subprocess.run(  # noqa: S603 - git command with controlled inputs
            checkout_cmd, check=True, timeout=config.clone_timeout, capture_output=True
        )

    def _build_clone_url(self, repository: str, token: str | None) -> str:
        """Build the clone URL with optional authentication."""
        if token:
            return f"https://x-access-token:{token}@github.com/{repository}.git"
        return f"{self.GITHUB_URL}/{repository}.git"

    def _build_clone_command(
        self, clone_url: str, target_dir: Path, strategy: CloneStrategy, ref: str
    ) -> list[str]:
        """Build git clone command based on strategy and ref.

        Args:
            clone_url: The repository URL to clone.
            target_dir: Directory to clone into.
            strategy: Clone strategy determining depth and filters.
            ref: Git ref (branch/tag) to clone. If not "HEAD", adds --branch flag.

        Returns:
            List of command arguments for git clone.

        """
        cmd = ["git", "clone"]
        cmd.extend(CLONE_STRATEGY_FLAGS[strategy])

        # For shallow clones with non-HEAD refs, we must specify --branch
        # otherwise git only fetches the default branch and checkout fails
        if ref != "HEAD":
            cmd.extend(["--branch", ref])

        cmd.extend([clone_url, str(target_dir)])
        return cmd

    def sparse_checkout(
        self, repo_dir: Path, patterns: list[str], timeout: int = 300
    ) -> None:
        """Configure sparse checkout with specified patterns.

        Args:
            repo_dir: Path to the cloned repository.
            patterns: List of patterns for sparse checkout.
            timeout: Timeout in seconds.

        Raises:
            RuntimeError: If sparse-checkout fails.
            subprocess.TimeoutExpired: If operation times out.

        """
        cmd = ["git", "-C", str(repo_dir), "sparse-checkout", "set", *patterns]
        subprocess.run(  # noqa: S603 - git command with controlled inputs
            cmd, check=True, timeout=timeout, capture_output=True
        )

    def collect_files(
        self,
        repo_dir: Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        max_files: int = 10000,
    ) -> list[Path]:
        """Collect files from repository matching patterns.

        Args:
            repo_dir: Path to the cloned repository.
            include_patterns: Patterns to include (or None for all files).
            exclude_patterns: Patterns to exclude (or None for no exclusions).
            max_files: Maximum number of files to collect.

        Returns:
            List of file paths relative to repo_dir.

        """
        # Gather all files recursively (excluding directories and .git)
        all_files = [
            f
            for f in repo_dir.rglob("*")
            if f.is_file() and ".git" not in f.relative_to(repo_dir).parts
        ]

        # Apply include patterns if specified
        if include_patterns:
            spec = pathspec.PathSpec.from_lines("gitwildmatch", include_patterns)
            all_files = [
                f for f in all_files if spec.match_file(f.relative_to(repo_dir))
            ]

        # Apply exclude patterns if specified
        if exclude_patterns:
            spec = pathspec.PathSpec.from_lines("gitwildmatch", exclude_patterns)
            all_files = [
                f for f in all_files if not spec.match_file(f.relative_to(repo_dir))
            ]

        # Limit to max_files
        return all_files[:max_files]
