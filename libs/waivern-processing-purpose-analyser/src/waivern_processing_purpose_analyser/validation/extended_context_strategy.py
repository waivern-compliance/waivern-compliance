"""Source code validation strategy for processing purpose findings.

Extends the shared ExtendedContextLLMValidationStrategy with processing
purpose-specific prompt generation, specifically for source_code schema input.
"""

from pathlib import Path
from typing import override

from waivern_analysers_shared.llm_validation import (
    ExtendedContextLLMValidationStrategy,
    SourceBatch,
)
from waivern_analysers_shared.types import LLMValidationConfig

from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeIndicatorModel,
)

from .providers import SourceCodeSourceProvider

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "batched_files_validation.md"


class SourceCodeValidationStrategy(
    ExtendedContextLLMValidationStrategy[ProcessingPurposeIndicatorModel]
):
    """Validation strategy for source_code schema findings.

    Uses full file content in prompts for richer validation context.
    Batches files by source to stay within token limits.

    Specific to source_code schema - for other schemas, different
    validation strategies would be needed.
    """

    def __init__(self, source_provider: SourceCodeSourceProvider) -> None:
        """Initialise with source provider.

        Args:
            source_provider: Provider for file paths and content.

        """
        super().__init__(source_provider)

    @override
    def get_batch_validation_prompt(
        self,
        batch: SourceBatch,
        findings_by_source: dict[str, list[ProcessingPurposeIndicatorModel]],
        source_contents: dict[str, str],
        config: LLMValidationConfig,
    ) -> str:
        """Generate validation prompt for a batch of source files.

        Args:
            batch: The batch of sources to validate.
            findings_by_source: Mapping of source IDs to their findings.
            source_contents: Mapping of source IDs to their content.
            config: LLM validation configuration.

        Returns:
            Formatted prompt string for LLM validation.

        """
        # Build source files section
        source_files_section = self._build_source_files_section(
            batch.sources, source_contents, findings_by_source
        )

        # Build findings section with finding IDs
        findings_section = self._build_findings_section(
            batch.sources, findings_by_source
        )

        # Use replace() instead of format() to avoid issues with curly braces
        # in source code content (e.g., JavaScript objects, Python dicts)
        prompt_template = _PROMPT_PATH.read_text()
        return (
            prompt_template.replace("{validation_mode}", config.llm_validation_mode)
            .replace("{source_files_section}", source_files_section)
            .replace("{findings_section}", findings_section)
        )

    def _build_source_files_section(
        self,
        sources: list[str],
        source_contents: dict[str, str],
        findings_by_source: dict[str, list[ProcessingPurposeIndicatorModel]],
    ) -> str:
        """Build the source files section of the prompt.

        Output format:
        ```
        === File: src/payments/checkout.py (3 findings) ===
        import stripe

        def process_payment(amount):
            return stripe.Charge.create(amount=amount)
        ```
        """
        sections: list[str] = []

        for source_id in sources:
            content = source_contents[source_id]
            finding_count = len(findings_by_source.get(source_id, []))
            sections.append(
                f"=== File: {source_id} ({finding_count} findings) ===\n{content}"
            )

        return "\n\n".join(sections)

    def _build_findings_section(
        self,
        sources: list[str],
        findings_by_source: dict[str, list[ProcessingPurposeIndicatorModel]],
    ) -> str:
        """Build the findings section with finding IDs.

        Output format:
        ```
        File: src/payments/checkout.py
          [a1b2c3d4-...] Purpose: Payment Processing, Patterns: stripe, checkout, Line: L42

        File: src/analytics/tracker.py
          [i9j0k1l2-...] Purpose: User Analytics, Patterns: mixpanel, track, Line: L12
        ```

        The finding ID (UUID) is used by the LLM to reference specific findings
        in its validation response.
        """
        lines: list[str] = []

        for source_id in sources:
            findings = findings_by_source.get(source_id, [])
            lines.append(f"\nFile: {source_id}")
            for finding in findings:
                line_num = finding.metadata.line_number if finding.metadata else None
                patterns = ", ".join(
                    f"{p.pattern} (×{p.match_count})" for p in finding.matched_patterns
                )
                lines.append(
                    f"  [{finding.id}] Purpose: {finding.purpose}, "
                    f"Patterns: {patterns}, Line: L{line_num}"
                )

        return "\n".join(lines)
