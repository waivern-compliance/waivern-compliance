"""Base class for compliance analysers with common functionality."""

from abc import abstractmethod
from typing import Any

from wct.analysers.base import Analyser
from wct.llm_service import LLMServiceError, LLMServiceFactory
from wct.rulesets import RulesetLoader


class BaseComplianceAnalyser(Analyser):
    """Base class for compliance analysers with shared functionality.

    This class provides common infrastructure for compliance analysers including:
    - Ruleset pattern loading
    - LLM service initialization
    - Evidence extraction with configurable context
    - Standard input schema processing
    """

    def __init__(
        self,
        ruleset_name: str,
        evidence_context_size: str = "small",
        enable_llm_validation: bool = True,
        llm_batch_size: int = 10,
    ):
        """Initialize the compliance analyser with common configuration.

        Args:
            ruleset_name: Name of the ruleset to use for analysis
            evidence_context_size: Size of context around evidence matches
                                  ('small': 50 chars, 'medium': 100 chars, 'large': 200 chars, 'full': entire content)
            enable_llm_validation: Whether to use LLM for validation (default: True)
            llm_batch_size: Number of findings to process in each LLM batch (default: 10)
        """
        super().__init__()  # Initialize logger from base class
        self.ruleset_name = ruleset_name
        self.evidence_context_size = evidence_context_size
        self.enable_llm_validation = enable_llm_validation
        self.llm_batch_size = llm_batch_size
        self._patterns = None
        self._llm_service = None

    @property
    def patterns(self) -> dict[str, Any]:
        """Get the loaded patterns, loading them if necessary."""
        if self._patterns is None:
            try:
                self._patterns = RulesetLoader.load_ruleset(self.ruleset_name)
                self.logger.info(f"Loaded ruleset: {self.ruleset_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load ruleset {self.ruleset_name}: {e}")
                # Fallback to empty patterns for graceful degradation
                self._patterns = {}
        return self._patterns

    @property
    def llm_service(self):
        """Get the LLM service, creating it if necessary."""
        if self._llm_service is None and self.enable_llm_validation:
            try:
                self._llm_service = LLMServiceFactory.create_anthropic_service()
                self.logger.info("LLM service initialized for compliance analysis")
            except LLMServiceError as e:
                self.logger.warning(
                    f"Failed to initialize LLM service: {e}. Continuing without LLM validation."
                )
                self.enable_llm_validation = False
        return self._llm_service

    def _get_context_size(self) -> int | None:
        """Get the context size in characters based on the configured level.

        Returns:
            Number of characters to include before and after each match,
            or None for full content (no truncation)
        """
        size_mapping = {"small": 50, "medium": 100, "large": 200, "full": None}
        return size_mapping.get(self.evidence_context_size.lower(), 50)

    def _extract_evidence(
        self, content: str, pattern: str, max_evidence: int = 3
    ) -> list[str]:
        """Extract evidence snippets where the pattern was found.

        Args:
            content: The full content to search in
            pattern: The pattern that was matched
            max_evidence: Maximum number of evidence snippets to collect

        Returns:
            List of unique evidence snippets showing context around matches
        """
        evidence_set = set()  # Use set to avoid duplicates
        content_lower = content.lower()
        pattern_lower = pattern.lower()

        # Find all occurrences of the pattern
        start_pos = 0
        while len(evidence_set) < max_evidence:
            match_pos = content_lower.find(pattern_lower, start_pos)
            if match_pos == -1:
                break

            # Extract context around the match
            context_size = self._get_context_size()

            if context_size is None:
                # 'full' option: include entire content without truncation
                evidence_snippet = content.strip()
            else:
                # Standard context window extraction
                context_start = max(0, match_pos - context_size)
                context_end = min(len(content), match_pos + len(pattern) + context_size)

                # Extract the evidence with context
                evidence_snippet = content[context_start:context_end].strip()

                # Add ellipsis if we truncated the context
                if context_start > 0:
                    evidence_snippet = "..." + evidence_snippet
                if context_end < len(content):
                    evidence_snippet = evidence_snippet + "..."

            # Add to set to automatically deduplicate
            evidence_set.add(evidence_snippet)

            # Move past this match to find the next occurrence
            start_pos = match_pos + 1

            # For 'full' context, only include one snippet since it contains everything
            if context_size is None:
                break

        # Convert set back to list and maintain consistent ordering
        return sorted(list(evidence_set))

    def _process_standard_input_data(
        self, data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Process standard_input schema data format.

        Handles the common pattern of iterating through data arrays
        and analyzing each content item independently.

        Args:
            data: Input data in standard_input schema format

        Returns:
            List of findings from analyzing all data items
        """
        findings = []

        if "data" in data and isinstance(data["data"], list):
            # Process each data item in the array
            for item in data["data"]:
                content = item.get("content", "")
                item_metadata = item.get("metadata", {})

                # Analyze each content piece using analyser-specific logic
                item_findings = self.analyze_content_item(content, item_metadata)
                findings.extend(item_findings)
        else:
            # Handle direct content format (fallback)
            content = data.get("content", "")
            metadata = data.get("metadata", {})
            findings = self.analyze_content_item(content, metadata)

        return findings

    @abstractmethod
    def analyze_content_item(
        self, content: str, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Analyze a single content item for compliance patterns.

        This abstract method must be implemented by subclasses to provide
        their specific analysis logic.

        Args:
            content: Text content to analyze
            metadata: Metadata about the content source

        Returns:
            List of findings for this content item
        """
        pass
