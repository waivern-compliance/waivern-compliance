"""End-to-end integration tests for SQLite connector with compliance data."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from waivern_sqlite import SQLiteConnectorFactory

from wct.executor import Executor
from wct.schemas import Schema


@pytest.fixture(autouse=True)
def _mock_llm_service(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    """Mock LLM service factory for integration tests.

    These tests use runbooks with enable_llm_validation: false, so LLM service
    is not actually needed. This fixture allows tests to run without API keys.

    This fixture is automatically used by all tests in this module via autouse=True.
    """
    # Create a mock LLM service
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = True

    # Patch LLMServiceFactory.create() to return our mock
    def mock_create(self):
        return mock_llm

    monkeypatch.setattr("waivern_llm.di.factory.LLMServiceFactory.create", mock_create)


class TestSQLiteE2EIntegration:
    """End-to-end integration tests for SQLite connector."""

    @pytest.fixture
    def compliance_database_path(self) -> str:
        """Return path to SQLite compliance test database."""
        db_path = Path(__file__).parent / "test_data" / "sqlite_compliance_test.db"

        # Ensure database exists
        if not db_path.exists():
            pytest.skip(f"SQLite compliance test database not found at {db_path}")

        return str(db_path)

    def test_sqlite_connector_extracts_compliance_data_successfully(
        self, compliance_database_path: str
    ):
        """SQLite connector successfully extracts data from compliance database."""
        # Arrange
        properties = {
            "database_path": compliance_database_path,
            "max_rows_per_table": 20,
        }
        factory = SQLiteConnectorFactory()
        connector = factory.create(properties)
        schema = Schema("standard_input", "1.0.0")

        # Act
        message = connector.extract(schema)

        # Assert - Verify message structure
        assert message is not None
        assert message.schema == schema
        assert message.content is not None
        assert isinstance(message.content, dict)

        # Assert - Verify database metadata
        assert "metadata" in message.content
        metadata = message.content["metadata"]
        assert metadata["connector_type"] == "sqlite_connector"
        assert "database_schema" in metadata
        assert metadata["database_schema"]["database_name"] == "sqlite_compliance_test"

        # Assert - Verify data structure (granular cell-level data)
        assert "data" in message.content
        data_items = message.content["data"]
        assert isinstance(data_items, list), (
            "Data should be a list of granular data items"
        )
        assert len(data_items) > 0, "Should extract data items"

        # Assert - Verify granular data item structure
        first_item = data_items[0]
        assert "content" in first_item, "Each data item should have content"
        assert "metadata" in first_item, "Each data item should have metadata"

        # Assert - Verify data item metadata structure
        item_metadata = first_item["metadata"]
        assert item_metadata["connector_type"] == "sqlite_connector"
        assert "table_name" in item_metadata
        assert "column_name" in item_metadata
        assert "schema_name" in item_metadata
        assert item_metadata["schema_name"] == "sqlite_compliance_test"

        # Assert - Verify expected tables are represented in data items
        expected_tables = {"customers", "employees", "orders", "support_tickets"}
        actual_tables = {item["metadata"]["table_name"] for item in data_items}
        assert expected_tables.issubset(actual_tables), (
            f"Missing tables: {expected_tables - actual_tables}"
        )

        # Assert - Verify customer data is extracted
        customer_items = [
            item for item in data_items if item["metadata"]["table_name"] == "customers"
        ]
        assert len(customer_items) > 0, "Should extract customer data items"

        # Assert - Verify employee data contains sensitive information
        employee_items = [
            item for item in data_items if item["metadata"]["table_name"] == "employees"
        ]
        assert len(employee_items) > 0, "Should extract employee data items"

        # Check for sensitive HR columns
        employee_columns = {item["metadata"]["column_name"] for item in employee_items}
        sensitive_columns = {"emergency_contact_name", "national_id", "salary"}
        found_sensitive = sensitive_columns.intersection(employee_columns)
        assert len(found_sensitive) > 0, (
            f"Should find sensitive HR columns, found: {employee_columns}"
        )

        # Assert - Verify support tickets contain customer communications
        ticket_items = [
            item
            for item in data_items
            if item["metadata"]["table_name"] == "support_tickets"
        ]
        assert len(ticket_items) > 0, "Should extract support ticket data items"

        # Find ticket content with sensitive information
        ticket_content = [
            item["content"]
            for item in ticket_items
            if item["content"] and "password" in str(item["content"]).lower()
        ]
        assert len(ticket_content) > 0, (
            "Should find ticket items with sensitive communication content"
        )

    def test_sqlite_connector_respects_row_limits(self, compliance_database_path: str):
        """SQLite connector respects max_rows_per_table configuration."""
        # Arrange
        row_limit = 3
        properties = {
            "database_path": compliance_database_path,
            "max_rows_per_table": row_limit,
        }
        factory = SQLiteConnectorFactory()
        connector = factory.create(properties)
        schema = Schema("standard_input", "1.0.0")

        # Act
        message = connector.extract(schema)

        # Assert - Verify row limits are respected per table
        data_items = message.content["data"]

        # Group data items by table to verify row limits
        table_item_counts = {}
        for item in data_items:
            table_name = item["metadata"]["table_name"]
            table_item_counts[table_name] = table_item_counts.get(table_name, 0) + 1

        # Each table should have at most row_limit * column_count items
        # (Since we have granular cell-level extraction)
        for table_name, item_count in table_item_counts.items():
            # Get column count for this table from database schema
            table_schema = next(
                (
                    table
                    for table in message.content["metadata"]["database_schema"][
                        "tables"
                    ]
                    if table["name"] == table_name
                ),
                None,
            )
            assert table_schema is not None, f"Table schema not found for {table_name}"

            column_count = len(table_schema["columns"])
            expected_max_items = row_limit * column_count

            assert item_count <= expected_max_items, (
                f"Table {table_name} has {item_count} data items, "
                f"expected at most {expected_max_items} "
                f"(row_limit={row_limit} * columns={column_count})"
            )


class TestSQLiteE2EPipeline:
    """Test SQLite connector integration with WCT pipeline."""

    def test_lamp_stack_lite_runbook_executes_successfully(self) -> None:
        """LAMP_stack_lite.yaml runbook runs without errors."""

        # Create executor with built-in components
        executor = Executor.create_with_built_ins()

        # Use the existing LAMP_stack_lite.yaml runbook
        runbook_path = Path("apps/wct/runbooks/samples/LAMP_stack_lite.yaml")
        assert runbook_path.exists(), f"Runbook not found: {runbook_path}"

        # Execute the complete pipeline
        results = executor.execute_runbook(runbook_path)

        # Should have 5 execution steps as defined in LAMP_stack_lite.yaml
        assert len(results) == 5, f"Expected 5 analysis results, got {len(results)}"

        # All steps should succeed
        for result in results:
            assert result.success, (
                f"Analysis '{result.analysis_name}' failed: {result.error_message}"
            )
            assert result.data is not None
            assert isinstance(result.data, dict)

    def test_lamp_stack_lite_finds_expected_personal_data(self) -> None:
        """Runbook detects minimum expected personal data patterns."""
        executor = Executor.create_with_built_ins()
        runbook_path = Path("apps/wct/runbooks/samples/LAMP_stack_lite.yaml")

        results = executor.execute_runbook(runbook_path)

        # Find personal data analysis results
        personal_data_results = [
            r for r in results if "personal_data_finding" in r.output_schema.lower()
        ]

        # Should have 2 personal data analyses (SQLite DB + filesystem)
        assert len(personal_data_results) == 2

        # Check that personal data was found in both analyses
        for result in personal_data_results:
            assert result.success
            findings = result.data.get("findings", [])

            # Should find at least some personal data patterns
            # (The SQLite test database contains 150+ instances of personal data)
            assert len(findings) > 0, (
                f"No personal data findings in {result.analysis_name}. "
                f"Expected findings from test data."
            )

            # Check structure of findings
            if findings:
                finding = findings[0]
                assert "matched_patterns" in finding
                assert "evidence" in finding
                assert "data_type" in finding

    def test_lamp_stack_lite_finds_expected_processing_purposes(self) -> None:
        """Runbook detects expected processing purpose patterns."""
        executor = Executor.create_with_built_ins()
        runbook_path = Path("apps/wct/runbooks/samples/LAMP_stack_lite.yaml")

        results = executor.execute_runbook(runbook_path)

        # Find processing purpose analysis results
        processing_purpose_results = [
            r
            for r in results
            if "processing_purpose_finding" in r.output_schema.lower()
        ]

        # Should have 2 processing purpose analyses (SQLite DB + filesystem)
        assert len(processing_purpose_results) == 2

        # Check that processing purposes were analyzed (may or may not find matches)
        for result in processing_purpose_results:
            assert result.success
            assert "findings" in result.data
            findings = result.data["findings"]

            # Structure should be correct even if no findings
            if findings:
                finding = findings[0]
                assert "matched_patterns" in finding
                assert "evidence" in finding
                assert "purpose" in finding
