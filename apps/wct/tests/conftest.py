"""Global test configuration for WCT tests."""

from importlib.metadata import entry_points
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load environment variables from WCT application .env file for testing
# This ensures VS Code and other test runners have access to the same environment
# Note: We use the WCT app's .env since that's where API keys and credentials live
env_file = Path(__file__).parent.parent / "apps" / "wct" / ".env"
if env_file.exists():
    load_dotenv(env_file)


@pytest.fixture(autouse=True)
def register_all_schemas() -> None:
    """Automatically register all schemas for WCT tests.

    Discovers and registers schemas from all installed packages via entry points.
    This ensures that schemas from standalone packages are available to tests.
    """
    schema_eps = entry_points(group="waivern.schemas")

    for ep in schema_eps:
        try:
            register_func = ep.load()
            register_func()
        except Exception:  # noqa: S110
            # Ignore failures - some schemas might not be available
            pass
