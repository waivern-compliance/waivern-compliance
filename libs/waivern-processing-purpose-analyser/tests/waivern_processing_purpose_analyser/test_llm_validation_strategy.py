"""Tests for SourceCodeValidationStrategy.

These tests verify behaviour specific to the SourceCodeValidationStrategy.
Base class behaviour (token-aware batching, error handling) is tested in
waivern_analysers_shared/llm_validation/test_extended_context_strategy.py.
"""

from unittest.mock import Mock

import pytest
from waivern_analysers_shared.llm_validation import SourceBatch
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail

from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeFindingMetadata,
    ProcessingPurposeFindingModel,
)
from waivern_processing_purpose_analyser.validation.extended_context_strategy import (
    SourceCodeValidationStrategy,
)
from waivern_processing_purpose_analyser.validation.providers import (
    SourceCodeSourceProvider,
)


def _make_finding(
    purpose: str = "Payment Processing",
    purpose_category: str = "OPERATIONAL",
    pattern: str = "stripe",
    source: str = "src/payments/checkout.py",
    line_number: int = 42,
) -> ProcessingPurposeFindingModel:
    """Create a finding with minimal boilerplate."""
    return ProcessingPurposeFindingModel(
        purpose=purpose,
        purpose_category=purpose_category,
        matched_patterns=[PatternMatchDetail(pattern=pattern, match_count=1)],
        evidence=[BaseFindingEvidence(content=f"Content: {pattern}")],
        metadata=ProcessingPurposeFindingMetadata(
            source=source, line_number=line_number
        ),
    )


class TestSourceCodeValidationStrategy:
    """Test suite for SourceCodeValidationStrategy-specific behaviour."""

    @pytest.fixture
    def source_provider(self) -> Mock:
        """Create mock source provider."""
        return Mock(spec=SourceCodeSourceProvider)

    @pytest.fixture
    def strategy(self, source_provider: Mock) -> SourceCodeValidationStrategy:
        """Create strategy instance."""
        return SourceCodeValidationStrategy(source_provider)

    @pytest.fixture
    def config(self) -> LLMValidationConfig:
        """Create standard LLM configuration."""
        return LLMValidationConfig(
            enable_llm_validation=True,
            llm_batch_size=10,
            llm_validation_mode="standard",
        )

    @pytest.fixture
    def sample_findings(self) -> list[ProcessingPurposeFindingModel]:
        """Create two sample findings for testing."""
        return [
            _make_finding(
                "Payment Processing",
                "FINANCIAL",
                "stripe",
                "src/payments/checkout.py",
                42,
            ),
            _make_finding(
                "User Analytics",
                "ANALYTICS",
                "mixpanel",
                "src/analytics/tracker.py",
                12,
            ),
        ]

    def test_prompt_includes_finding_ids_for_response_matching(
        self,
        strategy: SourceCodeValidationStrategy,
        config: LLMValidationConfig,
        sample_findings: list[ProcessingPurposeFindingModel],
    ) -> None:
        """Prompt includes finding IDs so LLM can reference them in response."""
        batch = SourceBatch(
            sources=["src/payments/checkout.py", "src/analytics/tracker.py"],
            estimated_tokens=1000,
        )
        findings_by_source = {
            "src/payments/checkout.py": [sample_findings[0]],
            "src/analytics/tracker.py": [sample_findings[1]],
        }
        source_contents = {
            "src/payments/checkout.py": "import stripe\n\ndef checkout(): pass",
            "src/analytics/tracker.py": "import mixpanel\n\ndef track(): pass",
        }

        prompt = strategy.get_batch_validation_prompt(
            batch, findings_by_source, source_contents, config
        )

        # Should include finding IDs (UUIDs) for response matching
        assert sample_findings[0].id in prompt
        assert sample_findings[1].id in prompt

    def test_prompt_includes_source_file_contents(
        self,
        strategy: SourceCodeValidationStrategy,
        config: LLMValidationConfig,
        sample_findings: list[ProcessingPurposeFindingModel],
    ) -> None:
        """Prompt includes full file contents for context-aware validation."""
        batch = SourceBatch(
            sources=["src/payments/checkout.py"],
            estimated_tokens=500,
        )
        findings_by_source = {"src/payments/checkout.py": [sample_findings[0]]}
        source_contents = {
            "src/payments/checkout.py": "import stripe\n\ndef process_payment(amount):\n    return stripe.Charge.create(amount=amount)"
        }

        prompt = strategy.get_batch_validation_prompt(
            batch, findings_by_source, source_contents, config
        )

        # Should include the actual source code
        assert "import stripe" in prompt
        assert "process_payment" in prompt
        assert "stripe.Charge.create" in prompt

    def test_prompt_includes_finding_details(
        self,
        strategy: SourceCodeValidationStrategy,
        config: LLMValidationConfig,
        sample_findings: list[ProcessingPurposeFindingModel],
    ) -> None:
        """Prompt includes purpose, patterns, and line numbers."""
        batch = SourceBatch(
            sources=["src/payments/checkout.py"],
            estimated_tokens=500,
        )
        findings_by_source = {"src/payments/checkout.py": [sample_findings[0]]}
        source_contents = {"src/payments/checkout.py": "import stripe"}

        prompt = strategy.get_batch_validation_prompt(
            batch, findings_by_source, source_contents, config
        )

        # Should include purpose and patterns
        assert "Payment Processing" in prompt
        assert "stripe" in prompt
        # Should include line number
        assert "L42" in prompt
