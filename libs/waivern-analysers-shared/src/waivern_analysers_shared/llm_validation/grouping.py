"""Grouping strategies for LLM validation.

Strategies for grouping findings before validation, enabling sampling
and group-level validation decisions.
"""

from collections import defaultdict
from typing import Protocol

from waivern_core.schemas.finding_types import BaseFindingModel

from waivern_analysers_shared.llm_validation.protocols import (
    ConcernProvider,
    SourceProvider,
)


class GroupingStrategy[T: BaseFindingModel](Protocol):
    """Protocol for grouping findings."""

    def group(self, findings: list[T]) -> dict[str, list[T]]:
        """Group findings by some attribute.

        Args:
            findings: List of findings to group.

        Returns:
            Dictionary mapping group keys to lists of findings.

        """
        ...


class ConcernGroupingStrategy[T: BaseFindingModel]:
    """Groups findings by compliance concern using a ConcernProvider.

    Example:
        provider = ProcessingPurposeConcernProvider()
        strategy = ConcernGroupingStrategy(provider)
        groups = strategy.group(findings)
        # {"Payment Processing": [...], "Analytics": [...]}

    """

    def __init__(self, concern_provider: ConcernProvider[T]) -> None:
        """Initialise with a concern provider.

        Args:
            concern_provider: Provider that extracts concern values from findings.

        """
        self._provider = concern_provider

    def group(self, findings: list[T]) -> dict[str, list[T]]:
        """Group findings by concern value.

        Args:
            findings: List of findings to group.

        Returns:
            Dictionary mapping concern values to lists of findings.

        """
        groups: dict[str, list[T]] = defaultdict(list)
        for finding in findings:
            concern = self._provider.get_concern(finding)
            groups[concern].append(finding)
        return dict(groups)


class SourceGroupingStrategy[T: BaseFindingModel]:
    """Groups findings by source file using a SourceProvider.

    Example:
        provider = ProcessingPurposeSourceProvider()
        strategy = SourceGroupingStrategy(provider)
        groups = strategy.group(findings)
        # {"src/app.py": [...], "src/utils.py": [...]}

    """

    def __init__(self, source_provider: SourceProvider[T]) -> None:
        """Initialise with a source provider.

        Args:
            source_provider: Provider that extracts source IDs from findings.

        """
        self._provider = source_provider

    def group(self, findings: list[T]) -> dict[str, list[T]]:
        """Group findings by source ID.

        Args:
            findings: List of findings to group.

        Returns:
            Dictionary mapping source IDs to lists of findings.

        """
        groups: dict[str, list[T]] = defaultdict(list)
        for finding in findings:
            source_id = self._provider.get_source_id(finding)
            groups[source_id].append(finding)
        return dict(groups)
