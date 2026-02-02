"""LLM Response Cache entry and key generation.

This module provides the CacheEntry model for LLM response caching,
including deterministic cache key generation.
"""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel
from waivern_core import JsonValue


class CacheEntry(BaseModel):
    """LLM response cache entry.

    Tracks the status and response of an LLM request for caching
    and async batch resumption.
    """

    status: Literal["pending", "completed", "failed"]
    response: dict[str, JsonValue] | None
    batch_id: str | None  # For async batch mode
    model_name: str
    response_model_name: str

    @classmethod
    def compute_key(cls, prompt: str, model: str, response_model: str) -> str:
        """Compute cache key from prompt, model, and response model.

        Uses SHA256 hash of concatenated values to ensure:
        - Same inputs always produce same key (deterministic)
        - Different models/response_models cache separately

        Args:
            prompt: The LLM prompt text.
            model: Model name (e.g., 'claude-sonnet-4-5').
            response_model: Response model name (e.g., 'ValidationResult').

        Returns:
            64-character hex string (SHA256 hash).

        """
        combined = f"{prompt}|{model}|{response_model}"
        return hashlib.sha256(combined.encode()).hexdigest()
