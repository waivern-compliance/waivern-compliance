"""Provider implementations for LLM validation.

These providers implement the shared protocols from waivern-analysers-shared,
adapting them to DataSubjectAnalyser's domain.

Testing rationale:
    These provider classes have NO dedicated unit tests because:

    1. They implement trivial behaviour (simple attribute access)
    2. The type checker validates protocol compliance with ConcernProvider[T]
    3. The grouping logic that uses these providers is tested in
       waivern-analysers-shared/tests/llm_validation/test_grouping.py
    4. This pattern is consistent with PersonalDataConcernProvider and
       ProcessingPurposeConcernProvider, which also have no dedicated tests

    If you add a provider with non-trivial logic (e.g., derived values,
    conditional logic, error handling), you SHOULD add tests for that behaviour.
"""

from waivern_data_subject_analyser.schemas import DataSubjectIndicatorModel


class DataSubjectConcernProvider:
    """Groups findings by data subject category.

    The 'concern' for data subject analysis is the subject category
    (e.g., "Customer", "Employee", "Patient").

    This class implements the ConcernProvider[DataSubjectIndicatorModel] protocol
    from waivern-analysers-shared. Protocol compliance is validated by the type
    checker - no runtime checks or tests are needed for this simple implementation.
    """

    @property
    def concern_key(self) -> str:
        """Return the attribute name for grouping."""
        return "subject_category"

    def get_concern(self, finding: DataSubjectIndicatorModel) -> str:
        """Extract subject category from finding.

        Args:
            finding: The finding to extract subject category from.

        Returns:
            The data subject category (e.g., "Customer", "Employee").

        """
        return finding.subject_category
