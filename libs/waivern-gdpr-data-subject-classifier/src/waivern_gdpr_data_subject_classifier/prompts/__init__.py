"""Prompt generation for GDPR data subject classifier LLM validation."""

from waivern_gdpr_data_subject_classifier.prompts.risk_modifier_validation import (
    get_risk_modifier_validation_prompt,
)

__all__ = [
    "get_risk_modifier_validation_prompt",
]
