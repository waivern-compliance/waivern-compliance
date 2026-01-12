"""Abstract base class for batched-files LLM validation strategy.

Provides token-aware batching of findings by file for efficient LLM validation.
Concrete implementations define how to extract file paths from findings and
how to generate validation prompts.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from waivern_core.schemas import BaseFindingModel
from waivern_llm import BaseLLMService

from .decision_engine import ValidationDecisionEngine
from .file_content import FileContentProvider, FileInfo
from .json_utils import extract_json_from_llm_response
from .models import LLMValidationResultListAdapter

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
class FileValidationResult[T]:
    """Result of file-based validation.

    Separates validated findings from those that couldn't be processed,
    allowing the caller to decide how to handle unvalidated findings
    (e.g., fallback to finding-based validation).

    Type parameter T is the finding type.
    """

    validated_findings: list[T]
    """Findings that were successfully validated via file-based batching."""

    unvalidated_findings: list[T]
    """Findings that couldn't be validated (oversized/missing files)."""

    all_batches_succeeded: bool
    """Whether all batch validations succeeded without errors."""


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


class BatchedFilesStrategyBase[T: BaseFindingModel](ABC):
    """Abstract base class for batched-files validation strategies.

    Provides token-aware batching infrastructure. Concrete implementations
    define analyser-specific behaviour (file path extraction, prompt generation).

    Type parameter T is the finding type, must be a BaseFindingModel subclass.
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
        validation_mode: str,
    ) -> str:
        """Generate the LLM validation prompt for a batch.

        Args:
            batch: The batch of files to validate.
            findings_by_file: Mapping of file paths to their findings.
            file_contents: Mapping of file paths to their content.
            validation_mode: Validation mode ("standard", "conservative", "aggressive").

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
        validation_mode: str = "standard",
    ) -> FileValidationResult[T]:
        """Validate findings using file-based batching with full file content.

        Orchestrates the complete validation flow:
        1. Group findings by source file
        2. Create token-aware batches
        3. For each batch, generate prompt with full file content and call LLM
        4. Parse responses and filter findings

        Findings from oversized/missing files are returned separately as
        unvalidated, allowing the caller to decide how to handle them
        (e.g., fallback to finding-based validation).

        Args:
            findings: List of findings to validate.
            file_provider: Provider for file content.
            max_tokens_per_batch: Maximum tokens per batch.
            llm_service: LLM service for validation calls.
            validation_mode: Validation mode ("standard", "conservative", "aggressive").

        Returns:
            FileValidationResult with validated and unvalidated findings.

        """
        if not findings:
            logger.debug("No findings to validate")
            return FileValidationResult(
                validated_findings=[],
                unvalidated_findings=[],
                all_batches_succeeded=True,
            )

        # Initialise result tracking outside try block to preserve progress
        validated_findings: list[T] = []
        unvalidated_findings: list[T] = []
        all_batches_succeeded = True
        processed_finding_ids: set[str] = set()

        try:
            # Group findings by file
            findings_by_file = self._group_findings_by_file(findings)

            if not findings_by_file:
                logger.warning("No findings could be grouped by file")
                return FileValidationResult(
                    validated_findings=[],
                    unvalidated_findings=list(findings),
                    all_batches_succeeded=False,
                )

            # Create token-aware batches
            batching_result = self._create_token_aware_batches(
                findings_by_file=findings_by_file,
                file_provider=file_provider,
                max_tokens_per_batch=max_tokens_per_batch,
            )

            # Validate each batch
            for batch_idx, batch in enumerate(batching_result.batches):
                # Track all findings in batch as processed (whether validated or filtered)
                batch_all_findings = [
                    f for file_path in batch.files for f in findings_by_file[file_path]
                ]
                for f in batch_all_findings:
                    processed_finding_ids.add(f.id)

                try:
                    batch_findings = self._validate_batch(
                        batch=batch,
                        findings_by_file=findings_by_file,
                        file_provider=file_provider,
                        llm_service=llm_service,
                        validation_mode=validation_mode,
                    )
                    validated_findings.extend(batch_findings)
                except Exception as e:
                    logger.error(f"Batch {batch_idx + 1} validation failed: {e}")
                    # Failed batch findings go to unvalidated
                    unvalidated_findings.extend(batch_all_findings)
                    all_batches_succeeded = False

            # Collect findings from oversized and missing files (unvalidated)
            self._collect_unbatchable_findings(
                file_paths=batching_result.oversized_files,
                reason="oversized",
                findings_by_file=findings_by_file,
                unvalidated_findings=unvalidated_findings,
                processed_finding_ids=processed_finding_ids,
            )
            self._collect_unbatchable_findings(
                file_paths=batching_result.missing_files,
                reason="missing",
                findings_by_file=findings_by_file,
                unvalidated_findings=unvalidated_findings,
                processed_finding_ids=processed_finding_ids,
            )

        except Exception as e:
            logger.error(f"File-based validation failed: {e}")
            all_batches_succeeded = False

        # Add any unprocessed findings to unvalidated (preserves progress on failure)
        for finding in findings:
            if finding.id not in processed_finding_ids:
                unvalidated_findings.append(finding)

        logger.debug(
            f"Validation complete: {len(validated_findings)} validated, "
            f"{len(unvalidated_findings)} unvalidated"
        )

        return FileValidationResult(
            validated_findings=validated_findings,
            unvalidated_findings=unvalidated_findings,
            all_batches_succeeded=all_batches_succeeded,
        )

    def _collect_unbatchable_findings(
        self,
        file_paths: list[str],
        reason: str,
        findings_by_file: dict[str, list[T]],
        unvalidated_findings: list[T],
        processed_finding_ids: set[str],
    ) -> None:
        """Collect findings from files that cannot be batched.

        Args:
            file_paths: List of file paths that couldn't be batched.
            reason: Reason for exclusion (e.g., "oversized", "missing").
            findings_by_file: Mapping of file paths to their findings.
            unvalidated_findings: List to append unvalidated findings to.
            processed_finding_ids: Set to track processed finding IDs.

        """
        for file_path in file_paths:
            file_findings = findings_by_file[file_path]
            logger.warning(
                f"{len(file_findings)} findings from {reason} "
                f"file cannot be validated: {file_path}"
            )
            for finding in file_findings:
                unvalidated_findings.append(finding)
                processed_finding_ids.add(finding.id)

    def _validate_batch(
        self,
        batch: FileBatch[T],
        findings_by_file: dict[str, list[T]],
        file_provider: FileContentProvider,
        llm_service: BaseLLMService,
        validation_mode: str,
    ) -> list[T]:
        """Validate a single batch of files.

        Args:
            batch: The batch to validate.
            findings_by_file: Mapping of file paths to findings.
            file_provider: Provider for loading file content.
            llm_service: LLM service for validation.
            validation_mode: Validation mode ("standard", "conservative", "aggressive").

        Returns:
            List of validated findings from this batch.

        """
        # Build flat list of findings in batch order for index mapping
        batch_findings: list[T] = []
        for file_path in batch.files:
            batch_findings.extend(findings_by_file[file_path])

        # Load content for files in this batch
        file_contents: dict[str, str] = {}
        for file_path in batch.files:
            content = file_provider.get_file_content(file_path)
            if content is None:
                raise RuntimeError(f"Content unavailable for batched file: {file_path}")
            file_contents[file_path] = content

        # Generate prompt
        prompt = self.get_batch_validation_prompt(
            batch=batch,
            findings_by_file=findings_by_file,
            file_contents=file_contents,
            validation_mode=validation_mode,
        )

        # Call LLM
        logger.debug(f"Validating batch with {len(batch_findings)} findings")
        response = llm_service.analyse_data("", prompt)
        logger.debug(f"LLM raw response (first 2000 chars):\n{response[:2000]}")

        # Parse response
        try:
            clean_json = extract_json_from_llm_response(response)
            logger.debug(f"Extracted JSON (first 500 chars): {clean_json[:500]}")
            validation_results = json.loads(clean_json)
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"JSON extraction/parsing failed: {e}")
            logger.error(f"Full LLM response was:\n{response}")
            raise

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
        # Validate response structure using strongly-typed model
        try:
            llm_validation_results = LLMValidationResultListAdapter.validate_python(
                validation_results
            )
        except Exception as e:
            logger.error(f"Failed to validate LLM response structure: {e}")
            # Re-raise so caller marks batch as failed and findings go to unvalidated
            # This ensures metadata accurately reflects validation failures
            raise

        # Build lookup from finding ID to finding
        findings_by_id = {f.id: f for f in findings}
        validated: list[T] = []
        processed_ids: set[str] = set()

        for result in llm_validation_results:
            finding = findings_by_id.get(result.finding_id)

            if finding is None:
                logger.error(
                    f"LLM returned unknown finding_id: {result.finding_id}. "
                    "Aborting validation for this batch."
                )
                return list(findings)

            processed_ids.add(result.finding_id)

            # Log validation decision
            ValidationDecisionEngine.log_validation_decision(result, finding)

            if ValidationDecisionEngine.should_keep_finding(result, finding):
                validated.append(finding)

        # Fail-safe: include findings not mentioned by LLM
        unprocessed_ids = set(findings_by_id.keys()) - processed_ids
        if unprocessed_ids:
            logger.warning(
                f"LLM omitted {len(unprocessed_ids)} findings from response, "
                "including them unvalidated"
            )
            for finding_id in unprocessed_ids:
                validated.append(findings_by_id[finding_id])

        return validated
