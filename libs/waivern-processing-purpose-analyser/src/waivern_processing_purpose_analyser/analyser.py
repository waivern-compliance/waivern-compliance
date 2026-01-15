"""Processing purpose analysis analyser for GDPR compliance."""

import importlib
import logging
import random
from collections import defaultdict
from types import ModuleType
from typing import override

from waivern_core import Analyser, InputRequirement
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import BaseLLMService

from .llm_validation_strategy import processing_purpose_validation_strategy
from .result_builder import ProcessingPurposeResultBuilder, SamplingInfo
from .schemas.types import ProcessingPurposeFindingModel, RemovedPurpose
from .types import ProcessingPurposeAnalyserConfig

logger = logging.getLogger(__name__)


class ProcessingPurposeAnalyser(Analyser):
    """Analyser for identifying data processing purposes.

    This analyser identifies and categorises data processing purposes from textual
    content to help organisations understand what they're using personal data for.
    """

    def __init__(
        self,
        config: ProcessingPurposeAnalyserConfig,
        llm_service: BaseLLMService | None = None,
    ) -> None:
        """Initialise the processing purpose analyser with dependency injection.

        Args:
            config: Configuration object with analysis settings
            llm_service: Optional LLM service for validation (injected by factory)

        """
        self._config = config
        self._llm_service = llm_service
        self._result_builder = ProcessingPurposeResultBuilder(config)

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "processing_purpose_analyser"

    def _load_reader(self, schema: Schema) -> ModuleType:
        """Dynamically import reader module.

        The reader module provides both read() and create_handler() functions,
        co-locating schema reading and handler creation.

        Args:
            schema: Input schema to load reader for

        Returns:
            Reader module with read() and create_handler() functions

        Raises:
            ModuleNotFoundError: If reader module doesn't exist for this version

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(
            f"waivern_processing_purpose_analyser.schema_readers.{module_name}"
        )

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations.

        ProcessingPurposeAnalyser accepts either standard_input OR source_code schema.
        Each is a valid alternative input.
        """
        return [
            [InputRequirement("standard_input", "1.0.0")],
            [InputRequirement("source_code", "1.0.0")],
        ]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this analyser."""
        return [Schema("processing_purpose_finding", "1.0.0")]

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process data to identify processing purposes.

        Supports multiple input schema types. The reader module for each schema
        provides both data reading and handler creation, keeping schema knowledge
        co-located.

        Args:
            inputs: List of input messages (single message expected)
            output_schema: Expected output schema

        Returns:
            Output message with processing purpose findings

        """
        logger.info("Starting processing purpose analysis")

        message = inputs[0]
        input_schema = message.schema
        logger.debug(f"Processing data with schema: {input_schema.name}")

        # Load reader and process findings
        reader = self._load_reader_module(input_schema)
        input_data = reader.read(message.content)
        handler = reader.create_handler(self._config)
        findings = handler.analyse(input_data)

        # Apply LLM validation if enabled
        sampling_info: SamplingInfo | None = None
        if self._config.llm_validation.enable_llm_validation:
            sampling_size = self._config.llm_validation.sampling_size
            if sampling_size is not None:
                # Use sampling-based validation
                validated_findings, validation_applied, sampling_info = (
                    self._validate_with_sampling(findings, message, sampling_size)
                )
            else:
                # Validate all findings
                validated_findings, validation_applied = (
                    self._validate_findings_with_llm(findings, message)
                )
        else:
            validated_findings, validation_applied = findings, False

        # Build output message
        return self._result_builder.build_output_message(
            findings,
            validated_findings,
            validation_applied,
            output_schema,
            sampling_info,
        )

    def _load_reader_module(self, schema: Schema) -> ModuleType:
        """Load reader module for the given schema.

        Args:
            schema: Input schema to load reader for

        Returns:
            Reader module

        Raises:
            ValueError: If schema is not supported

        """
        try:
            return self._load_reader(schema)
        except (ModuleNotFoundError, AttributeError) as e:
            raise ValueError(f"Unsupported input schema: {schema.name}") from e

    def _validate_findings_with_llm(
        self,
        findings: list[ProcessingPurposeFindingModel],
        input_message: Message,
    ) -> tuple[list[ProcessingPurposeFindingModel], bool]:
        """Validate findings using LLM.

        Args:
            findings: List of findings to validate
            input_message: Input message (validation strategy decides batching approach)

        Returns:
            Tuple of (validated findings, validation_was_applied)

        """
        if not findings:
            return findings, False

        if not self._llm_service:
            logger.warning("LLM service unavailable, returning original findings")
            return findings, False

        try:
            validated_findings, validation_succeeded = (
                processing_purpose_validation_strategy(
                    findings,
                    self._config.llm_validation,
                    self._llm_service,
                    input_message,
                )
            )
            return validated_findings, validation_succeeded
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            logger.warning("Returning original findings due to validation error")
            return findings, False

    def _validate_with_sampling(
        self,
        findings: list[ProcessingPurposeFindingModel],
        input_message: Message,
        sampling_size: int,
    ) -> tuple[list[ProcessingPurposeFindingModel], bool, SamplingInfo]:
        """Validate findings using purpose-based sampling.

        Samples N findings per purpose group and validates only those samples.
        Decision logic:
        1. If ALL samples for a purpose are FALSE_POSITIVE → remove entire group
        2. If ANY sample is TRUE_POSITIVE → keep the group (remove FP samples only)

        Args:
            findings: All findings from pattern matching
            input_message: Input message for validation context
            sampling_size: Number of samples per purpose group

        Returns:
            Tuple of (validated findings, validation applied, sampling info)

        """
        if not findings:
            return (
                findings,
                False,
                SamplingInfo(
                    samples_per_purpose=sampling_size,
                    samples_validated=0,
                    removed_purposes=[],
                ),
            )

        # 1. Group findings by purpose
        purpose_groups: dict[str, list[ProcessingPurposeFindingModel]] = defaultdict(
            list
        )
        for finding in findings:
            purpose_groups[finding.purpose].append(finding)

        logger.info(
            f"Sampling validation: {len(findings)} findings in "
            f"{len(purpose_groups)} purpose groups"
        )

        # 2. Sample N findings from each group
        sampled_findings: list[ProcessingPurposeFindingModel] = []
        sample_to_purpose: dict[int, str] = {}  # Map sample index to purpose

        for purpose, group_findings in purpose_groups.items():
            samples = random.sample(
                group_findings, min(sampling_size, len(group_findings))
            )
            for sample in samples:
                sample_to_purpose[len(sampled_findings)] = purpose
                sampled_findings.append(sample)

        logger.info(f"Selected {len(sampled_findings)} samples for LLM validation")

        # 3. Validate only the samples
        validated_samples, validation_applied = self._validate_findings_with_llm(
            sampled_findings, input_message
        )

        if not validation_applied:
            # Validation failed - return original findings
            return (
                findings,
                False,
                SamplingInfo(
                    samples_per_purpose=sampling_size,
                    samples_validated=0,
                    removed_purposes=[],
                ),
            )

        # 4. Identify which samples were kept (true positives)
        # Use finding.id (string UUID) not id() since validation returns new model instances
        validated_sample_ids = {f.id for f in validated_samples}

        # Group validated samples by purpose
        purpose_sample_results: dict[str, list[bool]] = defaultdict(list)
        for i, sample in enumerate(sampled_findings):
            purpose = sample_to_purpose[i]
            is_true_positive = sample.id in validated_sample_ids
            purpose_sample_results[purpose].append(is_true_positive)

        # 5. Determine which purposes to remove
        removed_purposes: list[RemovedPurpose] = []
        purposes_to_remove: set[str] = set()

        for purpose, results in purpose_sample_results.items():
            if not any(results):
                # ALL samples are false positives → remove entire purpose group
                purposes_to_remove.add(purpose)
                removed_purposes.append(
                    RemovedPurpose(
                        purpose=purpose,
                        reason="All sampled findings are false positives",
                        require_review=True,
                    )
                )
                logger.info(
                    f"Removing purpose '{purpose}': all {len(results)} samples "
                    "are false positives"
                )

        # 6. Build final validated findings list
        validated_findings = self._build_validated_findings_list(
            findings, sampled_findings, validated_sample_ids, purposes_to_remove
        )

        logger.info(
            f"Sampling validation complete: {len(findings)} → {len(validated_findings)} "
            f"findings ({len(removed_purposes)} purposes removed)"
        )

        sampling_info = SamplingInfo(
            samples_per_purpose=sampling_size,
            samples_validated=len(sampled_findings),
            removed_purposes=removed_purposes,
        )

        return validated_findings, True, sampling_info

    def _mark_finding_validated(
        self, finding: ProcessingPurposeFindingModel
    ) -> ProcessingPurposeFindingModel:
        """Mark a finding as LLM validated.

        Args:
            finding: Finding to mark

        Returns:
            New finding with validation marker in metadata context

        """
        # Create updated metadata with validation marker
        if finding.metadata:
            updated_context = dict(finding.metadata.context)
            updated_context["processing_purpose_llm_validated"] = True

            updated_metadata = finding.metadata.model_copy(
                update={"context": updated_context}
            )
            return finding.model_copy(update={"metadata": updated_metadata})

        return finding

    def _build_validated_findings_list(
        self,
        findings: list[ProcessingPurposeFindingModel],
        sampled_findings: list[ProcessingPurposeFindingModel],
        validated_sample_ids: set[str],
        purposes_to_remove: set[str],
    ) -> list[ProcessingPurposeFindingModel]:
        """Build the final list of validated findings after sampling.

        Args:
            findings: All original findings
            sampled_findings: Findings that were sampled for validation
            validated_sample_ids: Set of finding IDs (UUIDs) for samples that passed
            purposes_to_remove: Purpose names whose groups should be removed entirely

        Returns:
            List of findings to keep, with sampled true positives marked as validated

        """
        # Use finding IDs for membership check (not object identity)
        sampled_finding_ids = {f.id for f in sampled_findings}
        validated_findings: list[ProcessingPurposeFindingModel] = []

        for finding in findings:
            if finding.purpose in purposes_to_remove:
                # Skip - entire purpose group removed
                continue

            if finding.id in sampled_finding_ids:
                # This was a sample - check if it was validated
                if finding.id in validated_sample_ids:
                    # Mark as LLM validated
                    validated_finding = self._mark_finding_validated(finding)
                    validated_findings.append(validated_finding)
                # else: sample was false positive, skip it
            else:
                # Non-sampled finding - keep by inference (purpose group is valid)
                validated_findings.append(finding)

        return validated_findings
