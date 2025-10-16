"""Tests for WCT utility functions.

These tests verify the behavior contracts of utility functions,
not implementation details or internal structures.
"""

from pathlib import Path

from wct.utils import get_project_root


class TestGetProjectRoot:
    """Test project root discovery functionality."""

    def test_returns_absolute_path(self):
        """Test that get_project_root returns an absolute path."""
        root = get_project_root()
        assert isinstance(root, Path)
        assert root.is_absolute()

    def test_returns_consistent_path(self):
        """Test that multiple calls return the same path."""
        root1 = get_project_root()
        root2 = get_project_root()
        assert root1 == root2

    def test_returned_path_exists(self):
        """Test that the returned path exists as a directory."""
        root = get_project_root()
        assert root.exists()
        assert root.is_dir()

    def test_enables_logging_configuration_discovery(self):
        """Test that the root enables WCT to find its logging configuration.

        This tests the contract: get_project_root() returns a path from which
        WCT can locate its configuration files and operate correctly.
        We don't care about the exact structure, only that it works.
        """
        from wct.logging import get_config_path

        # If this succeeds without raising LoggingError, the root is correct
        config_path = get_config_path()

        # Verify the configuration actually exists and is usable
        assert config_path.exists()
        assert config_path.is_file()
        assert config_path.suffix == ".yaml"

    def test_enables_organisation_configuration_discovery(self):
        """Test that the root enables WCT to find organisation configuration.

        Similar to logging config test - we verify the contract that
        organisation configuration can be discovered from the returned root.
        """
        root = get_project_root()

        # Organisation config should be at root/config/organisation.yaml
        org_config = root / "config" / "organisation.yaml"
        assert org_config.exists()
