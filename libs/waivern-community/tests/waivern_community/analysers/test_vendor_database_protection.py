"""Tests for vendor database protection and data integrity.

This module tests the critical protection mechanisms for the Consensu.org
vendor database to prevent data loss, corruption, and ensure safe import operations.

Following TDD principles: each test addresses a single concern and genuine business requirement.
"""

import importlib.util
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


class TestVendorDatabaseProtection:
    """Test suite for vendor database protection mechanisms."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def temp_json_path(self):
        """Create temporary JSON file path."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = Path(f.name)
        yield json_path
        if json_path.exists():
            json_path.unlink()

    @pytest.fixture
    def valid_json_data(self):
        """Minimal valid JSON structure matching TCF format."""
        return {
            "gvlSpecificationVersion": 3,
            "vendorListVersion": 123,
            "tcfPolicyVersion": 5,
            "lastUpdated": "2025-09-04T16:00:24Z",
            "purposes": {},
            "specialPurposes": {},
            "features": {},
            "specialFeatures": {},
            "dataCategories": {},
            "stacks": {},
            "vendors": {},
        }

    # Category 1: Database Protection Tests

    def test_database_not_deleted_without_explicit_force(self, temp_db_path):
        """Test that existing database is not deleted without explicit --force flag.

        Business Requirement: Protect existing database from accidental deletion
        Critical: Prevents catastrophic data loss from production database
        """
        # Create an existing database file with identifiable content
        original_content = "existing database content - should not be deleted"
        temp_db_path.write_text(original_content)
        assert temp_db_path.exists(), "Setup: Database file should exist before test"

        # Import the main function to test using importlib
        vendor_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )
        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", vendor_db_path
        )
        assert spec is not None and spec.loader is not None, (
            f"Could not load module from {vendor_db_path}"
        )
        create_consensu_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_consensu_db_module)
        main = create_consensu_db_module.main

        # Mock sys.argv to simulate running: python create_consensu_db.py --db-path /temp/path
        # (without --force flag)
        test_args = ["create_consensu_db.py", "--db-path", str(temp_db_path)]

        with patch.object(sys, "argv", test_args):
            main()

        # Verify the existing database file was NOT deleted
        assert temp_db_path.exists(), (
            "Existing database should not be deleted without --force flag"
        )

        # Verify the original content is preserved (not overwritten)
        current_content = temp_db_path.read_text()
        assert current_content == original_content, (
            "Original database content should be preserved"
        )

    def test_database_creation_fails_when_file_locked(self, temp_db_path):
        """Test that database creation fails when file is locked by another process.

        Business Requirement: Prevent database corruption during concurrent access
        Critical: Multiple processes could corrupt the database simultaneously
        """
        # Create an existing database file
        temp_db_path.write_text("existing database")

        # Import the main function to test using importlib
        vendor_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )
        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", vendor_db_path
        )
        assert spec is not None and spec.loader is not None, (
            f"Could not load module from {vendor_db_path}"
        )
        create_consensu_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_consensu_db_module)
        main = create_consensu_db_module.main

        # Mock sqlite3.connect to simulate a locked database (raises OperationalError)
        # We need to patch it in the create_consensu_db module, not the sqlite3 module directly
        with patch.object(
            create_consensu_db_module.sqlite3,
            "connect",
            side_effect=sqlite3.OperationalError("database is locked"),
        ):
            # Mock sys.argv to simulate running with --force flag (to attempt creation)
            test_args = [
                "create_consensu_db.py",
                "--db-path",
                str(temp_db_path),
                "--force",
            ]

            with patch.object(sys, "argv", test_args):
                # This should raise an exception or handle the locked database gracefully
                with pytest.raises(
                    sqlite3.OperationalError, match="database is locked"
                ):
                    main()

        # The test reaching here means the exception was properly raised
        # The file was deleted by --force before the connection attempt, which is expected behavior

    def test_import_creates_backup_before_modification(
        self, temp_db_path, temp_json_path, valid_json_data
    ):
        """Test that import process creates backup before modifying database.

        Business Requirement: Enable recovery from failed imports
        Critical: Currently no recovery mechanism exists for partial failures
        """
        # Create an existing SQLite database file with proper schema using ConsensuDbCreator
        # Import the create_consensu_db module to create a proper database
        create_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )
        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", create_db_path
        )
        assert spec is not None and spec.loader is not None
        create_consensu_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_consensu_db_module)

        # Create the database with proper schema
        creator = create_consensu_db_module.ConsensuDbCreator(temp_db_path)
        creator.create_database()

        # Add some test data to verify backup preservation
        conn = sqlite3.connect(temp_db_path)
        conn.execute(
            "INSERT INTO metadata (gvl_specification_version, vendor_list_version, tcf_policy_version, last_updated) VALUES (99, 999, 9, '2025-01-01T00:00:00Z')"
        )
        conn.commit()
        conn.close()

        # Get the size of the original database for later verification
        original_size = temp_db_path.stat().st_size

        # Create a valid JSON file for import
        temp_json_path.write_text(json.dumps(valid_json_data))

        # Import the import_consensu_data main function using importlib
        vendor_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "import_consensu_data.py"
        )
        spec = importlib.util.spec_from_file_location(
            "import_consensu_data", vendor_db_path
        )
        assert spec is not None and spec.loader is not None, (
            f"Could not load module from {vendor_db_path}"
        )
        import_consensu_data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(import_consensu_data_module)
        main = import_consensu_data_module.main

        # Mock sys.argv to simulate running: python import_consensu_data.py --json-file temp.json --db-file temp.db
        test_args = [
            "import_consensu_data.py",
            "--json-file",
            str(temp_json_path),
            "--db-file",
            str(temp_db_path),
        ]

        with patch.object(sys, "argv", test_args):
            main()

        # Check that a timestamped backup file was created before modification
        # Format: database.db.backup.YYYYMMDD_HHMMSS
        backup_pattern = f"{temp_db_path.name}.backup.*"
        backup_files = list(temp_db_path.parent.glob(backup_pattern))
        assert len(backup_files) == 1, (
            f"Expected exactly one backup file matching {backup_pattern}, found {len(backup_files)}"
        )

        backup_path = backup_files[0]
        assert backup_path.exists(), "Backup file should be created before import"

        # Verify backup name follows timestamp format (database.db.backup.YYYYMMDD_HHMMSS)
        backup_name = backup_path.name
        assert backup_name.startswith(f"{temp_db_path.name}.backup."), (
            "Backup should have timestamped name"
        )
        timestamp_part = backup_name.split(".backup.")[-1]
        assert len(timestamp_part) == 15, (
            "Timestamp should be YYYYMMDD_HHMMSS format (15 chars)"
        )
        assert "_" in timestamp_part, "Timestamp should have underscore separator"

        # Verify backup is a valid database with original size
        backup_size = backup_path.stat().st_size
        assert backup_size == original_size, (
            "Backup should preserve original database content"
        )

        # Verify we can connect to the backup as a valid SQLite database
        backup_conn = sqlite3.connect(backup_path)
        cursor = backup_conn.execute(
            "SELECT gvl_specification_version FROM metadata WHERE id = 1"
        )
        backup_data = cursor.fetchone()
        backup_conn.close()

        assert backup_data is not None, "Backup should contain original data"
        assert backup_data[0] == 99, (
            "Backup should preserve original test data (gvl_specification_version=99)"
        )

    # Category 2: Data Integrity Protection Tests

    def test_import_rejects_invalid_json_structure(self, temp_db_path, temp_json_path):
        """Test that import rejects JSON with invalid structure.

        Business Requirement: Prevent database corruption from malformed data
        Critical: Invalid JSON could corrupt database silently
        """
        # Create a proper database with existing data
        create_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )
        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", create_db_path
        )
        assert spec is not None and spec.loader is not None
        create_consensu_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_consensu_db_module)

        # Create database with proper schema
        creator = create_consensu_db_module.ConsensuDbCreator(temp_db_path)
        creator.create_database()

        # Add some test data to verify it's preserved after failed import
        conn = sqlite3.connect(temp_db_path)
        conn.execute(
            "INSERT INTO metadata (gvl_specification_version, vendor_list_version, tcf_policy_version, last_updated) VALUES (99, 999, 9, '2025-01-01T00:00:00Z')"
        )
        conn.commit()
        conn.close()

        # Create invalid JSON file - missing required TCF structure
        invalid_json_data = {
            "invalidField": "this is not a valid TCF structure",
            "missingRequired": "fields",
        }
        temp_json_path.write_text(json.dumps(invalid_json_data))

        # Import the import_consensu_data main function
        vendor_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "import_consensu_data.py"
        )
        spec = importlib.util.spec_from_file_location(
            "import_consensu_data", vendor_db_path
        )
        assert spec is not None and spec.loader is not None
        import_consensu_data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(import_consensu_data_module)
        main = import_consensu_data_module.main

        # Mock sys.argv to simulate running import with invalid JSON
        test_args = [
            "import_consensu_data.py",
            "--json-file",
            str(temp_json_path),
            "--db-file",
            str(temp_db_path),
        ]

        # The import should reject invalid JSON structure with improved error handling
        with patch.object(sys, "argv", test_args):
            result = main()
            assert result == 4, (
                "Import should return exit code 4 for missing required fields"
            )

        # Verify original database data is preserved (not corrupted)
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.execute(
            "SELECT gvl_specification_version FROM metadata WHERE id = 1"
        )
        preserved_data = cursor.fetchone()
        conn.close()

        assert preserved_data is not None, (
            "Original database data should be preserved after failed import"
        )
        assert preserved_data[0] == 99, (
            "Original test data should be unchanged after failed import"
        )

    def test_import_rejects_missing_required_fields(self, temp_db_path, temp_json_path):
        """Test that import rejects JSON missing required TCF fields.

        Business Requirement: Ensure data completeness for compliance reporting
        Critical: Missing fields would break compliance functionality
        """
        # Create a proper database with existing data
        create_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )
        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", create_db_path
        )
        assert spec is not None and spec.loader is not None
        create_consensu_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_consensu_db_module)

        # Create database with proper schema
        creator = create_consensu_db_module.ConsensuDbCreator(temp_db_path)
        creator.create_database()

        # Add some test data to verify it's preserved after failed import
        conn = sqlite3.connect(temp_db_path)
        conn.execute(
            "INSERT INTO metadata (gvl_specification_version, vendor_list_version, tcf_policy_version, last_updated) VALUES (99, 999, 9, '2025-01-01T00:00:00Z')"
        )
        conn.commit()
        conn.close()

        # Import the import_consensu_data main function
        vendor_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "import_consensu_data.py"
        )
        spec = importlib.util.spec_from_file_location(
            "import_consensu_data", vendor_db_path
        )
        assert spec is not None and spec.loader is not None
        import_consensu_data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(import_consensu_data_module)
        main = import_consensu_data_module.main

        # Test each required field individually
        required_fields = [
            "gvlSpecificationVersion",
            "vendorListVersion",
            "tcfPolicyVersion",
            "lastUpdated",
        ]

        base_valid_data = {
            "gvlSpecificationVersion": 3,
            "vendorListVersion": 123,
            "tcfPolicyVersion": 5,
            "lastUpdated": "2025-09-04T16:00:24Z",
            "purposes": {},
            "specialPurposes": {},
            "features": {},
            "specialFeatures": {},
            "dataCategories": {},
            "stacks": {},
            "vendors": {},
        }

        for missing_field in required_fields:
            # Create JSON data missing one required field
            incomplete_data = base_valid_data.copy()
            del incomplete_data[missing_field]
            temp_json_path.write_text(json.dumps(incomplete_data))

            # Mock sys.argv to simulate running import with incomplete JSON
            test_args = [
                "import_consensu_data.py",
                "--json-file",
                str(temp_json_path),
                "--db-file",
                str(temp_db_path),
            ]

            # The import should reject JSON missing required field with improved error handling
            with patch.object(sys, "argv", test_args):
                result = main()
                assert result == 4, (
                    f"Import should return exit code 4 for missing field: {missing_field}"
                )

        # Verify original database data is preserved after all failed imports
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.execute(
            "SELECT gvl_specification_version FROM metadata WHERE id = 1"
        )
        preserved_data = cursor.fetchone()
        conn.close()

        assert preserved_data is not None, (
            "Original database data should be preserved after failed imports"
        )
        assert preserved_data[0] == 99, (
            "Original test data should be unchanged after failed imports"
        )

    def test_import_validates_data_types_match_schema(
        self, temp_db_path, temp_json_path
    ):
        """Test that import validates data types match expected schema.

        Business Requirement: Prevent type mismatch errors in downstream analysis
        Important: Type mismatches could break WCT analysis components
        """
        # Create valid database with proper schema
        create_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )
        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", create_db_path
        )
        assert spec is not None and spec.loader is not None
        create_consensu_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_consensu_db_module)

        # Create database with proper schema
        creator = create_consensu_db_module.ConsensuDbCreator(temp_db_path)
        creator.create_database()

        # Load the import_consensu_data module dynamically
        vendor_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "import_consensu_data.py"
        )
        spec = importlib.util.spec_from_file_location(
            "import_consensu_data", vendor_db_path
        )
        assert spec is not None and spec.loader is not None, (
            f"Could not load module from {vendor_db_path}"
        )
        import_consensu_data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(import_consensu_data_module)
        main = import_consensu_data_module.main

        # Test case 1: String where integer expected (vendor ID)
        invalid_json_string_id = {
            "gvlSpecificationVersion": 3,
            "vendorListVersion": 1,
            "tcfPolicyVersion": 4,
            "lastUpdated": "2024-01-01T00:00:00Z",
            "vendors": {
                "not_a_number": {  # String ID instead of integer
                    "name": "Test Vendor",
                    "usesCookies": True,
                    "cookieRefresh": False,
                    "usesNonCookieAccess": False,
                }
            },
        }

        temp_json_path.write_text(json.dumps(invalid_json_string_id))

        # Should fail with type conversion error (ValueError during int() conversion)
        with patch.object(
            sys,
            "argv",
            [
                "import_consensu_data.py",
                "--json-file",
                str(temp_json_path),
                "--db-file",
                str(temp_db_path),
            ],
        ):
            # Improved error handling should return exit code 3 for ValueError
            result = main()
            assert result == 3, (
                "Import should return exit code 3 for data type validation errors"
            )

        # TODO: Test more data type validation scenarios
        # Note: The current implementation validates integer conversion for vendor IDs
        # which demonstrates the system has type validation capabilities

    def test_import_handles_oversized_json_gracefully(
        self, temp_db_path, temp_json_path
    ):
        """Test that import handles oversized JSON files gracefully.

        Business Requirement: System stability under resource constraints
        Important: Prevents system crashes from memory exhaustion
        """
        # Create database first
        create_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )

        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", create_db_path
        )
        if spec is None or spec.loader is None:
            pytest.skip(
                f"Could not load create_consensu_db module from {create_db_path}"
            )
        create_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_db_module)

        creator = create_db_module.ConsensuDbCreator(temp_db_path)
        creator.create_database()

        # Create a very large JSON file (simulate oversized data)
        # We'll create a JSON with thousands of vendors to test memory handling
        oversized_data: dict[str, Any] = {
            "gvlSpecificationVersion": 3,
            "vendorListVersion": 999,
            "tcfPolicyVersion": 5,
            "lastUpdated": "2025-09-04T16:00:24Z",
            "purposes": {
                str(i): {
                    "name": f"Purpose {i}",
                    "description": f"Description for purpose {i}",
                    "illustrations": [],
                }
                for i in range(1, 12)
            },
            "specialPurposes": {
                str(i): {
                    "name": f"Special Purpose {i}",
                    "description": f"Description for special purpose {i}",
                    "illustrations": [],
                }
                for i in range(1, 4)
            },
            "features": {
                str(i): {
                    "name": f"Feature {i}",
                    "description": f"Description for feature {i}",
                    "illustrations": [],
                }
                for i in range(1, 4)
            },
            "specialFeatures": {
                str(i): {
                    "name": f"Special Feature {i}",
                    "description": f"Description for special feature {i}",
                    "illustrations": [],
                }
                for i in range(1, 3)
            },
            "dataCategories": {
                str(i): {
                    "name": f"Data Category {i}",
                    "description": f"Description for data category {i}",
                }
                for i in range(1, 12)
            },
            "stacks": {},
            "vendors": {},
        }

        # Generate thousands of vendors to create a large JSON
        for vendor_id in range(1, 5001):  # 5000 vendors
            oversized_data["vendors"][str(vendor_id)] = {
                "name": f"Test Vendor {vendor_id}" + "x" * 1000,  # Large vendor names
                "usesCookies": True,
                "cookieRefresh": False,
                "usesNonCookieAccess": True,
                "purposes": list(range(1, 12)),  # All purposes
                "legIntPurposes": list(range(1, 12)),
                "flexiblePurposes": [],
                "specialPurposes": [1, 2, 3],
                "features": [1, 2, 3],
                "specialFeatures": [1, 2],
                "dataDeclaration": list(range(1, 12)),
                "urls": [
                    {
                        "langId": "en",
                        "privacy": f"https://vendor{vendor_id}.com/privacy" + "x" * 500,
                        "legIntClaim": f"https://vendor{vendor_id}.com/legal"
                        + "x" * 500,
                    }
                ],
                "dataRetention": {
                    "stdRetention": 365,
                    "purposes": {str(p): 365 for p in range(1, 12)},
                    "specialPurposes": {str(p): 365 for p in range(1, 4)},
                },
            }

        with open(temp_json_path, "w", encoding="utf-8") as f:
            json.dump(oversized_data, f)

        # Import the data
        import_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "import_consensu_data.py"
        )

        # Test that import handles oversized file gracefully (no memory crash)
        with patch(
            "sys.argv",
            [
                "import_consensu_data.py",
                "--json-file",
                str(temp_json_path),
                "--db-file",
                str(temp_db_path),
            ],
        ):
            spec = importlib.util.spec_from_file_location(
                "import_consensu_data", import_db_path
            )
            if spec is None or spec.loader is None:
                pytest.skip(
                    f"Could not load import_consensu_data module from {import_db_path}"
                )
            import_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(import_module)

            # Should complete without memory errors or crashes
            result = import_module.main()

            # Should succeed (return 0) despite large file size
            assert result == 0

            # Verify data was actually imported
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM vendors")
            vendor_count = cursor.fetchone()[0]
            conn.close()

            # Should have imported all 5000 vendors
            assert vendor_count == 5000

    # Category 3: Import Process Safety Tests

    def test_transaction_rollback_on_constraint_violation(
        self, temp_db_path, temp_json_path
    ):
        """Test that transactions rollback completely on constraint violations.

        Business Requirement: Maintain database consistency during failed imports
        Critical: Foreign key violations could leave database inconsistent
        """
        # Create a proper database with existing data
        create_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )
        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", create_db_path
        )
        assert spec is not None and spec.loader is not None
        create_consensu_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_consensu_db_module)

        # Create database with proper schema
        creator = create_consensu_db_module.ConsensuDbCreator(temp_db_path)
        creator.create_database()

        # Add some test data to verify it's preserved after failed import
        conn = sqlite3.connect(temp_db_path)
        conn.execute(
            "INSERT INTO metadata (gvl_specification_version, vendor_list_version, tcf_policy_version, last_updated) VALUES (99, 999, 9, '2025-01-01T00:00:00Z')"
        )
        conn.commit()
        original_metadata_count = conn.execute(
            "SELECT COUNT(*) FROM metadata"
        ).fetchone()[0]
        conn.close()

        # Create JSON data that will cause constraint violations
        # This data has vendors referencing non-existent purposes (foreign key violation)
        constraint_violating_data = {
            "gvlSpecificationVersion": 3,
            "vendorListVersion": 123,
            "tcfPolicyVersion": 5,
            "lastUpdated": "2025-09-04T16:00:24Z",
            "purposes": {
                "1": {
                    "id": 1,
                    "name": "Test Purpose",
                    "description": "Test description",
                    "illustrations": [],
                }
            },
            "specialPurposes": {},
            "features": {},
            "specialFeatures": {},
            "dataCategories": {},
            "stacks": {},
            "vendors": {
                "100": {
                    "id": 100,
                    "name": "Test Vendor",
                    "purposes": [
                        999
                    ],  # This purpose ID doesn't exist - will cause foreign key violation
                    "legIntPurposes": [],
                    "flexiblePurposes": [],
                    "specialPurposes": [],
                    "features": [],
                    "specialFeatures": [],
                    "dataDeclaration": [],
                    "urls": [],
                    "usesCookies": False,
                    "cookieRefresh": False,
                    "usesNonCookieAccess": False,
                }
            },
        }
        temp_json_path.write_text(json.dumps(constraint_violating_data))

        # Import the import_consensu_data main function
        vendor_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "import_consensu_data.py"
        )
        spec = importlib.util.spec_from_file_location(
            "import_consensu_data", vendor_db_path
        )
        assert spec is not None and spec.loader is not None
        import_consensu_data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(import_consensu_data_module)
        main = import_consensu_data_module.main

        # Mock sys.argv to simulate running import with constraint-violating JSON
        test_args = [
            "import_consensu_data.py",
            "--json-file",
            str(temp_json_path),
            "--db-file",
            str(temp_db_path),
        ]

        # The import should fail due to constraint violation with improved error handling
        with patch.object(sys, "argv", test_args):
            result = main()
            assert result == 5, (
                "Import should return exit code 5 for database constraint violations"
            )

        # Verify that NO partial data was committed - complete rollback occurred
        conn = sqlite3.connect(temp_db_path)

        # Check that original metadata count is unchanged (no new metadata added)
        current_metadata_count = conn.execute(
            "SELECT COUNT(*) FROM metadata"
        ).fetchone()[0]
        assert current_metadata_count == original_metadata_count, (
            "Metadata count should be unchanged after rollback"
        )

        # Check that no purposes were added from the failed import
        purpose_count = conn.execute("SELECT COUNT(*) FROM purposes").fetchone()[0]
        assert purpose_count == 0, "No purposes should have been added due to rollback"

        # Check that no vendors were added from the failed import
        vendor_count = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
        assert vendor_count == 0, "No vendors should have been added due to rollback"

        # Verify original test data is still there
        cursor = conn.execute(
            "SELECT gvl_specification_version FROM metadata WHERE id = 1"
        )
        preserved_data = cursor.fetchone()
        conn.close()

        assert preserved_data is not None, (
            "Original database data should be preserved after rollback"
        )
        assert preserved_data[0] == 99, (
            "Original test data should be unchanged after rollback"
        )

    def _setup_comprehensive_test_data(self, temp_db_path):
        """Helper to set up comprehensive test data across multiple tables."""
        # Create database with proper schema
        create_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )
        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", create_db_path
        )
        assert spec is not None and spec.loader is not None
        create_consensu_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_consensu_db_module)

        creator = create_consensu_db_module.ConsensuDbCreator(temp_db_path)
        creator.create_database()

        # Add comprehensive test data
        conn = sqlite3.connect(temp_db_path)
        conn.execute(
            "INSERT INTO metadata (gvl_specification_version, vendor_list_version, tcf_policy_version, last_updated) VALUES (99, 999, 9, '2025-01-01T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO purposes (id, name, description, illustrations) VALUES (1, 'Test Purpose', 'Test Description', '[]')"
        )
        conn.execute(
            "INSERT INTO purposes (id, name, description, illustrations) VALUES (2, 'Another Purpose', 'Another Description', '[]')"
        )
        conn.execute(
            "INSERT INTO vendors (id, name, uses_cookies, cookie_refresh, uses_non_cookie_access) VALUES (50, 'Existing Vendor', 1, 0, 1)"
        )
        conn.execute(
            "INSERT INTO vendor_purposes (vendor_id, purpose_id) VALUES (50, 1)"
        )
        conn.execute(
            "INSERT INTO vendor_purposes (vendor_id, purpose_id) VALUES (50, 2)"
        )
        conn.execute(
            "INSERT INTO vendor_urls (vendor_id, lang_id, privacy_url) VALUES (50, 'en', 'https://example.com/privacy')"
        )
        conn.commit()
        conn.close()

    def _capture_original_data_state(self, temp_db_path):
        """Helper to capture original data state for verification."""
        conn = sqlite3.connect(temp_db_path)
        original_state = {
            "metadata_count": conn.execute("SELECT COUNT(*) FROM metadata").fetchone()[
                0
            ],
            "purposes_count": conn.execute("SELECT COUNT(*) FROM purposes").fetchone()[
                0
            ],
            "vendors_count": conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0],
            "vendor_purposes_count": conn.execute(
                "SELECT COUNT(*) FROM vendor_purposes"
            ).fetchone()[0],
            "vendor_urls_count": conn.execute(
                "SELECT COUNT(*) FROM vendor_urls"
            ).fetchone()[0],
            "metadata": conn.execute(
                "SELECT gvl_specification_version, vendor_list_version FROM metadata WHERE id = 1"
            ).fetchone(),
            "vendor_name": conn.execute(
                "SELECT name FROM vendors WHERE id = 50"
            ).fetchone()[0],
            "purpose_names": [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM purposes ORDER BY id"
                ).fetchall()
            ],
        }
        conn.close()
        return original_state

    def _verify_data_preservation(self, temp_db_path, original_state):
        """Helper to verify all original data is preserved exactly."""
        conn = sqlite3.connect(temp_db_path)

        # Check table counts
        assert (
            conn.execute("SELECT COUNT(*) FROM metadata").fetchone()[0]
            == original_state["metadata_count"]
        )
        assert (
            conn.execute("SELECT COUNT(*) FROM purposes").fetchone()[0]
            == original_state["purposes_count"]
        )
        assert (
            conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
            == original_state["vendors_count"]
        )
        assert (
            conn.execute("SELECT COUNT(*) FROM vendor_purposes").fetchone()[0]
            == original_state["vendor_purposes_count"]
        )
        assert (
            conn.execute("SELECT COUNT(*) FROM vendor_urls").fetchone()[0]
            == original_state["vendor_urls_count"]
        )

        # Check specific data values
        current_metadata = conn.execute(
            "SELECT gvl_specification_version, vendor_list_version FROM metadata WHERE id = 1"
        ).fetchone()
        assert current_metadata == original_state["metadata"]

        current_vendor_name = conn.execute(
            "SELECT name FROM vendors WHERE id = 50"
        ).fetchone()[0]
        assert current_vendor_name == original_state["vendor_name"]

        current_purpose_names = [
            row[0]
            for row in conn.execute("SELECT name FROM purposes ORDER BY id").fetchall()
        ]
        assert current_purpose_names == original_state["purpose_names"]

        # Verify relationships and URLs
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM vendor_purposes WHERE vendor_id = 50"
            ).fetchone()[0]
            == 2
        )
        assert (
            conn.execute(
                "SELECT privacy_url FROM vendor_urls WHERE vendor_id = 50"
            ).fetchone()[0]
            == "https://example.com/privacy"
        )

        conn.close()

    def test_import_preserves_existing_data_on_failure(
        self, temp_db_path, temp_json_path
    ):
        """Test that existing data is preserved when import fails.

        Business Requirement: Prevent data loss during import failures
        Critical: Failed import should not corrupt existing working database
        """
        # Set up comprehensive test data
        self._setup_comprehensive_test_data(temp_db_path)
        original_state = self._capture_original_data_state(temp_db_path)

        # Create invalid JSON that will cause import to fail
        invalid_json_data = {
            "gvlSpecificationVersion": 3,
            # Missing "vendorListVersion" - will cause KeyError
            "tcfPolicyVersion": 5,
            "lastUpdated": "2025-09-04T16:00:24Z",
            "purposes": {},
            "specialPurposes": {},
            "features": {},
            "specialFeatures": {},
            "dataCategories": {},
            "stacks": {},
            "vendors": {},
        }
        temp_json_path.write_text(json.dumps(invalid_json_data))

        # Import the import_consensu_data main function
        vendor_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "import_consensu_data.py"
        )
        spec = importlib.util.spec_from_file_location(
            "import_consensu_data", vendor_db_path
        )
        assert spec is not None and spec.loader is not None
        import_consensu_data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(import_consensu_data_module)

        # Run failed import and verify data preservation
        test_args = [
            "import_consensu_data.py",
            "--json-file",
            str(temp_json_path),
            "--db-file",
            str(temp_db_path),
        ]
        with patch.object(sys, "argv", test_args):
            result = import_consensu_data_module.main()
            assert result == 4, (
                "Import should return exit code 4 for missing required field"
            )

        # Verify ALL existing data is completely preserved
        self._verify_data_preservation(temp_db_path, original_state)

    def test_incremental_update_only_modifies_changed_records(
        self, temp_db_path, temp_json_path
    ):
        """Test that incremental update only modifies changed records.

        Business Requirement: Efficient updates without unnecessary data churn
        Important: Current system blindly overwrites all data
        """
        # Create database with proper schema
        create_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )
        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", create_db_path
        )
        assert spec is not None and spec.loader is not None
        create_consensu_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_consensu_db_module)

        creator = create_consensu_db_module.ConsensuDbCreator(temp_db_path)
        creator.create_database()

        # Load the import_consensu_data module
        vendor_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "import_consensu_data.py"
        )
        spec = importlib.util.spec_from_file_location(
            "import_consensu_data", vendor_db_path
        )
        assert spec is not None and spec.loader is not None
        import_consensu_data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(import_consensu_data_module)
        main = import_consensu_data_module.main

        # Initial import with original data
        initial_data: dict[str, Any] = {
            "gvlSpecificationVersion": 3,
            "vendorListVersion": 100,
            "tcfPolicyVersion": 5,
            "lastUpdated": "2025-01-01T10:00:00Z",
            "purposes": {
                "1": {
                    "name": "Store data",
                    "description": "Store and access data",
                    "illustrations": [],
                }
            },
            "specialPurposes": {},
            "features": {},
            "specialFeatures": {},
            "dataCategories": {},
            "stacks": {},
            "vendors": {
                "1": {
                    "name": "Test Vendor",
                    "usesCookies": True,
                    "cookieRefresh": False,
                    "usesNonCookieAccess": False,
                    "purposes": [1],
                },
                "2": {
                    "name": "Another Vendor",
                    "usesCookies": False,
                    "cookieRefresh": False,
                    "usesNonCookieAccess": True,
                },
            },
        }

        temp_json_path.write_text(json.dumps(initial_data))

        # Perform initial import
        with patch.object(
            sys,
            "argv",
            [
                "import_consensu_data.py",
                "--json-file",
                str(temp_json_path),
                "--db-file",
                str(temp_db_path),
            ],
        ):
            result = main()
            assert result == 0, "Initial import should succeed"

        # Capture timestamps and checksums after initial import
        conn = sqlite3.connect(temp_db_path)

        # Add timestamp tracking to track when records were last modified
        # Note: SQLite doesn't have built-in timestamp tracking, so we'll use metadata
        original_metadata = conn.execute(
            "SELECT gvl_specification_version, vendor_list_version, tcf_policy_version, last_updated FROM metadata"
        ).fetchall()

        # Count check (optional): can verify totals haven't changed unexpectedly
        _vendor_count = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
        _purpose_count = conn.execute("SELECT COUNT(*) FROM purposes").fetchone()[0]

        # Get specific vendor data to verify only changed ones are modified
        vendor1_original = conn.execute(
            "SELECT name, uses_cookies FROM vendors WHERE id = 1"
        ).fetchone()
        vendor2_original = conn.execute(
            "SELECT name, uses_cookies FROM vendors WHERE id = 2"
        ).fetchone()

        conn.close()

        # Second import with ONLY vendor 1 changed (vendor 2 unchanged)
        updated_data = initial_data.copy()
        updated_data["vendorListVersion"] = 101  # Increment version
        updated_data["lastUpdated"] = "2025-01-01T12:00:00Z"  # New timestamp
        # Only change vendor 1's name
        updated_data["vendors"]["1"]["name"] = "Modified Test Vendor"
        # Vendor 2 remains exactly the same

        temp_json_path.write_text(json.dumps(updated_data))

        # Perform incremental update
        with patch.object(
            sys,
            "argv",
            [
                "import_consensu_data.py",
                "--json-file",
                str(temp_json_path),
                "--db-file",
                str(temp_db_path),
            ],
        ):
            result = main()
            assert result == 0, "Incremental update should succeed"

        # Verify incremental update behavior
        conn = sqlite3.connect(temp_db_path)

        # Check that metadata was updated (this should change)
        new_metadata = conn.execute(
            "SELECT gvl_specification_version, vendor_list_version, tcf_policy_version, last_updated FROM metadata"
        ).fetchall()

        # Verify metadata actually changed
        assert new_metadata != original_metadata, "Metadata should be updated"
        assert new_metadata[0][1] == 101, "Vendor list version should be updated to 101"

        # Check vendor changes
        vendor1_updated = conn.execute(
            "SELECT name, uses_cookies FROM vendors WHERE id = 1"
        ).fetchone()
        vendor2_updated = conn.execute(
            "SELECT name, uses_cookies FROM vendors WHERE id = 2"
        ).fetchone()

        conn.close()

        # Verify only vendor 1 was modified
        assert vendor1_updated[0] == "Modified Test Vendor", (
            "Vendor 1 name should be updated"
        )
        assert vendor1_original != vendor1_updated, "Vendor 1 should have changed"

        # CRITICAL TEST: Vendor 2 should be identical (no unnecessary modification)
        # This tests whether the system does incremental updates or blind overwrites
        # Current expectation: system likely does blind overwrite (test may fail initially)
        assert vendor2_updated == vendor2_original, (
            f"Vendor 2 should remain unchanged. Original: {vendor2_original}, "
            f"Updated: {vendor2_updated}. System should do incremental updates, not blind overwrites."
        )

    def test_import_reports_detailed_validation_errors(
        self, temp_db_path, temp_json_path, capsys
    ):
        """Test that import provides detailed validation error reports.

        Business Requirement: Enable debugging and data quality improvement
        Important: Operators need to understand why imports fail
        """
        # Create database first
        create_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )

        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", create_db_path
        )
        if spec is None or spec.loader is None:
            pytest.skip(
                f"Could not load create_consensu_db module from {create_db_path}"
            )
        create_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_db_module)

        creator = create_db_module.ConsensuDbCreator(temp_db_path)
        creator.create_database()

        # Create JSON with missing required field (should trigger KeyError)
        invalid_data = {
            "gvlSpecificationVersion": 3,
            "vendorListVersion": 123,
            "tcfPolicyVersion": 5,
            # Missing "lastUpdated" field - required field
            "purposes": {},
            "specialPurposes": {},
            "features": {},
            "specialFeatures": {},
            "dataCategories": {},
            "stacks": {},
            "vendors": {},
        }

        with open(temp_json_path, "w", encoding="utf-8") as f:
            json.dump(invalid_data, f)

        # Import the data and capture output
        import_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "import_consensu_data.py"
        )

        with patch(
            "sys.argv",
            [
                "import_consensu_data.py",
                "--json-file",
                str(temp_json_path),
                "--db-file",
                str(temp_db_path),
            ],
        ):
            spec = importlib.util.spec_from_file_location(
                "import_consensu_data", import_db_path
            )
            if spec is None or spec.loader is None:
                pytest.skip(
                    f"Could not load import_consensu_data module from {import_db_path}"
                )
            import_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(import_module)

            # Should return error code 4 for missing required field
            result = import_module.main()
            assert result == 4

            # Capture the output to verify detailed error reporting
            captured = capsys.readouterr()
            output = captured.out

            # Should contain detailed error information
            assert "ERROR: Missing required field in JSON data" in output
            assert "Missing field: 'lastUpdated'" in output
            assert "Please verify the JSON contains all required TCF fields" in output

    # Category 4: Data Consistency Tests

    def test_vendor_ids_remain_consistent_across_updates(
        self, temp_db_path, temp_json_path
    ):
        """Test that vendor IDs remain consistent across database updates.

        Business Requirement: Maintain referential integrity for dependent systems
        Important: Vendor IDs are primary keys referenced by other WCT components
        """
        # Setup database and perform initial import
        initial_data = self._setup_vendor_consistency_test_data()
        self._perform_vendor_import_and_get_results(
            temp_db_path, temp_json_path, initial_data
        )

        # Perform update import with modifications
        updated_data = self._create_updated_vendor_data(initial_data)
        self._perform_vendor_import_and_get_results(
            temp_db_path, temp_json_path, updated_data
        )

        # Verify vendor ID consistency
        self._verify_vendor_id_consistency(temp_db_path)

    def _setup_vendor_consistency_test_data(self):
        """Setup initial test data for vendor consistency testing."""
        return {
            "gvlSpecificationVersion": 3,
            "vendorListVersion": 100,
            "tcfPolicyVersion": 5,
            "lastUpdated": "2025-09-04T16:00:24Z",
            "purposes": {
                "1": {
                    "name": "Purpose 1",
                    "description": "Description 1",
                    "illustrations": [],
                }
            },
            "specialPurposes": {},
            "features": {},
            "specialFeatures": {},
            "dataCategories": {},
            "stacks": {},
            "vendors": {
                "123": {
                    "name": "Vendor 123",
                    "usesCookies": True,
                    "cookieRefresh": False,
                    "usesNonCookieAccess": False,
                    "purposes": [1],
                },
                "456": {
                    "name": "Vendor 456",
                    "usesCookies": False,
                    "cookieRefresh": False,
                    "usesNonCookieAccess": True,
                    "purposes": [1],
                },
                "789": {
                    "name": "Vendor 789",
                    "usesCookies": True,
                    "cookieRefresh": True,
                    "usesNonCookieAccess": False,
                    "purposes": [1],
                },
            },
        }

    def _perform_vendor_import_and_get_results(
        self, temp_db_path, temp_json_path, data
    ):
        """Perform vendor import and return vendor results."""
        # Always ensure database exists with proper schema
        create_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )

        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", create_db_path
        )
        if spec is None or spec.loader is None:
            pytest.skip(
                f"Could not load create_consensu_db module from {create_db_path}"
            )
        create_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_db_module)

        # Ensure database has proper schema
        db_needs_creation = True
        if temp_db_path.exists():
            # Check if database has proper schema by trying to query metadata table
            try:
                conn = sqlite3.connect(temp_db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='metadata'"
                )
                has_metadata_table = cursor.fetchone()[0] > 0
                conn.close()
                if has_metadata_table:
                    db_needs_creation = False
            except sqlite3.Error:
                # Database exists but is corrupted, recreate it
                temp_db_path.unlink()

        if db_needs_creation:
            creator = create_db_module.ConsensuDbCreator(temp_db_path)
            creator.create_database()

        # Import data
        with open(temp_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        import_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "import_consensu_data.py"
        )

        with patch(
            "sys.argv",
            [
                "import_consensu_data.py",
                "--json-file",
                str(temp_json_path),
                "--db-file",
                str(temp_db_path),
            ],
        ):
            spec = importlib.util.spec_from_file_location(
                "import_consensu_data", import_db_path
            )
            if spec is None or spec.loader is None:
                pytest.skip(
                    f"Could not load import_consensu_data module from {import_db_path}"
                )
            import_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(import_module)

            result = import_module.main()
            assert result == 0

        # Get vendor results
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM vendors ORDER BY id")
        vendors = cursor.fetchall()
        conn.close()

        return vendors

    def _create_updated_vendor_data(self, initial_data):
        """Create updated vendor data with modifications."""
        updated_data = initial_data.copy()
        updated_data["vendorListVersion"] = 101
        updated_data["vendors"]["123"]["name"] = "Updated Vendor 123"
        updated_data["vendors"]["456"]["usesCookies"] = True  # Changed setting
        # Note: Vendor 789 removed, new vendor 999 added
        del updated_data["vendors"]["789"]
        updated_data["vendors"]["999"] = {
            "name": "New Vendor 999",
            "usesCookies": True,
            "cookieRefresh": False,
            "usesNonCookieAccess": True,
            "purposes": [1],
        }
        return updated_data

    def _verify_vendor_id_consistency(self, temp_db_path):
        """Verify vendor ID consistency after updates."""
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM vendors ORDER BY id")
        updated_vendors = cursor.fetchall()
        conn.close()

        updated_ids = {vendor[0] for vendor in updated_vendors}

        # Vendor 123 and 456 should still exist with same IDs
        assert 123 in updated_ids, "Vendor ID 123 should be preserved across updates"
        assert 456 in updated_ids, "Vendor ID 456 should be preserved across updates"

        # Vendor 789 should be removed (this tests proper cleanup)
        assert 789 not in updated_ids, (
            "Vendor ID 789 should be removed when not in updated data"
        )

        # New vendor 999 should be added with correct ID
        assert 999 in updated_ids, "New vendor ID 999 should be added"

        # Verify the names were updated correctly for existing vendors
        updated_vendor_dict = {vendor[0]: vendor[1] for vendor in updated_vendors}
        assert updated_vendor_dict[123] == "Updated Vendor 123", (
            "Vendor 123 name should be updated"
        )
        assert updated_vendor_dict[456] == "Vendor 456", (
            "Vendor 456 name should remain unchanged"
        )
        assert updated_vendor_dict[999] == "New Vendor 999", (
            "New vendor 999 should have correct name"
        )

    def test_foreign_key_relationships_validated_during_import(
        self, temp_db_path, temp_json_path
    ):
        """Test that foreign key relationships are validated during import.

        Business Requirement: Ensure relational integrity of normalized schema
        Important: 8 junction tables depend on proper foreign key validation
        """
        # Create database first
        create_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "create_consensu_db.py"
        )

        spec = importlib.util.spec_from_file_location(
            "create_consensu_db", create_db_path
        )
        if spec is None or spec.loader is None:
            pytest.skip(
                f"Could not load create_consensu_db module from {create_db_path}"
            )
        create_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_db_module)

        creator = create_db_module.ConsensuDbCreator(temp_db_path)
        creator.create_database()

        # Create JSON data with foreign key constraint violations
        # Vendor references purpose ID that doesn't exist
        invalid_fk_data = {
            "gvlSpecificationVersion": 3,
            "vendorListVersion": 123,
            "tcfPolicyVersion": 5,
            "lastUpdated": "2025-09-04T16:00:24Z",
            "purposes": {
                "1": {
                    "name": "Purpose 1",
                    "description": "Description 1",
                    "illustrations": [],
                }
            },
            "specialPurposes": {},
            "features": {},
            "specialFeatures": {},
            "dataCategories": {},
            "stacks": {},
            "vendors": {
                "100": {
                    "name": "Test Vendor",
                    "usesCookies": True,
                    "cookieRefresh": False,
                    "usesNonCookieAccess": False,
                    "purposes": [1, 999],  # Purpose ID 999 doesn't exist - FK violation
                    "legIntPurposes": [],
                    "flexiblePurposes": [],
                    "specialPurposes": [],
                    "features": [],
                    "specialFeatures": [],
                    "dataDeclaration": [],
                }
            },
        }

        with open(temp_json_path, "w", encoding="utf-8") as f:
            json.dump(invalid_fk_data, f)

        # Import the data and expect foreign key constraint violation
        import_db_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "waivern_community"
            / "analysers"
            / "data_export_analyser"
            / "vendor-database"
            / "import_consensu_data.py"
        )

        with patch(
            "sys.argv",
            [
                "import_consensu_data.py",
                "--json-file",
                str(temp_json_path),
                "--db-file",
                str(temp_db_path),
            ],
        ):
            spec = importlib.util.spec_from_file_location(
                "import_consensu_data", import_db_path
            )
            if spec is None or spec.loader is None:
                pytest.skip(
                    f"Could not load import_consensu_data module from {import_db_path}"
                )
            import_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(import_module)

            # Should return error code 5 for constraint violation
            result = import_module.main()
            assert result == 5, (
                "Import should fail with exit code 5 for foreign key constraint violations"
            )

        # Verify that the database remains in a consistent state (no partial data)
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Should have no data imported due to complete transaction rollback
        cursor.execute("SELECT COUNT(*) FROM vendors")
        vendor_count = cursor.fetchone()[0]
        assert vendor_count == 0, (
            "No vendors should be imported when foreign key constraints fail"
        )

        cursor.execute("SELECT COUNT(*) FROM purposes")
        purpose_count = cursor.fetchone()[0]
        assert purpose_count == 0, (
            "No purposes should be imported when transaction rollback occurs"
        )

        cursor.execute("SELECT COUNT(*) FROM metadata")
        metadata_count = cursor.fetchone()[0]
        assert metadata_count == 0, (
            "No metadata should be imported when transaction rollback occurs"
        )

        conn.close()
