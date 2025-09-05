#!/usr/bin/env python3
"""Import Consensu.org TCF Global Vendor List JSON data into SQLite database.

This script reads the JSON vendor list file and imports all data
into the normalized SQLite database schema.
"""

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class ConsensuDataImporter:
    """Imports Consensu.org vendor list JSON data into SQLite database."""

    def __init__(self, db_path: Path, json_path: Path) -> None:
        """Initialize with database and JSON file paths."""
        self.db_path = db_path
        self.json_path = json_path
        self.conn: sqlite3.Connection
        self.data: dict[str, Any] = {}

    def _create_backup(self) -> None:
        """Create timestamped backup of existing database before import."""
        if not self.db_path.exists():
            return  # No existing database to backup

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.db_path.with_suffix(
            f"{self.db_path.suffix}.backup.{timestamp}"
        )

        try:
            shutil.copy2(self.db_path, backup_path)
            print(f"Created backup: {backup_path}")
        except Exception as e:
            raise Exception(f"Failed to create backup: {e}") from e

    def import_data(self) -> None:
        """Load JSON data and import into database."""
        print(f"Loading JSON data from {self.json_path}")
        with open(self.json_path, encoding="utf-8") as f:
            self.data = json.load(f)

        # Create backup before connecting to database
        self._create_backup()

        print(f"Connecting to database {self.db_path}")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")

        try:
            self._import_metadata()
            self._import_reference_data()
            self._import_vendors()
            self._import_vendor_relationships()

            self.conn.commit()
            print("Data import completed successfully")
            self._print_statistics()

        except Exception as e:
            print(f"Error during import: {e}")
            self.conn.rollback()
            raise e
        finally:
            if self.conn:
                self.conn.close()

    def _import_metadata(self) -> None:
        """Import GVL metadata (supports incremental updates)."""
        print("Importing metadata...")
        # Clear existing metadata and insert new (metadata is singular)
        self.conn.execute("DELETE FROM metadata")
        self.conn.execute(
            """
            INSERT INTO metadata (
                gvl_specification_version,
                vendor_list_version,
                tcf_policy_version,
                last_updated
            ) VALUES (?, ?, ?, ?)
        """,
            (
                self.data["gvlSpecificationVersion"],
                self.data["vendorListVersion"],
                self.data["tcfPolicyVersion"],
                self.data["lastUpdated"],
            ),
        )

    def _import_reference_data(self) -> None:
        """Import all reference tables (purposes, features, etc.)."""
        print("Importing reference data...")

        # Import purposes (use INSERT OR REPLACE for incremental updates)
        for purpose_id, purpose_data in self.data.get("purposes", {}).items():
            self.conn.execute(
                """
                INSERT OR REPLACE INTO purposes (id, name, description, illustrations)
                VALUES (?, ?, ?, ?)
            """,
                (
                    int(purpose_id),
                    purpose_data["name"],
                    purpose_data["description"],
                    json.dumps(purpose_data.get("illustrations", [])),
                ),
            )

        # Import special purposes (use INSERT OR REPLACE for incremental updates)
        for sp_id, sp_data in self.data.get("specialPurposes", {}).items():
            self.conn.execute(
                """
                INSERT OR REPLACE INTO special_purposes (id, name, description, illustrations)
                VALUES (?, ?, ?, ?)
            """,
                (
                    int(sp_id),
                    sp_data["name"],
                    sp_data["description"],
                    json.dumps(sp_data.get("illustrations", [])),
                ),
            )

        # Import features (use INSERT OR REPLACE for incremental updates)
        for feature_id, feature_data in self.data.get("features", {}).items():
            self.conn.execute(
                """
                INSERT OR REPLACE INTO features (id, name, description, illustrations)
                VALUES (?, ?, ?, ?)
            """,
                (
                    int(feature_id),
                    feature_data["name"],
                    feature_data["description"],
                    json.dumps(feature_data.get("illustrations", [])),
                ),
            )

        # Import special features (use INSERT OR REPLACE for incremental updates)
        for sf_id, sf_data in self.data.get("specialFeatures", {}).items():
            self.conn.execute(
                """
                INSERT OR REPLACE INTO special_features (id, name, description, illustrations)
                VALUES (?, ?, ?, ?)
            """,
                (
                    int(sf_id),
                    sf_data["name"],
                    sf_data["description"],
                    json.dumps(sf_data.get("illustrations", [])),
                ),
            )

        # Import data categories (use INSERT OR REPLACE for incremental updates)
        for dc_id, dc_data in self.data.get("dataCategories", {}).items():
            self.conn.execute(
                """
                INSERT OR REPLACE INTO data_categories (id, name, description)
                VALUES (?, ?, ?)
            """,
                (int(dc_id), dc_data["name"], dc_data["description"]),
            )

        # Import stacks (use INSERT OR REPLACE for incremental updates)
        for stack_id, stack_data in self.data.get("stacks", {}).items():
            self.conn.execute(
                """
                INSERT OR REPLACE INTO stacks (id, name, description)
                VALUES (?, ?, ?)
            """,
                (int(stack_id), stack_data["name"], stack_data["description"]),
            )

            # Import stack relationships
            for purpose_id in stack_data.get("purposes", []):
                self.conn.execute(
                    """
                    INSERT INTO stack_purposes (stack_id, purpose_id)
                    VALUES (?, ?)
                """,
                    (int(stack_id), purpose_id),
                )

            for sf_id in stack_data.get("specialFeatures", []):
                self.conn.execute(
                    """
                    INSERT INTO stack_special_features (stack_id, special_feature_id)
                    VALUES (?, ?)
                """,
                    (int(stack_id), sf_id),
                )

    def _import_vendors(self) -> None:
        """Import vendor data."""
        print(f"Importing {len(self.data.get('vendors', {}))} vendors...")

        # Get current vendor IDs in database
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM vendors")
        existing_vendor_ids = {row[0] for row in cursor.fetchall()}

        # Get new vendor IDs from the data
        new_vendor_ids = {
            int(vendor_id) for vendor_id in self.data.get("vendors", {}).keys()
        }

        # Remove vendors that are no longer in the updated data
        vendors_to_remove = existing_vendor_ids - new_vendor_ids
        for vendor_id in vendors_to_remove:
            print(f"Removing vendor {vendor_id} (not in updated data)")
            self.conn.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))

        for vendor_id, vendor_data in self.data.get("vendors", {}).items():
            # Insert or replace main vendor record (supports incremental updates)
            self.conn.execute(
                """
                INSERT OR REPLACE INTO vendors (
                    id, name, cookie_max_age_seconds, uses_cookies,
                    cookie_refresh, uses_non_cookie_access, device_storage_disclosure_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    int(vendor_id),
                    vendor_data["name"],
                    vendor_data.get("cookieMaxAgeSeconds"),
                    vendor_data.get("usesCookies", False),
                    vendor_data.get("cookieRefresh", False),
                    vendor_data.get("usesNonCookieAccess", False),
                    vendor_data.get("deviceStorageDisclosureUrl"),
                ),
            )

            # Import vendor URLs (delete existing and re-insert for clean incremental update)
            self.conn.execute(
                "DELETE FROM vendor_urls WHERE vendor_id = ?", (int(vendor_id),)
            )
            for url_data in vendor_data.get("urls", []):
                self.conn.execute(
                    """
                    INSERT INTO vendor_urls (
                        vendor_id, lang_id, privacy_url, leg_int_claim_url
                    ) VALUES (?, ?, ?, ?)
                """,
                    (
                        int(vendor_id),
                        url_data.get("langId"),
                        url_data.get("privacy"),
                        url_data.get("legIntClaim"),
                    ),
                )

            # Import data retention (use INSERT OR REPLACE for incremental updates)
            retention_data = vendor_data.get("dataRetention", {})
            if retention_data:
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO vendor_data_retention (
                        vendor_id, std_retention, purposes_retention, special_purposes_retention
                    ) VALUES (?, ?, ?, ?)
                """,
                    (
                        int(vendor_id),
                        retention_data.get("stdRetention"),
                        json.dumps(retention_data.get("purposes", {})),
                        json.dumps(retention_data.get("specialPurposes", {})),
                    ),
                )

    def _import_vendor_relationships(self) -> None:
        """Import vendor relationship data (purposes, features, etc.) with incremental update support."""
        print("Importing vendor relationships...")

        for vendor_id, vendor_data in self.data.get("vendors", {}).items():
            vendor_id_int = int(vendor_id)

            # Clear existing relationships for this vendor to ensure clean incremental update
            self.conn.execute(
                "DELETE FROM vendor_purposes WHERE vendor_id = ?", (vendor_id_int,)
            )
            self.conn.execute(
                "DELETE FROM vendor_leg_int_purposes WHERE vendor_id = ?",
                (vendor_id_int,),
            )
            self.conn.execute(
                "DELETE FROM vendor_flexible_purposes WHERE vendor_id = ?",
                (vendor_id_int,),
            )
            self.conn.execute(
                "DELETE FROM vendor_special_purposes WHERE vendor_id = ?",
                (vendor_id_int,),
            )
            self.conn.execute(
                "DELETE FROM vendor_features WHERE vendor_id = ?", (vendor_id_int,)
            )
            self.conn.execute(
                "DELETE FROM vendor_special_features WHERE vendor_id = ?",
                (vendor_id_int,),
            )
            self.conn.execute(
                "DELETE FROM vendor_data_declarations WHERE vendor_id = ?",
                (vendor_id_int,),
            )

            # Import purposes
            for purpose_id in vendor_data.get("purposes", []):
                self.conn.execute(
                    """
                    INSERT INTO vendor_purposes (vendor_id, purpose_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, purpose_id),
                )

            # Import legitimate interest purposes
            for purpose_id in vendor_data.get("legIntPurposes", []):
                self.conn.execute(
                    """
                    INSERT INTO vendor_leg_int_purposes (vendor_id, purpose_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, purpose_id),
                )

            # Import flexible purposes
            for purpose_id in vendor_data.get("flexiblePurposes", []):
                self.conn.execute(
                    """
                    INSERT INTO vendor_flexible_purposes (vendor_id, purpose_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, purpose_id),
                )

            # Import special purposes
            for sp_id in vendor_data.get("specialPurposes", []):
                self.conn.execute(
                    """
                    INSERT INTO vendor_special_purposes (vendor_id, special_purpose_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, sp_id),
                )

            # Import features
            for feature_id in vendor_data.get("features", []):
                self.conn.execute(
                    """
                    INSERT INTO vendor_features (vendor_id, feature_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, feature_id),
                )

            # Import special features
            for sf_id in vendor_data.get("specialFeatures", []):
                self.conn.execute(
                    """
                    INSERT INTO vendor_special_features (vendor_id, special_feature_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, sf_id),
                )

            # Import data declarations
            for dc_id in vendor_data.get("dataDeclaration", []):
                self.conn.execute(
                    """
                    INSERT INTO vendor_data_declarations (vendor_id, data_category_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, dc_id),
                )

    def _print_statistics(self) -> None:
        """Print import statistics."""
        stats_queries = [
            ("Vendors", "SELECT COUNT(*) FROM vendors"),
            ("Purposes", "SELECT COUNT(*) FROM purposes"),
            ("Special Purposes", "SELECT COUNT(*) FROM special_purposes"),
            ("Features", "SELECT COUNT(*) FROM features"),
            ("Special Features", "SELECT COUNT(*) FROM special_features"),
            ("Data Categories", "SELECT COUNT(*) FROM data_categories"),
            ("Stacks", "SELECT COUNT(*) FROM stacks"),
            ("Vendor URLs", "SELECT COUNT(*) FROM vendor_urls"),
            ("Vendor-Purpose Relations", "SELECT COUNT(*) FROM vendor_purposes"),
            ("Vendor-Feature Relations", "SELECT COUNT(*) FROM vendor_features"),
        ]

        print("\nImport Statistics:")
        print("=" * 40)
        for name, query in stats_queries:
            count = self.conn.execute(query).fetchone()[0]
            print(f"{name:.<30} {count:>8}")


def _handle_import_error(e: Exception, json_file: Path) -> int:
    """Handle import errors and return appropriate exit code."""
    error_handlers = {
        json.JSONDecodeError: (
            2,
            f"ERROR: Invalid JSON format in {json_file}",
            "JSON parsing failed",
            "Please verify the JSON file is properly formatted",
        ),
        ValueError: (
            3,
            "ERROR: Data type validation failed during import",
            "Data type validation failed",
            "Please verify all data types in the JSON match expected schema",
        ),
        KeyError: (
            4,
            "ERROR: Missing required field in JSON data",
            "Missing required field",
            "Please verify the JSON contains all required TCF fields",
        ),
        sqlite3.IntegrityError: (
            5,
            "ERROR: Database constraint violation",
            "Database constraint violation",
            "Data import failed due to referential integrity issues",
        ),
        sqlite3.Error: (
            6,
            "ERROR: Database operation failed",
            "Database operation failed",
            "Check database file permissions and disk space",
        ),
        PermissionError: (
            7,
            "ERROR: File permission denied",
            "File permission denied",
            "Check file and directory permissions",
        ),
        FileNotFoundError: (
            8,
            "ERROR: File access failed",
            "File access failed",
            "Verify file paths are correct and files exist",
        ),
    }

    # Find matching error type
    for error_type, (
        exit_code,
        title,
        _detail_prefix,
        advice,
    ) in error_handlers.items():
        if isinstance(e, error_type):
            print(title)
            if error_type == KeyError:
                print(f"Missing field: {e}")
            else:
                print(f"Details: {e}")
            print(advice)
            return exit_code

    # Default case for unexpected errors
    print("ERROR: Unexpected error during import")
    print(f"Details: {e}")
    print("Please report this issue with the error details above")
    return 9


def main() -> int:
    """Run the import."""
    parser = argparse.ArgumentParser(
        description="Import Consensu.org TCF vendor list data"
    )
    parser.add_argument(
        "--json-file",
        type=Path,
        default=Path(__file__).parent / "consensu.org.v3.vendor-list.json",
        help="Path to Consensu.org JSON file",
    )
    parser.add_argument(
        "--db-file",
        type=Path,
        default=Path(__file__).parent / "consensu_vendors.db",
        help="Path to SQLite database file",
    )

    args = parser.parse_args()

    # Validate files exist
    if not args.json_file.exists():
        print(f"JSON file not found: {args.json_file}")
        return 1

    if not args.db_file.exists():
        print(f"Database file not found: {args.db_file}")
        print("Please create the database first using create_consensu_db.py")
        return 1

    # Run import with comprehensive error handling
    try:
        importer = ConsensuDataImporter(args.db_file, args.json_file)
        importer.import_data()
        return 0
    except Exception as e:
        return _handle_import_error(e, args.json_file)


if __name__ == "__main__":
    sys.exit(main())
