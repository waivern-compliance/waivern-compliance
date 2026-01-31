"""Core types for LLM Service v2.

This module defines the foundational types used throughout the v2 LLM service:
- ItemGroup: Groups findings with optional shared content
- BatchingMode: How the service should batch items
- PromptBuilder: Protocol for building prompts from items
- SkipReason: Why a group was skipped during batching
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol

from waivern_core import Finding


@dataclass(frozen=True)
class ItemGroup[T: Finding]:
    """Groups findings with optional shared content.

    Processors create these to group findings by domain logic (e.g., by source file,
    by category). The LLM service then decides how to batch these groups.

    Content is attached at the group level to avoid memory duplication when
    multiple findings share the same source content.

    Type parameter T is bound to the Finding protocol.
    """

    items: Sequence[T]
    """The findings in this group."""

    content: str | None = None
    """Shared context for extended-context mode (e.g., source file content)."""

    group_id: str | None = None
    """Optional identifier for tracking and logging."""


class BatchingMode(Enum):
    """How the LLM service should batch items.

    Processors choose the batching mode based on whether additional context
    (like source file content) helps validation.
    """

    COUNT_BASED = auto()
    """Flatten all items from all groups, split by count.

    Use when items are independent and don't benefit from shared context.
    """

    EXTENDED_CONTEXT = auto()
    """Keep groups intact, bin-pack by tokens.

    Use when items benefit from shared context (e.g., findings from the same
    source file validated together with the file content).
    """


class PromptBuilder[T: Finding](Protocol):
    """Protocol for building prompts from items.

    Processors implement this to create domain-specific prompts.
    The LLM service calls this for each batch it creates.
    """

    def build_prompt(self, items: Sequence[T], content: str | None = None) -> str:
        """Build a complete prompt for the given items.

        Args:
            items: The findings to include in the prompt.
            content: Optional shared context (e.g., source file content).

        Returns:
            Complete prompt string including role/context instructions.

        """
        ...


class SkipReason(Enum):
    """Why a group was skipped during batching.

    Groups may be skipped for various reasons. The LLM service tracks these
    so callers can implement fallback strategies or report on validation gaps.
    """

    OVERSIZED = "oversized_source"
    """Group exceeds the model's context window."""

    MISSING_CONTENT = "missing_content"
    """Extended context mode but group has no content."""

    NO_SOURCE = "no_source"
    """Finding has no source metadata."""

    BATCH_ERROR = "batch_error"
    """LLM call failed for this batch."""
