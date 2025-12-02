"""LLM validation prompts for processing purpose analysis.

This module contains prompt templates used for LLM-based validation
of processing purpose findings to filter false positives.
"""

from .processing_purpose_validation import get_processing_purpose_validation_prompt

__all__ = [
    "get_processing_purpose_validation_prompt",
]
