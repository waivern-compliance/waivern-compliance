"""Core types for the LLM service.

This module defines the foundational types used throughout the LLM service:
- ItemGroup: Groups findings with optional shared content
- BatchingMode: How the service should batch items
- PromptBuilder: Protocol for building prompts from items
- SkipReason: Why a finding/group was skipped during processing
- SkippedFinding: A finding that was skipped with its reason
- LLMCompletionResult: Return type for LLMService.complete()
- LLMRequest: Dispatch request declaring LLM needs as data
- LLMDispatchResult: Dispatch result carrying LLM responses and skipped findings
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Protocol, override, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field
from waivern_core import ExecutionContext, Finding, JsonValue
from waivern_core.dispatch import DispatchRequest, DispatchResult


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
    """Shared context for the group (e.g., source file content). Used by EXTENDED_CONTEXT and INDEPENDENT modes."""

    group_id: str | None = None
    """Optional identifier for tracking and logging."""


class BatchingMode(Enum):
    """How the LLM service should batch items.

    Processors choose the batching mode based on the semantic relationship
    between input items and output decisions.

    DESIGN NOTE — Three Semantic Contracts
    ---------------------------------------

    The three modes represent distinct caller intents, not just batching
    strategies. The key distinction is the input→output contract:

    - COUNT_BASED / EXTENDED_CONTEXT → N items in, N decisions out
      (one decision per item)
    - INDEPENDENT → N items in, 1 decision out
      (items collectively inform a single verdict)

    COUNT_BASED is the degenerate case of EXTENDED_CONTEXT with no shared
    context. EXTENDED_CONTEXT differs only in that items share a context
    (e.g., source file content) that the LLM needs alongside each item.

    INDEPENDENT produces an atomic, indivisible output — splitting its items
    across batches would break the semantic because the LLM needs all evidence
    together to form one verdict.

    EXTENDED_CONTEXT produces per-item decisions — items CAN be split across
    batches (each carrying the same context) because each decision is
    independent. This splitting is a future optimisation; currently each group
    becomes its own batch.

    Decision matrix:
    - Items need no shared context → COUNT_BASED
    - Items share context, per-item decisions → EXTENDED_CONTEXT
    - Items form one unit, single decision → INDEPENDENT
    """

    COUNT_BASED = auto()
    """Flatten all items from all groups, split by count.

    Use when items are independent and don't benefit from shared context.
    Example: validating findings based on their own evidence only.
    """

    EXTENDED_CONTEXT = auto()
    """One group per batch. Items share context, produce per-item decisions.

    Use when items benefit from shared context (e.g., findings from the same
    source file validated together with the file content). Each group produces
    a list of per-item decisions.

    Currently each group becomes its own batch. A future optimisation hook
    supports oversized group splitting and same-context bin-packing.
    """

    INDEPENDENT = auto()
    """One group per batch. Items form one unit, produce a single decision.

    Use when all items in a group collectively inform a single verdict
    (e.g., assessing a control using all evidence as a whole). Splitting
    items across batches would break the semantic.

    Preserves input order for 1:1 group-to-response mapping.
    """


@runtime_checkable
class PromptBuilder[T: Finding](Protocol):
    """Protocol for building prompts from groups of findings.

    Processors implement this to create domain-specific prompts.
    The LLM service calls this for each batch it creates, passing the
    batch's groups directly. Each group carries its own items and
    optional content.
    """

    def build_prompt(self, groups: Sequence[ItemGroup[T]]) -> str:
        """Build a complete prompt for the given groups.

        Args:
            groups: The groups to include in the prompt. Each group contains
                items and optional content (e.g., source file content).

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


class LLMRequest[T: Finding](DispatchRequest):
    """Dispatch request declaring a processor's LLM needs as data.

    Captures everything a processor knows about its LLM requirements:
    the grouped findings, how to build prompts, the expected response shape,
    and the batching strategy. The dispatcher interprets this to plan batches,
    build prompts, and route to the LLM provider.

    Serialisation:
        ``prompt_builder`` and ``response_model`` are excluded from
        serialisation — they are live Python objects only needed on first
        run. During dispatch, the dispatcher computes cache keys and
        populates ``built_cache_keys``. On resume, the stored keys enable
        direct cache lookup without the builder or response model.

    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    groups: Sequence[ItemGroup[T]]
    """Processor-defined groupings of findings."""

    prompt_builder: PromptBuilder[T] | None = Field(default=None, exclude=True)
    """Domain-specific prompt builder. Excluded from serialisation.

    Required on first run. ``None`` on resume (prompts already cached).
    """

    response_model: type[BaseModel] | None = Field(default=None, exclude=True)
    """Expected response shape for the LLM. Excluded from serialisation.

    Used by the dispatcher on first run to call
    ``provider.invoke_structured()`` (sync mode) or generate the JSON
    schema for ``BatchRequest`` (batch mode). ``None`` on resume.
    """

    batching_mode: BatchingMode
    """How the dispatcher should batch items."""

    run_id: str
    """Cache scoping key."""

    built_cache_keys: list[str] | None = None
    """Cache keys computed during dispatch; ``None`` until first run completes."""


class LLMDispatchResult(DispatchResult):
    """Dispatch result carrying raw LLM responses and skipped findings.

    Returned by the ``LLMDispatcher`` after processing an ``LLMRequest``.
    Responses are raw dicts — the processor deserialises them in
    ``finalise()`` using its own response model type.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_name: str
    """LLM model that produced these responses (e.g. 'claude-sonnet-4-5-20250929')."""

    responses: list[dict[str, JsonValue]]
    """Raw response dicts, one per batch processed."""

    skipped: list[SkippedFinding[Finding]]
    """Findings that could not be processed, with reasons."""

    @override
    def enrich_execution_context(self, context: ExecutionContext) -> ExecutionContext:
        """Set ``model_name`` from the LLM response."""
        return replace(context, model_name=self.model_name)
