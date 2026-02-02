"""Core types for LLM Service v2.

This module defines the foundational types used throughout the v2 LLM service:
- ItemGroup: Groups findings with optional shared content
- BatchingMode: How the service should batch items
- PromptBuilder: Protocol for building prompts from items
- SkipReason: Why a finding/group was skipped during processing
- SkippedFinding: A finding that was skipped with its reason
- LLMCompletionResult: Return type for LLMService.complete()
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol

from pydantic import BaseModel
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
    """Why a finding or group was skipped during LLM processing.

    Findings may be skipped for various reasons. The LLM service returns these
    so callers can implement fallback strategies or report on validation gaps.

    IMPORTANT - MISSING_SOURCE vs MISSING_CONTENT distinction:
    These are NOT the same thing. They represent different stages in content retrieval:

    1. Processor groups findings by source
    2. For each finding, processor looks up source_id to get content
       - No source_id? → MISSING_SOURCE (data issue at finding level)
       - Has source_id but ContentProvider.get_content() fails? → MISSING_CONTENT

    Both result in skipping during EXTENDED_CONTEXT mode, but indicate different
    root causes requiring different remediation.
    """

    OVERSIZED = "oversized_source"
    """Group exceeds the model's context window even when processed alone."""

    MISSING_SOURCE = "missing_source"
    """Finding lacks source_id for content lookup via ContentProvider.

    This is a data issue at the finding level - the finding doesn't have
    a source_id attribute, so we cannot look up its content.

    NOT the same as MISSING_CONTENT - see class docstring for distinction.
    """

    MISSING_CONTENT = "missing_content"
    """Finding has source_id but ContentProvider failed to retrieve content.

    The finding has a source_id, but when ContentProvider.get_content(source_id)
    was called, it returned None or failed. This is a content retrieval issue.

    NOT the same as MISSING_SOURCE - see class docstring for distinction.
    """

    BATCH_ERROR = "batch_error"
    """LLM call failed for this batch after retries."""


@dataclass(frozen=True)
class SkippedFinding[T: Finding]:
    """A finding that was skipped during LLM processing.

    The batch/group structure is an internal LLM service concern and is not
    exposed to callers. Processors receive a flat list of skipped findings
    to handle according to their domain logic.
    """

    finding: T
    """The finding that was skipped."""

    reason: SkipReason
    """Why this finding was skipped."""


@dataclass(frozen=True)
class LLMCompletionResult[T: Finding, R: BaseModel]:
    """Result of LLM completion - responses plus skipped findings.

    The responses list contains one response per batch processed. Processors
    interpret responses according to their domain logic:
    - Filtering processors: R contains TRUE_POSITIVE/FALSE_POSITIVE verdicts
    - Enriching processors: R contains classifications to add

    The skipped list contains individual findings that could not be processed.
    Processors decide how to handle these (e.g., keep as-is, mark as
    unvalidated, fall back to simpler validation).

    DESIGN NOTE - Why no batch/group info exposed:
    The batch and group structure is an INTERNAL LLM service concern for
    optimising API calls. Callers don't need to know how findings were batched -
    they only need to know:
    1. What responses came back (one per batch, but batch count is opaque)
    2. Which individual findings were skipped and why

    The old v1 design didn't expose batch info either. Don't add it.
    """

    responses: list[R]
    """One response per batch processed.

    Note: Callers should NOT assume a 1:1 mapping between input items and
    responses. Batching is an internal optimisation. The processor must
    correlate responses with findings based on response content.
    """

    skipped: list[SkippedFinding[T]]
    """Individual findings that could not be processed, with reasons.

    This is a FLAT list of findings, not grouped by batch or original group.
    The group structure is internal to the LLM service.
    """
