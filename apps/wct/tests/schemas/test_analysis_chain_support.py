"""Tests for analysis chain tracking support in metadata for audit purposes."""

from waivern_core.schemas import AnalysisChainEntry, BaseAnalysisOutputMetadata


class TestAnalysisChainSupport:
    """Test that analysis metadata supports audit chain tracking capabilities."""

    def test_analysis_metadata_includes_chain_tracking_field(self) -> None:
        """Test that analysis metadata includes chain tracking for audit purposes.

        Business Logic: Organisations need audit trails showing the sequence
        of analyses performed on their data for compliance and governance.
        """
        # Arrange & Act
        metadata = BaseAnalysisOutputMetadata(
            ruleset_used="test_ruleset",
            llm_validation_enabled=False,
            analyses_chain=[AnalysisChainEntry(order=1, analyser="test_analyser")],
        )

        # Assert - Chain tracking field must be present and properly typed
        assert hasattr(metadata, "analyses_chain"), (
            "Analysis metadata must include analyses_chain for audit tracking"
        )
        assert isinstance(metadata.analyses_chain, list), (
            "analyses_chain must be a list to track sequence of analyses"
        )
        assert len(metadata.analyses_chain) >= 1, (
            "analyses_chain must have at least one entry as it's now mandatory"
        )

    def test_analysis_chain_entry_supports_audit_requirements(self) -> None:
        """Test that chain entries capture essential audit information.

        Business Logic: Each step in the analysis chain must record sufficient
        information for compliance reporting and process traceability.
        """
        # Arrange & Act
        chain_entry = AnalysisChainEntry(
            order=1,
            analyser="personal_data_analyser",
        )

        # Assert - Chain entry must capture audit-required information
        assert chain_entry.order == 1, (
            "Chain entry must track sequence order for audit trail"
        )
        assert chain_entry.analyser == "personal_data_analyser", (
            "Chain entry must identify which analyser performed the step"
        )
        assert hasattr(chain_entry, "execution_timestamp"), (
            "Chain entry must capture when analysis was performed"
        )

    def test_analysis_metadata_accepts_populated_chain(self) -> None:
        """Test that analysis metadata can accept pre-populated analysis chain.

        Business Logic: Downstream analysers must be able to extend existing
        audit chains to maintain complete processing history.
        """
        # Arrange
        existing_chain = [
            AnalysisChainEntry(order=1, analyser="personal_data_analyser"),
            AnalysisChainEntry(order=2, analyser="data_subject_analyser"),
        ]

        # Act
        metadata = BaseAnalysisOutputMetadata(
            ruleset_used="processing_purposes",
            llm_validation_enabled=True,
            analyses_chain=existing_chain,
        )

        # Assert - Chain should be preserved for audit continuity
        assert len(metadata.analyses_chain) == 2, (
            "Pre-existing chain entries must be preserved"
        )
        assert metadata.analyses_chain[0].analyser == "personal_data_analyser"
        assert metadata.analyses_chain[1].analyser == "data_subject_analyser"
        assert metadata.analyses_chain[0].order == 1
        assert metadata.analyses_chain[1].order == 2

    def test_metadata_serialisation_preserves_chain_information(self) -> None:
        """Test that chain information survives serialisation for data interchange.

        Business Logic: Analysis metadata must be serialisable to JSON for
        storage, transmission, and integration with downstream systems.
        """
        # Arrange
        chain = [AnalysisChainEntry(order=1, analyser="test_analyser")]
        metadata = BaseAnalysisOutputMetadata(
            ruleset_used="test_ruleset",
            llm_validation_enabled=False,
            analyses_chain=chain,
        )

        # Act
        serialised = metadata.model_dump(mode="json")

        # Assert - Chain information must survive serialisation
        assert "analyses_chain" in serialised, (
            "Serialised metadata must include analyses_chain"
        )
        assert len(serialised["analyses_chain"]) == 1, (
            "Chain entries must be preserved in serialisation"
        )
        assert serialised["analyses_chain"][0]["analyser"] == "test_analyser", (
            "Analyser identification must survive serialisation"
        )
        assert serialised["analyses_chain"][0]["order"] == 1, (
            "Sequence order must survive serialisation"
        )

    def test_analysis_chain_order_must_be_unique_and_sequential(self) -> None:
        """Test that analysis chain entries have unique, sequential order values.

        Business Logic: Each step in the analysis chain must have a unique
        sequence number to maintain proper audit trail ordering.
        """
        # Arrange & Act
        chain = [
            AnalysisChainEntry(order=1, analyser="first_analyser"),
            AnalysisChainEntry(order=2, analyser="second_analyser"),
            AnalysisChainEntry(order=3, analyser="third_analyser"),
        ]

        metadata = BaseAnalysisOutputMetadata(
            ruleset_used="test_ruleset",
            llm_validation_enabled=False,
            analyses_chain=chain,
        )

        # Assert - Orders must be unique and sequential
        orders = [entry.order for entry in metadata.analyses_chain]
        assert orders == [1, 2, 3], "Chain orders must be unique and sequential"
        assert len(set(orders)) == len(orders), "All order values must be unique"

    def test_next_order_calculation_for_chain_extension(self) -> None:
        """Test calculation of next order number when extending existing chain.

        Business Logic: When analysers extend an existing chain, they must
        calculate the correct next order number to maintain sequence integrity.
        """
        # Arrange - Existing chain with some entries
        existing_chain = [
            AnalysisChainEntry(order=1, analyser="personal_data_analyser"),
            AnalysisChainEntry(order=2, analyser="data_subject_analyser"),
        ]

        # Act - Calculate next order (simulating what analysers should do)
        next_order = (
            max(entry.order for entry in existing_chain) + 1 if existing_chain else 1
        )

        # Create new chain entry
        new_entry = AnalysisChainEntry(
            order=next_order, analyser="processing_purpose_analyser"
        )
        extended_chain = existing_chain + [new_entry]

        metadata = BaseAnalysisOutputMetadata(
            ruleset_used="processing_purposes",
            llm_validation_enabled=False,
            analyses_chain=extended_chain,
        )

        # Assert - New entry has correct sequential order
        assert metadata.analyses_chain[-1].order == 3, (
            "New chain entry must have next sequential order"
        )
        orders = [entry.order for entry in metadata.analyses_chain]
        assert orders == [1, 2, 3], "Extended chain must maintain sequential order"
        assert len(set(orders)) == len(orders), (
            "All orders in extended chain must be unique"
        )
