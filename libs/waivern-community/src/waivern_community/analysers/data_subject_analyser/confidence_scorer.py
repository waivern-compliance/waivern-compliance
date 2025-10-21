"""Confidence scoring for data subject classification.

CONFIDENCE SCORING SYSTEM EXPLAINED
===================================

The data subject confidence scoring system provides a numerical measure (0-100)
of how certain we are about a classification based on the patterns we matched.

HOW IT WORKS:
1. Each rule in the ruleset has a confidence_weight (1-50 points)
2. When content matches patterns, we sum the weights of all matched rules
3. The total is capped at 100 to create a percentage-like score
4. Higher scores = more evidence = more confident classification

RULE WEIGHT GUIDELINES:
- Primary indicators (45-50 points): Strong, direct evidence
  Example: "employee_id", "patient_record", "customer_account"
- Secondary indicators (25-35 points): Supporting evidence
  Example: "salary", "medical_appointment", "subscription_status"
- Contextual indicators (5-15 points): Weak but relevant evidence
  Example: "company_email", "user_profile", "contact_info"

EXAMPLE CALCULATION:
Content: "employee john doe staff_id 12345 salary benefits"
Matched rules:
- employee_direct_role_fields (patterns: "employee", "staff_id") → 45 points
- employee_hr_system_indicators (patterns: "salary", "benefits") → 30 points
Total score: min(45 + 30, 100) = 75

INTERPRETATION:
- 90-100: Very high confidence (multiple strong indicators)
- 70-89:  High confidence (strong primary + secondary evidence)
- 50-69:  Medium confidence (primary indicator or multiple secondary)
- 30-49:  Low-medium confidence (weak primary or strong contextual)
- 1-29:   Low confidence (only contextual indicators)
- 0:      No confidence (no patterns matched)

Note: The system provides only raw scores. Consumers can apply their own
thresholds based on their risk tolerance and compliance requirements.
"""

from waivern_rulesets.data_subjects import DataSubjectRule


class DataSubjectConfidenceScorer:
    """Confidence scorer for data subject classification.

    Implements the GDPR confidence scoring algorithm for data subject categories
    using weighted rule matching.
    """

    def calculate_confidence(self, matched_rules: list[DataSubjectRule]) -> int:
        """Calculate confidence score from matched rules.

        Implements algorithm: sum(rule.confidence_weight for rule in matched_rules),
        capped at 100%.

        Args:
            matched_rules: List of rules that were matched for a data subject

        Returns:
            Confidence score (0-100)

        """
        if not matched_rules:
            return 0

        # Calculate total confidence score (sum of weights, capped at 100)
        total_score = sum(rule.confidence_weight for rule in matched_rules)
        return min(total_score, 100)
