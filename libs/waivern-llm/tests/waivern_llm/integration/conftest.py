"""Shared fixtures for LLM service integration tests.

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


@pytest.fixture
def require_openai_api_key() -> str:
    """Skip test if OPENAI_API_KEY is not set, otherwise return the key."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")
    return api_key


@pytest.fixture
def require_google_api_key() -> str:
    """Skip test if GOOGLE_API_KEY is not set, otherwise return the key."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not set")
    return api_key


def _check_langchain_openai_available() -> bool:
    """Check if langchain-openai is installed."""
    try:
        from langchain_openai import ChatOpenAI  # pyright: ignore[reportUnusedImport]

        del ChatOpenAI  # Explicitly mark as used for availability check
        return True
    except ImportError:
        return False


def _check_langchain_google_available() -> bool:
    """Check if langchain-google-genai is installed."""
    try:
        from langchain_google_genai import (  # pyright: ignore[reportUnusedImport]
            ChatGoogleGenerativeAI,
        )

        del ChatGoogleGenerativeAI  # Explicitly mark as used for availability check
        return True
    except ImportError:
        return False


@pytest.fixture
def require_openai(require_openai_api_key: str) -> str:
    """Skip test if OpenAI API key or langchain-openai is unavailable."""
    if not _check_langchain_openai_available():
        pytest.skip("langchain-openai not installed - run: uv sync --group llm-openai")
    return require_openai_api_key


@pytest.fixture
def require_google(require_google_api_key: str) -> str:
    """Skip test if Google API key or langchain-google-genai is unavailable."""
    if not _check_langchain_google_available():
        pytest.skip(
            "langchain-google-genai not installed - run: uv sync --group llm-google"
        )
    return require_google_api_key
