"""Tests for Runbook implementation classes (not schema validation).

These tests focus on the business logic and public API of Runbook dataclasses.
They do NOT test validation logic, which is handled by RunbookSchema tests.

Note: Some tests use empty collections to test dataclass behavior in isolation.
In production, the RunbookSchema JSON schema enforces minItems: 1 for all
arrays, so empty collections cannot occur at runtime through normal loading.
"""

import dataclasses

from wct.analysers.base import AnalyserConfig
from wct.connectors.base import ConnectorConfig
from wct.runbook import ExecutionStep, Runbook, RunbookSummary


class TestRunbookSummary:
    """Tests for RunbookSummary dataclass."""

    def test_runbook_summary_creation(self) -> None:
        """Test RunbookSummary can be created with valid data."""
        summary = RunbookSummary(
            name="Test Runbook",
            description="Test description",
            connector_count=2,
            analyser_count=3,
            execution_steps=4,
            connector_types=["mysql", "filesystem"],
            analyser_types=["personal_data", "processing_purpose"],
        )

        assert summary.name == "Test Runbook"
        assert summary.description == "Test description"
        assert summary.connector_count == 2  # noqa: PLR2004
        assert summary.analyser_count == 3.0  # noqa: PLR2004
        assert summary.execution_steps == 4  # noqa: PLR2004
        assert summary.connector_types == ["mysql", "filesystem"]
        assert summary.analyser_types == ["personal_data", "processing_purpose"]

    def test_runbook_summary_immutability(self) -> None:
        """Test RunbookSummary is frozen (immutable)."""
        summary = RunbookSummary(
            name="Test",
            description="Test",
            connector_count=1,
            analyser_count=1,
            execution_steps=1,
            connector_types=["test"],
            analyser_types=["test"],
        )

        # Should be frozen dataclass
        assert dataclasses.is_dataclass(summary)
        # Attempting to modify should raise an error (frozen=True)
        try:
            summary.name = "Modified"  # type: ignore
            assert False, "Expected frozen dataclass to prevent modification"
        except (dataclasses.FrozenInstanceError, AttributeError):
            pass  # Expected behavior


class TestExecutionStep:
    """Tests for ExecutionStep dataclass."""

    def test_execution_step_creation_with_defaults(self) -> None:
        """Test ExecutionStep creation with default context."""
        step = ExecutionStep(
            connector="test_connector",
            analyser="test_analyser",
            input_schema_name="standard_input",
            output_schema_name="personal_data_finding",
        )

        assert step.connector == "test_connector"
        assert step.analyser == "test_analyser"
        assert step.input_schema_name == "standard_input"
        assert step.output_schema_name == "personal_data_finding"
        assert step.context == {}  # Default empty dict

    def test_execution_step_creation_with_custom_context(self) -> None:
        """Test ExecutionStep creation with custom context."""
        custom_context = {"priority": "high", "timeout": 300}
        step = ExecutionStep(
            connector="test_connector",
            analyser="test_analyser",
            input_schema_name="standard_input",
            output_schema_name="personal_data_finding",
            context=custom_context,
        )

        assert step.context == custom_context

    def test_execution_step_immutability(self) -> None:
        """Test ExecutionStep is frozen (immutable)."""
        step = ExecutionStep(
            connector="test_connector",
            analyser="test_analyser",
            input_schema_name="standard_input",
            output_schema_name="personal_data_finding",
        )

        # Should be frozen dataclass
        assert dataclasses.is_dataclass(step)
        # Attempting to modify should raise an error (frozen=True)
        try:
            step.connector = "modified"  # type: ignore
            assert False, "Expected frozen dataclass to prevent modification"
        except (dataclasses.FrozenInstanceError, AttributeError):
            pass  # Expected behavior


