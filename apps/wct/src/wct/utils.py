"""Utility functions for WCT project operations.

This module provides common utility functions used across the WCT codebase,
including project root discovery and other shared functionality.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


class ProjectUtilsError(Exception):
    """Exception raised for project utility errors."""

    pass


def get_project_root() -> Path:
    """Get the project root directory using robust discovery methods.

    This function follows industry-standard approaches used by tools like pytest,
    black, and setuptools to find the project root:
    1. Package location via importlib (handles installed packages)
    2. Upward search for project markers (handles development)

    Returns:
        Path to the project root directory

    Raises:
        ProjectUtilsError: If project root cannot be determined

    """
    # Method 1: Use package location if installed (preferred)
    try:
        spec = importlib.util.find_spec("wct")
        if spec and spec.origin:
            package_path = Path(spec.origin).parent

            # For development installs, the package might be a symlink to src/wct
            if package_path.is_symlink():
                real_package = package_path.resolve()
                if real_package.name == "wct" and real_package.parent.name == "src":
                    potential_root = real_package.parent.parent
                    if (potential_root / "src" / "wct" / "config").is_dir():
                        return potential_root

            # For regular installs, search upward from package location
            for path in [package_path, *package_path.parents]:
                if (path / "src" / "wct" / "config").is_dir():
                    return path
    except (ImportError, AttributeError):
        # Package not found via importlib, continue to marker-based discovery
        pass

    # Method 2: Search upward from current file for project markers (development)
    current_path = Path(__file__).parent.resolve()

    for path in [current_path, *current_path.parents]:
        # Look for common project root markers
        markers = [
            path / "pyproject.toml",  # Modern Python project file
            path / "setup.py",  # Legacy setup file
            path / ".git",  # Git repository root
            path / "src" / "wct",  # Our package structure
        ]

        if any(marker.exists() for marker in markers):
            # Verify this looks like our project by checking for src/wct/config/
            if (path / "src" / "wct" / "config").is_dir():
                return path

    # If both methods fail, provide clear error message
    raise ProjectUtilsError(
        f"Could not determine project root. Searched:\n"
        f"1. Package location via importlib.util.find_spec('wct')\n"
        f"2. Upward from {current_path} for project markers\n"
        f"Expected to find a directory containing 'src/wct/config/' subdirectory."
    )
