"""Provider implementations for LLM validation.

These providers implement the shared protocols from waivern-analysers-shared,
adapting them to PersonalDataAnalyser's domain.

Testing rationale:
    These provider classes have NO dedicated unit tests because:

    1. They implement trivial behaviour (simple attribute access)
    2. The type checker validates protocol compliance with ConcernProvider[T]
    3. The grouping logic that uses these providers is tested in
       waivern-analysers-shared/tests/llm_validation/test_grouping.py

    If you add a provider with non-trivial logic (e.g., derived values,
    conditional logic, error handling), you SHOULD add tests for that behaviour.
"""

from waivern_personal_data_analyser.schemas.types import PersonalDataIndicatorModel


class PersonalDataConcernProvider:
    """Groups findings by personal data category.

    The 'concern' for personal data analysis is the data category
    (e.g., "email", "phone", "health").
    """

    @property
    def concern_key(self) -> str:
        """Return the attribute name for grouping."""
        return "category"

    def get_concern(self, finding: PersonalDataIndicatorModel) -> str:
        """Extract category from finding.

        Args:
            finding: The finding to extract category from.

        Returns:
            The personal data category.

        """
        return finding.category
