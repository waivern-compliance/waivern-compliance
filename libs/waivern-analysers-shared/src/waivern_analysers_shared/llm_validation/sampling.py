"""Sampling strategies for LLM validation.

Strategies for selecting representative samples from grouped findings,
enabling cost-effective validation while maintaining confidence.
"""

import random
from dataclasses import dataclass
from typing import Protocol

from waivern_core.schemas.finding_types import BaseFindingModel


@dataclass
class SamplingResult[T: BaseFindingModel]:
    """Result of a sampling operation.

    Tracks which findings were selected for validation and which
    are kept by inference (not directly validated).
    """

    sampled: dict[str, list[T]]
    """Findings selected for LLM validation, keyed by group."""

    non_sampled: dict[str, list[T]]
    """Findings kept by inference (not directly validated), keyed by group."""


class SamplingStrategy[T: BaseFindingModel](Protocol):
    """Protocol for sampling findings from groups."""

    def sample(self, groups: dict[str, list[T]]) -> SamplingResult[T]:
        """Sample findings from each group.

        Args:
            groups: Dictionary mapping group keys to lists of findings.

        Returns:
            SamplingResult containing sampled and non-sampled findings.

        """
        ...


class RandomSamplingStrategy[T: BaseFindingModel]:
    """Randomly samples N findings per group.

    When a group has fewer findings than the sample size,
    all findings in that group are selected as samples.

    Example:
        strategy = RandomSamplingStrategy(sample_size=3)
        result = strategy.sample(groups)
        # result.sampled["Payment"] contains up to 3 findings
        # result.non_sampled["Payment"] contains the rest

    """

    def __init__(self, sample_size: int) -> None:
        """Initialise with the number of samples to take per group.

        Args:
            sample_size: Maximum number of findings to sample from each group.

        """
        self._sample_size = sample_size

    def sample(self, groups: dict[str, list[T]]) -> SamplingResult[T]:
        """Randomly sample findings from each group.

        Args:
            groups: Dictionary mapping group keys to lists of findings.

        Returns:
            SamplingResult with sampled and non-sampled findings per group.

        """
        sampled: dict[str, list[T]] = {}
        non_sampled: dict[str, list[T]] = {}

        for group_key, findings in groups.items():
            if len(findings) <= self._sample_size:
                sampled[group_key] = list(findings)
                non_sampled[group_key] = []
            else:
                samples = random.sample(findings, self._sample_size)
                sampled[group_key] = samples
                sample_ids = {f.id for f in samples}
                non_sampled[group_key] = [f for f in findings if f.id not in sample_ids]

        return SamplingResult(sampled=sampled, non_sampled=non_sampled)
