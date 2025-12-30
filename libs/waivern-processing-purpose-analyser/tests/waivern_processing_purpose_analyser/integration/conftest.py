"""Shared fixtures for ProcessingPurposeAnalyser integration tests.

These tests require real API keys and make actual API calls.
Run with: uv run pytest -m integration
"""

import os

import pytest


@pytest.fixture
def require_anthropic_api_key() -> str:
    """Skip test if ANTHROPIC_API_KEY is not set, otherwise return the key."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return api_key
