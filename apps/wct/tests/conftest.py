"""Global test configuration for WCT tests."""

from importlib.metadata import entry_points

import pytest


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