class TestRunbook:
    """Tests for Runbook dataclass and its business logic."""

    def test_runbook_creation(self) -> None:
        """Test Runbook can be created with valid configuration data."""
        connectors = [
            ConnectorConfig(name="conn1", type="mysql", properties={}),
            ConnectorConfig(name="conn2", type="filesystem", properties={}),
        ]
        analysers = [
            AnalyserConfig(
                name="anal1", type="personal_data", properties={}, metadata={}
            ),
            AnalyserConfig(
                name="anal2", type="processing_purpose", properties={}, metadata={}
            ),
        ]
        execution = [
            ExecutionStep("conn1", "anal1", "standard_input", "personal_data_finding"),
            ExecutionStep(
                "conn2", "anal2", "source_code", "processing_purpose_finding"
            ),
        ]

        runbook = Runbook(
            name="Test Runbook",
            description="Test runbook for validation",
            connectors=connectors,
            analysers=analysers,
            execution=execution,
        )

        assert runbook.name == "Test Runbook"
        assert runbook.description == "Test runbook for validation"
        assert len(runbook.connectors) == 2  # noqa: PLR2004
        assert len(runbook.analysers) == 2  # noqa: PLR2004
        assert len(runbook.execution) == 2  # noqa: PLR2004

    def test_runbook_immutability(self) -> None:
        """Test Runbook is frozen (immutable).

        Note: Uses minimal valid configuration. In production, schema validation
        requires at least 1 connector, analyser, and execution step.
        """
        # Use minimal valid configuration (1 item each, as schema requires)
        connectors = [
            ConnectorConfig(name="test_conn", type="filesystem", properties={})
        ]
        analysers = [
            AnalyserConfig(
                name="test_anal", type="personal_data", properties={}, metadata={}
            )
        ]
        execution = [
            ExecutionStep(
                "test_conn", "test_anal", "standard_input", "personal_data_finding"
            )
        ]

        runbook = Runbook(
            name="Test",
            description="Test",
            connectors=connectors,
            analysers=analysers,
            execution=execution,
        )

        # Should be frozen dataclass
        assert dataclasses.is_dataclass(runbook)
        # Attempting to modify should raise an error (frozen=True)
        try:
            runbook.name = "Modified"  # type: ignore
            assert False, "Expected frozen dataclass to prevent modification"
        except (dataclasses.FrozenInstanceError, AttributeError):
            pass  # Expected behavior

    def test_get_summary_basic_stats(self) -> None:
        """Test get_summary returns correct basic statistics."""
        connectors = [
            ConnectorConfig(name="conn1", type="mysql", properties={}),
            ConnectorConfig(name="conn2", type="filesystem", properties={}),
        ]
        analysers = [
            AnalyserConfig(
                name="anal1", type="personal_data", properties={}, metadata={}
            ),
            AnalyserConfig(
                name="anal2", type="processing_purpose", properties={}, metadata={}
            ),
            AnalyserConfig(
                name="anal3", type="personal_data", properties={}, metadata={}
            ),
        ]
        execution = [
            ExecutionStep("conn1", "anal1", "standard_input", "personal_data_finding"),
            ExecutionStep(
                "conn2", "anal2", "source_code", "processing_purpose_finding"
            ),
        ]

        runbook = Runbook(
            name="Test Runbook",
            description="A comprehensive test runbook",
            connectors=connectors,
            analysers=analysers,
            execution=execution,
        )

        summary = runbook.get_summary()

        # Test basic properties
        assert summary.name == "Test Runbook"
        assert summary.description == "A comprehensive test runbook"

        # Test counts
        assert summary.connector_count == 2  # noqa: PLR2004
        assert summary.analyser_count == 3  # noqa: PLR2004
        assert summary.execution_steps == 2  # noqa: PLR2004

    def test_get_summary_type_deduplication(self) -> None:
        """Test get_summary correctly deduplicates connector and analyser types."""
        # Create multiple connectors of same types
        connectors = [
            ConnectorConfig(name="mysql1", type="mysql", properties={}),
            ConnectorConfig(
                name="mysql2", type="mysql", properties={}
            ),  # Duplicate type
            ConnectorConfig(name="fs1", type="filesystem", properties={}),
            ConnectorConfig(
                name="fs2", type="filesystem", properties={}
            ),  # Duplicate type
        ]

        # Create multiple analysers of same types
        analysers = [
            AnalyserConfig(
                name="pd1", type="personal_data", properties={}, metadata={}
            ),
            AnalyserConfig(
                name="pd2", type="personal_data", properties={}, metadata={}
            ),  # Duplicate type
            AnalyserConfig(
                name="pp1", type="processing_purpose", properties={}, metadata={}
            ),
        ]

        execution = [
            ExecutionStep("mysql1", "pd1", "standard_input", "personal_data_finding")
        ]

        runbook = Runbook(
            name="Deduplication Test",
            description="Test type deduplication",
            connectors=connectors,
            analysers=analysers,
            execution=execution,
        )

        summary = runbook.get_summary()

        # Should deduplicate types but preserve order (using list conversion from set)
        connector_types = summary.connector_types
        analyser_types = summary.analyser_types

        # Check that duplicates are removed
        assert (
            len(connector_types) == 2  # noqa: PLR2004
        )  # mysql, filesystem (deduplicated)
        assert (
            len(analyser_types) == 2  # noqa: PLR2004
        )  # personal_data, processing_purpose (deduplicated)

        # Check that all unique types are present
        assert set(connector_types) == {"mysql", "filesystem"}
        assert set(analyser_types) == {"personal_data", "processing_purpose"}

    def test_get_summary_empty_collections(self) -> None:
        """Test get_summary handles empty collections (theoretical edge case).

        IMPORTANT: This tests dataclass behavior in isolation. In production,
        the RunbookSchema JSON schema enforces minItems: 1, so empty collections
        cannot occur through normal runbook loading. This test verifies the
        get_summary() method's robustness in pure unit testing scenarios.
        """
        runbook = Runbook(
            name="Empty Runbook",
            description="Runbook with no components",
            connectors=[],
            analysers=[],
            execution=[],
        )

        summary = runbook.get_summary()

        assert summary.name == "Empty Runbook"
        assert summary.description == "Runbook with no components"
        assert summary.connector_count == 0
        assert summary.analyser_count == 0
        assert summary.execution_steps == 0
        assert summary.connector_types == []
        assert summary.analyser_types == []

    def test_get_summary_returns_runbook_summary_instance(self) -> None:
        """Test get_summary returns proper RunbookSummary instance."""
        # Use minimal schema-compliant configuration
        connectors = [
            ConnectorConfig(name="test_conn", type="filesystem", properties={})
        ]
        analysers = [
            AnalyserConfig(
                name="test_anal", type="personal_data", properties={}, metadata={}
            )
        ]
        execution = [
            ExecutionStep(
                "test_conn", "test_anal", "standard_input", "personal_data_finding"
            )
        ]

        runbook = Runbook(
            name="Test",
            description="Test",
            connectors=connectors,
            analysers=analysers,
            execution=execution,
        )

        summary = runbook.get_summary()
        assert isinstance(summary, RunbookSummary)
        assert dataclasses.is_dataclass(summary)
