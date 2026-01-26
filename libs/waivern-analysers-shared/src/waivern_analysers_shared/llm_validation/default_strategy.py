"""Default LLM validation strategy with count-based batching.

Flow
----

::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                   DefaultLLMValidationStrategy                          │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │  Findings ──► Batch by count (llm_batch_size) ──► For each batch:       │
    │                        │                               │                │
    │                        │                               └──► validate_batch()
    │                        │                                        (abstract)
    │                        │                                                │
    │                        └──► aggregate_batch_results() ──► TResult       │
    │                                     (abstract)                          │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

Batching is count-based: findings are split into batches of ``llm_batch_size``
regardless of content size. For token-aware batching with full source content,
use :class:`ExtendedContextLLMValidationStrategy` instead.

This is an abstract base class. For filtering (keep/remove findings), use
:class:`FilteringLLMValidationStrategy`. For enrichment (extract attributes),
create a strategy that extends this class with appropriate result types.
"""

import logging
from abc import abstractmethod
from typing import override

from waivern_core import Finding
from waivern_llm import BaseLLMService

from waivern_analysers_shared.types import LLMValidationConfig

from .strategy import LLMValidationStrategy

logger = logging.getLogger(__name__)


class DefaultLLMValidationStrategy[
    TFinding: Finding,
    TResult,
    TBatchResult,
](LLMValidationStrategy[TFinding, TResult]):
    """Abstract base for LLM validation strategies using count-based batching.

    Provides reusable infrastructure:
    - Count-based batching (by llm_batch_size)
    - Error handling per batch
    - Total failure handling

    Subclasses define:
    - Batch validation (prompt generation, LLM call, response processing)
    - Result aggregation (how to combine batch results)

    Type parameters:
        TFinding: The finding type, bound to the Finding protocol.
        TResult: The final strategy result type (returned by validate_findings).
        TBatchResult: The intermediate per-batch result type.
    """

    # -------------------------------------------------------------------------
    # Reusable: Batching and Error Handling
    # -------------------------------------------------------------------------

    @override
    def validate_findings(
        self,
        findings: list[TFinding],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> TResult:
        """Validate findings using LLM with count-based batching.

        Orchestrates the validation flow:
        1. Batch findings by count (llm_batch_size)
        2. For each batch: call validate_batch()
        3. Aggregate all batch results
        4. Handle errors gracefully

        Empty input is handled naturally: the batching loop executes zero
        times, and aggregate_batch_results([], []) returns the correct
        empty result.

        Args:
            findings: List of findings to validate.
            config: Configuration including batch_size, validation_mode, etc.
            llm_service: LLM service instance.

        Returns:
            Strategy-specific result type.

        """
        try:
            return self._process_findings_in_batches(findings, config, llm_service)

        except Exception as e:
            logger.error(f"LLM validation strategy failed: {e}")
            logger.warning("Returning failure result due to validation strategy error")
            return self._handle_total_failure(findings)

    def _process_findings_in_batches(
        self,
        findings: list[TFinding],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> TResult:
        """Process findings in batches for LLM validation.

        Args:
            findings: List of finding objects to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            Aggregated result from all batches.

        """
        batch_size = config.llm_batch_size

        # Accumulators for all batches
        batch_results: list[TBatchResult] = []
        failed_batches: list[list[TFinding]] = []

        for i in range(0, len(findings), batch_size):
            batch = findings[i : i + batch_size]
            try:
                batch_result = self._validate_batch(batch, config, llm_service)
                batch_results.append(batch_result)
            except Exception as e:
                logger.error(
                    f"LLM validation failed for batch {i // batch_size + 1}: {e}"
                )
                logger.warning(
                    "Marking batch findings as failed due to validation error"
                )
                failed_batches.append(batch)

        return self._aggregate_batch_results(batch_results, failed_batches)

    # -------------------------------------------------------------------------
    # Abstract: Batch Validation (internal hooks for subclasses)
    # -------------------------------------------------------------------------

    @abstractmethod
    def _validate_batch(
        self,
        findings_batch: list[TFinding],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> TBatchResult:
        """Validate a single batch of findings using LLM.

        Subclasses implement this to:
        1. Generate the validation prompt
        2. Call the LLM with the appropriate response model
        3. Process the response into a batch result

        Args:
            findings_batch: Batch of findings to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            Intermediate result for this batch.

        """
        ...

    @abstractmethod
    def _aggregate_batch_results(
        self,
        batch_results: list[TBatchResult],
        failed_batches: list[list[TFinding]],
    ) -> TResult:
        """Aggregate results from all batches into final result.

        Args:
            batch_results: Results from successful batches.
            failed_batches: Findings from batches that failed LLM validation.

        Returns:
            Final strategy result.

        """
        ...

    @abstractmethod
    def _handle_total_failure(self, findings: list[TFinding]) -> TResult:
        """Handle case where entire validation fails.

        Called when an unexpected exception occurs at the strategy level
        (outside of individual batch processing).

        Args:
            findings: All findings that were to be validated.

        Returns:
            Strategy-specific failure result.

        """
        ...
