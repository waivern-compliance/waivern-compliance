"""Abstract base class for batched-files LLM validation strategy.

Provides token-aware batching of findings by file for efficient LLM validation.
Concrete implementations define how to extract file paths from findings and
how to generate validation prompts.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from waivern_llm import BaseLLMService

from .decision_engine import ValidationDecisionEngine
from .file_content import FileContentProvider, FileInfo
from .json_utils import extract_json_from_llm_response
from .models import LLMValidationResultModel

logger = logging.getLogger(__name__)


@dataclass
class FileBatch[T]:
    """A batch of files to validate together.

    Type parameter T is the finding type.
    """

    files: list[str]
    """List of file paths in this batch."""

    estimated_tokens: int
    """Estimated total tokens for files in this batch."""


@dataclass
class BatchingResult[T]:
    """Result of creating token-aware batches.

    Type parameter T is the finding type.
    """

    batches: list[FileBatch[T]]
    """Batches that fit within token limits."""

    oversized_files: list[str] = field(default_factory=list)
    """Files that exceed the token limit on their own."""

    missing_files: list[str] = field(default_factory=list)
    """Files not found in the file provider."""


@dataclass
class _BatchBuilder[T]:
    """Accumulates files into batches respecting token limits.

    Encapsulates the state management for greedy bin-packing algorithm.
    Type parameter T is the finding type (for consistency with FileBatch).
    """

    max_tokens: int
    """Maximum tokens allowed per batch."""

    _batches: list[FileBatch[T]] = field(default_factory=list)
    _current_files: list[str] = field(default_factory=list)
    _current_tokens: int = 0

    def add_file(self, file_path: str, file_tokens: int) -> None:
        """Add a file to the current batch, starting a new batch if needed."""
        if self._current_tokens + file_tokens <= self.max_tokens:
            self._current_files.append(file_path)
            self._current_tokens += file_tokens
        else:
            self._finalise_current_batch()
            self._current_files = [file_path]
            self._current_tokens = file_tokens

    def _finalise_current_batch(self) -> None:
        """Finalise the current batch if non-empty."""
        if self._current_files:
            self._batches.append(
                FileBatch(
                    files=list(self._current_files),
                    estimated_tokens=self._current_tokens,
                )
            )
            self._current_files.clear()
            self._current_tokens = 0

    def build(self) -> list[FileBatch[T]]:
        """Finalise and return all batches."""
        self._finalise_current_batch()
        return self._batches


class BatchedFilesStrategyBase[T](ABC):
    """Abstract base class for batched-files validation strategies.

    Provides token-aware batching infrastructure. Concrete implementations
    define analyser-specific behaviour (file path extraction, prompt generation).

    Type parameter T is the finding type (e.g., ProcessingPurposeFindingModel).
    """

    @abstractmethod
    def extract_file_path_from_finding(self, finding: T) -> str | None:
        """Extract the source file path from a finding.

        Args:
            finding: The finding to extract file path from.

        Returns:
            File path string, or None if path cannot be extracted.

        """
        ...

    @abstractmethod
    def get_batch_validation_prompt(
        self,
        batch: FileBatch[T],
        findings_by_file: dict[str, list[T]],
        file_contents: dict[str, str],
    ) -> str:
        """Generate the LLM validation prompt for a batch.

        Args:
            batch: The batch of files to validate.
            findings_by_file: Mapping of file paths to their findings.
            file_contents: Mapping of file paths to their content.

        Returns:
            Formatted prompt string for LLM validation.

        """
        ...

    def _group_findings_by_file(self, findings: list[T]) -> dict[str, list[T]]:
        """Group findings by their source file.

        Args:
            findings: List of findings to group.

        Returns:
            Dictionary mapping file paths to their findings.
            Findings with no extractable file path are excluded.

        """
        grouped: dict[str, list[T]] = {}

        for finding in findings:
            file_path = self.extract_file_path_from_finding(finding)
            if file_path:
                if file_path not in grouped:
                    grouped[file_path] = []
                grouped[file_path].append(finding)

        return grouped

    def _create_token_aware_batches(
        self,
        findings_by_file: dict[str, list[T]],
        file_provider: FileContentProvider,
        max_tokens_per_batch: int,
    ) -> BatchingResult[T]:
        """Create batches of files that fit within token limits.

        Uses greedy bin-packing: adds files to current batch until limit
        is reached, then starts a new batch.

        Args:
            findings_by_file: Mapping of file paths to their findings.
            file_provider: Provider for file content and token estimates.
            max_tokens_per_batch: Maximum tokens allowed per batch.

        Returns:
            BatchingResult with batches and any oversized files.

        """
        all_files = file_provider.get_all_files()
        sorted_paths = self._sort_files_by_token_estimate(
            file_paths=list(findings_by_file.keys()),
            all_files=all_files,
        )

        builder: _BatchBuilder[T] = _BatchBuilder(max_tokens=max_tokens_per_batch)
        oversized_files: list[str] = []
        missing_files: list[str] = []

        for file_path in sorted_paths:
            if file_path not in all_files:
                missing_files.append(file_path)
                continue

            file_tokens = all_files[file_path].estimated_tokens

            if file_tokens > max_tokens_per_batch:
                oversized_files.append(file_path)
            else:
                builder.add_file(file_path, file_tokens)

        result = BatchingResult(
            batches=builder.build(),
            oversized_files=oversized_files,
            missing_files=missing_files,
        )

        logger.info(
            f"Created {len(result.batches)} batches, "
            f"{len(result.oversized_files)} oversized files, "
            f"{len(result.missing_files)} missing files"
        )

        return result

    def _sort_files_by_token_estimate(
        self,
        file_paths: list[str],
        all_files: dict[str, FileInfo],
    ) -> list[str]:
        """Sort file paths by token estimate (largest first) for better packing."""
        return sorted(
            file_paths,
            key=lambda p: all_files[p].estimated_tokens if p in all_files else 0,
            reverse=True,
        )

    def validate_findings_with_file_content(
        self,
        findings: list[T],
        file_provider: FileContentProvider,
        max_tokens_per_batch: int,
        llm_service: BaseLLMService,
    ) -> tuple[list[T], bool]:
        """Validate findings using file-based batching with full file content.

        Orchestrates the complete validation flow:
        1. Group findings by source file
        2. Create token-aware batches
        3. For each batch, generate prompt with full file content and call LLM
        4. Parse responses and filter findings

        Args:
            findings: List of findings to validate.
            file_provider: Provider for file content.
            max_tokens_per_batch: Maximum tokens per batch.
            llm_service: LLM service for validation calls.

        Returns:
            Tuple of (validated_findings, all_batches_succeeded).

        """
        if not findings:
            logger.debug("No findings to validate")
            return [], True

        try:
            # Group findings by file
            findings_by_file = self._group_findings_by_file(findings)

            if not findings_by_file:
                logger.warning("No findings could be grouped by file")
                return findings, False

            # Create token-aware batches
            batching_result = self._create_token_aware_batches(
                findings_by_file=findings_by_file,
                file_provider=file_provider,
                max_tokens_per_batch=max_tokens_per_batch,
            )

            # Validate each batch
            validated_findings: list[T] = []
            all_batches_succeeded = True

            for batch_idx, batch in enumerate(batching_result.batches):
                try:
                    batch_findings = self._validate_batch(
                        batch=batch,
                        findings_by_file=findings_by_file,
                        file_provider=file_provider,
                        llm_service=llm_service,
                    )
                    validated_findings.extend(batch_findings)
                except Exception as e:
                    logger.error(f"Batch {batch_idx + 1} validation failed: {e}")

                    # Include unvalidated findings from failed batch
                    for file_path in batch.files:
                        validated_findings.extend(findings_by_file[file_path])
                    all_batches_succeeded = False

            # Include findings from oversized files (unvalidated)
            for file_path in batching_result.oversized_files:
                logger.warning(
                    f"Including {len(findings_by_file[file_path])} unvalidated "
                    f"findings from oversized file: {file_path}"
                )
                validated_findings.extend(findings_by_file[file_path])

            # Include findings from missing files (unvalidated)
            for file_path in batching_result.missing_files:
                logger.warning(
                    f"Including {len(findings_by_file[file_path])} unvalidated "
                    f"findings from missing file: {file_path}"
                )
                validated_findings.extend(findings_by_file[file_path])

            logger.debug(
                f"Validation complete: {len(findings)} → {len(validated_findings)}"
            )

            return validated_findings, all_batches_succeeded

        except Exception as e:
            logger.error(f"File-based validation failed: {e}")
            return findings, False

    def _validate_batch(
        self,
        batch: FileBatch[T],
        findings_by_file: dict[str, list[T]],
        file_provider: FileContentProvider,
        llm_service: BaseLLMService,
    ) -> list[T]:
        """Validate a single batch of files.

        Args:
            batch: The batch to validate.
            findings_by_file: Mapping of file paths to findings.
            file_provider: Provider for loading file content.
            llm_service: LLM service for validation.

        Returns:
            List of validated findings from this batch.

        """
        # Build flat list of findings in batch order for index mapping
        batch_findings: list[T] = []
        for file_path in batch.files:
            batch_findings.extend(findings_by_file[file_path])

        # Load content only for files in this batch
        file_contents: dict[str, str] = {}
        for file_path in batch.files:
            content = file_provider.get_file_content(file_path)
            if content is not None:
                file_contents[file_path] = content

        # Generate prompt
        prompt = self.get_batch_validation_prompt(
            batch=batch,
            findings_by_file=findings_by_file,
            file_contents=file_contents,
        )

        # Call LLM
        logger.debug(f"Validating batch with {len(batch_findings)} findings")
        response = llm_service.analyse_data("", prompt)

        # Parse response
        clean_json = extract_json_from_llm_response(response)
        validation_results = json.loads(clean_json)

        # Filter findings based on validation results
        return self._filter_findings_by_results(batch_findings, validation_results)

    def _filter_findings_by_results(
        self,
        findings: list[T],
        validation_results: list[dict[str, object]],
    ) -> list[T]:
        """Filter findings based on LLM validation results.

        Uses fail-safe approach: findings not mentioned by LLM are included
        (with warning), consistent with existing validation error handling.

        Args:
            findings: Flat list of findings in batch order.
            validation_results: Validation results from LLM.

        Returns:
            List of findings that should be kept.

        """
        validated: list[T] = []
        processed_indices: set[int] = set()

        for result_data in validation_results:
            # Extract finding_index from raw data (not part of model)
            raw_index = result_data.get("finding_index")
            if raw_index is None:
                logger.warning("Validation result missing finding_index")
                continue

            try:
                finding_index = int(raw_index)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                logger.warning(f"Invalid finding_index: {raw_index}")
                continue

            if finding_index < 0 or finding_index >= len(findings):
                logger.warning(
                    f"Finding index {finding_index} out of range [0, {len(findings)})"
                )
                continue

            processed_indices.add(finding_index)
            finding = findings[finding_index]

            try:
                result = LLMValidationResultModel.model_validate(result_data)
            except Exception as e:
                logger.warning(f"Failed to parse validation result: {e}")
                # Use defaults for malformed results (consistent with existing strategy)
                result = LLMValidationResultModel()

            # Log validation decision
            ValidationDecisionEngine.log_validation_decision(
                result, finding, self._get_finding_id
            )

            if ValidationDecisionEngine.should_keep_finding(
                result, finding, self._get_finding_id
            ):
                validated.append(finding)

        # Fail-safe: include findings not mentioned by LLM
        unprocessed_indices = set(range(len(findings))) - processed_indices
        if unprocessed_indices:
            logger.warning(
                f"LLM omitted {len(unprocessed_indices)} findings from response, "
                "including them unvalidated"
            )
            for idx in sorted(unprocessed_indices):
                validated.append(findings[idx])

        return validated

    def _get_finding_id(self, finding: T) -> str:
        """Get identifier for logging. Override for better logging."""
        return str(finding)
