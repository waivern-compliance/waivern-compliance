#!/usr/bin/env python3
"""Import Consensu.org TCF Global Vendor List JSON data into SQLite database.

This script reads the JSON vendor list file and imports all data
into the normalized SQLite database schema.
"""

import argparse
import json
import sqlite3
import sys
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

    def import_data(self) -> None:
        """Load JSON data and import into database."""
        print(f"Loading JSON data from {self.json_path}")
        with open(self.json_path, encoding="utf-8") as f:
            self.data = json.load(f)

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
        """Import GVL metadata."""
        print("Importing metadata...")
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

        # Import purposes
        for purpose_id, purpose_data in self.data.get("purposes", {}).items():
            self.conn.execute(
                """
                INSERT INTO purposes (id, name, description, illustrations)
                VALUES (?, ?, ?, ?)
            """,
                (
                    int(purpose_id),
                    purpose_data["name"],
                    purpose_data["description"],
                    json.dumps(purpose_data.get("illustrations", [])),
                ),
            )

        # Import special purposes
        for sp_id, sp_data in self.data.get("specialPurposes", {}).items():
            self.conn.execute(
                """
                INSERT INTO special_purposes (id, name, description, illustrations)
                VALUES (?, ?, ?, ?)
            """,
                (
                    int(sp_id),
                    sp_data["name"],
                    sp_data["description"],
                    json.dumps(sp_data.get("illustrations", [])),
                ),
            )

        # Import features
        for feature_id, feature_data in self.data.get("features", {}).items():
            self.conn.execute(
                """
                INSERT INTO features (id, name, description, illustrations)
                VALUES (?, ?, ?, ?)
            """,
                (
                    int(feature_id),
                    feature_data["name"],
                    feature_data["description"],
                    json.dumps(feature_data.get("illustrations", [])),
                ),
            )

        # Import special features
        for sf_id, sf_data in self.data.get("specialFeatures", {}).items():
            self.conn.execute(
                """
                INSERT INTO special_features (id, name, description, illustrations)
                VALUES (?, ?, ?, ?)
            """,
                (
                    int(sf_id),
                    sf_data["name"],
                    sf_data["description"],
                    json.dumps(sf_data.get("illustrations", [])),
                ),
            )

        # Import data categories
        for dc_id, dc_data in self.data.get("dataCategories", {}).items():
            self.conn.execute(
                """
                INSERT INTO data_categories (id, name, description)
                VALUES (?, ?, ?)
            """,
                (int(dc_id), dc_data["name"], dc_data["description"]),
            )

        # Import stacks
        for stack_id, stack_data in self.data.get("stacks", {}).items():
            self.conn.execute(
                """
                INSERT INTO stacks (id, name, description)
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

        for vendor_id, vendor_data in self.data.get("vendors", {}).items():
            # Insert main vendor record
            self.conn.execute(
                """
                INSERT INTO vendors (
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

            # Import vendor URLs
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

            # Import data retention
            retention_data = vendor_data.get("dataRetention", {})
            if retention_data:
                self.conn.execute(
                    """
                    INSERT INTO vendor_data_retention (
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
        """Import vendor relationship data (purposes, features, etc.)."""
        print("Importing vendor relationships...")

        for vendor_id, vendor_data in self.data.get("vendors", {}).items():
            vendor_id_int = int(vendor_id)

            # Import purposes
            for purpose_id in vendor_data.get("purposes", []):
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO vendor_purposes (vendor_id, purpose_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, purpose_id),
                )

            # Import legitimate interest purposes
            for purpose_id in vendor_data.get("legIntPurposes", []):
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO vendor_leg_int_purposes (vendor_id, purpose_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, purpose_id),
                )

            # Import flexible purposes
            for purpose_id in vendor_data.get("flexiblePurposes", []):
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO vendor_flexible_purposes (vendor_id, purpose_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, purpose_id),
                )

            # Import special purposes
            for sp_id in vendor_data.get("specialPurposes", []):
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO vendor_special_purposes (vendor_id, special_purpose_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, sp_id),
                )

            # Import features
            for feature_id in vendor_data.get("features", []):
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO vendor_features (vendor_id, feature_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, feature_id),
                )

            # Import special features
            for sf_id in vendor_data.get("specialFeatures", []):
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO vendor_special_features (vendor_id, special_feature_id)
                    VALUES (?, ?)
                """,
                    (vendor_id_int, sf_id),
                )

            # Import data declarations
            for dc_id in vendor_data.get("dataDeclaration", []):
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO vendor_data_declarations (vendor_id, data_category_id)
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

    # Run import
    importer = ConsensuDataImporter(args.db_file, args.json_file)
    importer.import_data()

    return 0


if __name__ == "__main__":
    sys.exit(main())
