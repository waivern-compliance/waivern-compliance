"""Provider implementations for LLM validation.

These providers implement the shared protocols from waivern-analysers-shared,
adapting them to PersonalDataAnalyser's domain.
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
