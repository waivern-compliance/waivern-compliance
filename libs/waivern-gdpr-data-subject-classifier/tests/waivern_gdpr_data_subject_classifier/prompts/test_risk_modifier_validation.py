"""Tests for risk modifier validation prompt.

Testing Philosophy for LLM Prompts
==================================

Prompts are treated as **configuration**, not code. We deliberately avoid testing
prompt content (e.g., "does the prompt contain 'minor'?") because:

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

This classifier's prompt has no mode-specific branching, so we only test input validation.
"""

import pytest

from waivern_gdpr_data_subject_classifier.prompts import (
    get_risk_modifier_validation_prompt,
)


class TestRiskModifierValidationPrompt:
    """Test risk modifier validation prompt generation."""

    def test_empty_findings_raises_error(self) -> None:
        """Test that empty findings list raises ValueError.

        Defensive check - no point calling LLM with no findings to analyse.
        """
        with pytest.raises(ValueError, match="At least one finding must be provided"):
            get_risk_modifier_validation_prompt(findings=[], available_modifiers=[])
