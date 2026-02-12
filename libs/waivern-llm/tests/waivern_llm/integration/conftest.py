"""Shared fixtures and models for LLM service integration tests.

These tests require real API keys and make actual API calls.
Run with: uv run pytest -m integration
"""

import os
from typing import Literal

import pytest
from pydantic import BaseModel, Field

# =============================================================================
# Shared batch integration test models
# =============================================================================


class ValidationResult(BaseModel):
    """Single validation result — mirrors real analyser response models."""

    finding_id: str = Field(description="ID of the finding being validated")
    validation_result: Literal["TRUE_POSITIVE", "FALSE_POSITIVE"] = Field(
        description="Whether the finding is a true or false positive"
    )
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Explanation for the validation decision")


class ValidationResponse(BaseModel):
    """Batch validation response — mirrors LLMValidationResponseModel."""

    results: list[ValidationResult] = Field(
        description="List of validation results for each finding"
    )


VALIDATION_PROMPT = """\
You are a compliance data validator. Analyse the following finding and determine \
whether it is a TRUE_POSITIVE or FALSE_POSITIVE.

Finding ID: finding-001
Content: "The system stores user email addresses for account recovery purposes."
Category: personal_data
Matched pattern: email

Respond with a ValidationResponse containing exactly one result for finding-001.\
"""

POLL_INTERVAL_SECONDS = 10
POLL_TIMEOUT_SECONDS = 300  # 5 minutes


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
