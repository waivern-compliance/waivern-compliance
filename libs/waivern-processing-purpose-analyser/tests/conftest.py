"""Test configuration for waivern-processing-purpose-analyser."""

import pytest
from waivern_source_code_analyser import (
    register_schemas as register_source_code_schemas,
)

from waivern_processing_purpose_analyser import register_schemas


@pytest.fixture(autouse=True)
def _register_schemas() -> None:  # pyright: ignore[reportUnusedFunction]
    """Register schemas for all tests.

    This fixture automatically runs before every test to ensure schemas are registered.
    Registers both processing-purpose-analyser and source_code schemas.
    """
    register_schemas()
    register_source_code_schemas()
