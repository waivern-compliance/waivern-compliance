"""Tests for processing purpose validation prompt.

Testing Philosophy for LLM Prompts
==================================

Prompts are treated as **configuration**, not code. We deliberately avoid testing
prompt content (e.g., "does the prompt contain 'TRUE_POSITIVE'?") because:

1. **False confidence**: String-contains tests pass even when prompts are broken.
   A prompt could contain all the "right" strings but still produce poor LLM results.

2. **Brittle tests**: Any prompt rewording breaks tests, even if the prompt improves.
   This discourages prompt iteration and optimisation.

3. **LangChain handles structure**: We use `with_structured_output()` which validates
   response structure via Pydantic models. Testing "does prompt mention finding_id"
   is redundant — the response model enforces this.

4. **Real validation is integration-level**: The only way to truly validate a prompt
   is to run it through an LLM. Unit tests for prompt content give false assurance.

What we DO test:
- **Input validation**: Empty findings should raise an error (prevents runtime failures)
- **Mode-specific branching**: If a prompt function has conditional logic (e.g.,
  conservative vs standard mode), those code branches are worth testing

This analyser's prompt HAS mode-specific branching (conservative vs standard mode,
sensitive purposes warnings), so we test those code branches in addition to input
validation.
"""

import pytest
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail

from waivern_processing_purpose_analyser.prompts.processing_purpose_validation import (
    get_processing_purpose_validation_prompt,
)
from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeIndicatorMetadata,
    ProcessingPurposeIndicatorModel,
)


class TestProcessingPurposeValidationPrompt:
    """Test processing purpose validation prompt generation.

    Tests focus on:
    - Input validation (empty findings)
    - Mode-specific branching (conservative vs standard)
    - Configurable behaviour (sensitive purposes)
    """

    def create_test_finding(
        self,
        purpose: str = "Test Purpose",
        matched_pattern: str = "test",
        evidence: list[str] | None = None,
        source: str = "test_source",
    ) -> ProcessingPurposeIndicatorModel:
        """Helper to create test finding objects."""
        evidence_list = evidence if evidence is not None else ["test evidence"]
        evidence_items = [
            BaseFindingEvidence(content=content) for content in evidence_list
        ]
        metadata = ProcessingPurposeIndicatorMetadata(source=source)

        return ProcessingPurposeIndicatorModel(
            purpose=purpose,
            matched_patterns=[
                PatternMatchDetail(pattern=matched_pattern, match_count=1)
            ],
            evidence=evidence_items,
            metadata=metadata,
        )

    # -------------------------------------------------------------------------
    # Input Validation
    # -------------------------------------------------------------------------

    def test_error_handling(self) -> None:
        """Test error handling for invalid inputs.

        Defensive check - no point calling LLM with no findings to analyse.
        """
        with pytest.raises(ValueError, match="At least one finding must be provided"):
            get_processing_purpose_validation_prompt([], "standard")

    def test_validation_mode_fallback(self) -> None:
        """Test that invalid validation modes fall back to standard behaviour.

        Tests branching: invalid mode → standard mode fallback.
        """
        findings = [self.create_test_finding()]

        prompt = get_processing_purpose_validation_prompt(findings, "invalid_mode")

        assert "STANDARD VALIDATION MODE" in prompt
        assert "CONSERVATIVE VALIDATION MODE" not in prompt
        assert '"flag_for_review"' not in prompt

    # -------------------------------------------------------------------------
    # Mode-Specific Branching (Conservative vs Standard)
    # -------------------------------------------------------------------------

    def test_conservative_mode_enables_flag_for_review_option(self) -> None:
        """Test that conservative mode includes flag_for_review action option.

        Tests branching: conservative mode adds "flag_for_review" to response format.
        """
        findings = [self.create_test_finding()]

        prompt = get_processing_purpose_validation_prompt(findings, "conservative")

        assert '"flag_for_review"' in prompt

    def test_standard_mode_excludes_flag_for_review_option(self) -> None:
        """Test that standard mode does not include flag_for_review action option.

        Tests branching: standard mode only allows "discard" action.
        """
        findings = [self.create_test_finding()]

        prompt = get_processing_purpose_validation_prompt(findings, "standard")

        assert '"flag_for_review"' not in prompt

    def test_conservative_mode_extends_reasoning_length(self) -> None:
        """Test that conservative mode allows longer reasoning explanations.

        Tests branching: mode affects reasoning word limit (120 vs 150 words).
        """
        findings = [self.create_test_finding()]

        standard_prompt = get_processing_purpose_validation_prompt(findings, "standard")
        conservative_prompt = get_processing_purpose_validation_prompt(
            findings, "conservative"
        )

        assert "max 120 words" in standard_prompt
        assert "max 150 words" in conservative_prompt

    # -------------------------------------------------------------------------
    # Configurable Behaviour (Sensitive Purposes)
    # -------------------------------------------------------------------------

    def test_privacy_sensitive_purposes_trigger_warnings(self) -> None:
        """Test that privacy-sensitive purposes trigger warnings when configured.

        Tests conditional logic: findings with purposes in sensitive_purposes list
        trigger "PRIVACY SENSITIVE" warning in prompt.
        """
        sensitive_purposes = ["AI Training", "User Analytics", "Marketing Targeting"]

        for purpose in sensitive_purposes:
            findings = [self.create_test_finding(purpose=purpose)]

            prompt = get_processing_purpose_validation_prompt(
                findings, "conservative", sensitive_purposes
            )

            assert "PRIVACY SENSITIVE" in prompt, (
                f"Purpose '{purpose}' should trigger privacy warning when configured"
            )

    def test_non_sensitive_purpose_does_not_trigger_privacy_warnings(self) -> None:
        """Test that non-sensitive purposes don't trigger privacy-sensitive warnings.

        Tests conditional logic: purposes NOT in sensitive_purposes list should
        not trigger the warning.
        """
        findings = [
            self.create_test_finding(
                purpose="Security Monitoring",
                matched_pattern="security",
            )
        ]
        sensitive_purposes = ["AI Training", "User Analytics", "Marketing Targeting"]

        prompt = get_processing_purpose_validation_prompt(
            findings, "conservative", sensitive_purposes
        )

        assert "PRIVACY SENSITIVE" not in prompt
