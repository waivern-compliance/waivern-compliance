#!/usr/bin/env python3
"""Create SQLite database for Consensu.org TCF Global Vendor List.

This script creates a normalized SQLite database schema to store
TCF (Transparency and Consent Framework) vendor list data from
the Consensu.org v3 JSON format.
"""

import argparse
import sqlite3
from pathlib import Path


class ConsensuDbCreator:
    """Creates and manages Consensu.org vendor list SQLite database."""

    def __init__(self, db_path: Path) -> None:
        """Initialize with database file path."""
        self.db_path = db_path
        self.conn: sqlite3.Connection

    def create_database(self) -> None:
        """Create the complete database schema."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")

        try:
            self._create_metadata_tables()
            self._create_reference_tables()
            self._create_vendor_tables()
            self._create_junction_tables()
            self._create_indexes()
            self.conn.commit()
            print(f"Database created successfully at {self.db_path}")
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            if self.conn:
                self.conn.close()

    def _create_metadata_tables(self) -> None:
        """Create tables for GVL metadata."""
        self.conn.execute("""
            CREATE TABLE metadata (
                id INTEGER PRIMARY KEY,
                gvl_specification_version INTEGER NOT NULL,
                vendor_list_version INTEGER NOT NULL,
                tcf_policy_version INTEGER NOT NULL,
                last_updated TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def _create_reference_tables(self) -> None:
        """Create reference tables for purposes, features, etc."""
        # Purposes table
        self.conn.execute("""
            CREATE TABLE purposes (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                illustrations TEXT  -- JSON array as text
            )
        """)

        # Special purposes table
        self.conn.execute("""
            CREATE TABLE special_purposes (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                illustrations TEXT  -- JSON array as text
            )
        """)

        # Features table
        self.conn.execute("""
            CREATE TABLE features (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                illustrations TEXT  -- JSON array as text
            )
        """)

        # Special features table
        self.conn.execute("""
            CREATE TABLE special_features (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                illustrations TEXT  -- JSON array as text
            )
        """)

        # Data categories table
        self.conn.execute("""
            CREATE TABLE data_categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)

        # Stacks table
        self.conn.execute("""
            CREATE TABLE stacks (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)

    def _create_vendor_tables(self) -> None:
        """Create main vendor tables."""
        # Main vendors table
        self.conn.execute("""
            CREATE TABLE vendors (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                cookie_max_age_seconds INTEGER,
                uses_cookies BOOLEAN NOT NULL,
                cookie_refresh BOOLEAN NOT NULL,
                uses_non_cookie_access BOOLEAN NOT NULL,
                device_storage_disclosure_url TEXT
            )
        """)

        # Vendor URLs table (multi-language support)
        self.conn.execute("""
            CREATE TABLE vendor_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_id INTEGER NOT NULL,
                lang_id TEXT NOT NULL,
                privacy_url TEXT,
                leg_int_claim_url TEXT,
                FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE
            )
        """)

        # Vendor data retention table
        self.conn.execute("""
            CREATE TABLE vendor_data_retention (
                vendor_id INTEGER PRIMARY KEY,
                std_retention INTEGER,  -- Standard retention in days
                purposes_retention TEXT,  -- JSON object for purpose-specific retention
                special_purposes_retention TEXT,  -- JSON object for special purpose retention
                FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE
            )
        """)

    def _create_junction_tables(self) -> None:
        """Create junction tables for many-to-many relationships."""
        # Vendor purposes
        self.conn.execute("""
            CREATE TABLE vendor_purposes (
                vendor_id INTEGER NOT NULL,
                purpose_id INTEGER NOT NULL,
                PRIMARY KEY (vendor_id, purpose_id),
                FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
                FOREIGN KEY (purpose_id) REFERENCES purposes (id) ON DELETE CASCADE
            )
        """)

        # Vendor legitimate interest purposes
        self.conn.execute("""
            CREATE TABLE vendor_leg_int_purposes (
                vendor_id INTEGER NOT NULL,
                purpose_id INTEGER NOT NULL,
                PRIMARY KEY (vendor_id, purpose_id),
                FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
                FOREIGN KEY (purpose_id) REFERENCES purposes (id) ON DELETE CASCADE
            )
        """)

        # Vendor flexible purposes
        self.conn.execute("""
            CREATE TABLE vendor_flexible_purposes (
                vendor_id INTEGER NOT NULL,
                purpose_id INTEGER NOT NULL,
                PRIMARY KEY (vendor_id, purpose_id),
                FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
                FOREIGN KEY (purpose_id) REFERENCES purposes (id) ON DELETE CASCADE
            )
        """)

        # Vendor special purposes
        self.conn.execute("""
            CREATE TABLE vendor_special_purposes (
                vendor_id INTEGER NOT NULL,
                special_purpose_id INTEGER NOT NULL,
                PRIMARY KEY (vendor_id, special_purpose_id),
                FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
                FOREIGN KEY (special_purpose_id) REFERENCES special_purposes (id) ON DELETE CASCADE
            )
        """)

        # Vendor features
        self.conn.execute("""
            CREATE TABLE vendor_features (
                vendor_id INTEGER NOT NULL,
                feature_id INTEGER NOT NULL,
                PRIMARY KEY (vendor_id, feature_id),
                FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
                FOREIGN KEY (feature_id) REFERENCES features (id) ON DELETE CASCADE
            )
        """)

        # Vendor special features
        self.conn.execute("""
            CREATE TABLE vendor_special_features (
                vendor_id INTEGER NOT NULL,
                special_feature_id INTEGER NOT NULL,
                PRIMARY KEY (vendor_id, special_feature_id),
                FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
                FOREIGN KEY (special_feature_id) REFERENCES special_features (id) ON DELETE CASCADE
            )
        """)

        # Vendor data declarations
        self.conn.execute("""
            CREATE TABLE vendor_data_declarations (
                vendor_id INTEGER NOT NULL,
                data_category_id INTEGER NOT NULL,
                PRIMARY KEY (vendor_id, data_category_id),
                FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE,
                FOREIGN KEY (data_category_id) REFERENCES data_categories (id) ON DELETE CASCADE
            )
        """)

        # Stack purposes
        self.conn.execute("""
            CREATE TABLE stack_purposes (
                stack_id INTEGER NOT NULL,
                purpose_id INTEGER NOT NULL,
                PRIMARY KEY (stack_id, purpose_id),
                FOREIGN KEY (stack_id) REFERENCES stacks (id) ON DELETE CASCADE,
                FOREIGN KEY (purpose_id) REFERENCES purposes (id) ON DELETE CASCADE
            )
        """)

        # Stack special features
        self.conn.execute("""
            CREATE TABLE stack_special_features (
                stack_id INTEGER NOT NULL,
                special_feature_id INTEGER NOT NULL,
                PRIMARY KEY (stack_id, special_feature_id),
                FOREIGN KEY (stack_id) REFERENCES stacks (id) ON DELETE CASCADE,
                FOREIGN KEY (special_feature_id) REFERENCES special_features (id) ON DELETE CASCADE
            )
        """)

    def _create_indexes(self) -> None:
        """Create indexes for performance."""
        indexes = [
            "CREATE INDEX idx_vendor_urls_vendor_id ON vendor_urls (vendor_id)",
            "CREATE INDEX idx_vendor_urls_lang_id ON vendor_urls (lang_id)",
            "CREATE INDEX idx_vendor_purposes_vendor_id ON vendor_purposes (vendor_id)",
            "CREATE INDEX idx_vendor_purposes_purpose_id ON vendor_purposes (purpose_id)",
            "CREATE INDEX idx_vendor_features_vendor_id ON vendor_features (vendor_id)",
            "CREATE INDEX idx_vendor_features_feature_id ON vendor_features (feature_id)",
            "CREATE INDEX idx_vendors_name ON vendors (name)",
            "CREATE INDEX idx_vendors_uses_cookies ON vendors (uses_cookies)",
            "CREATE INDEX idx_vendors_uses_non_cookie_access ON vendors (uses_non_cookie_access)",
        ]

        for index_sql in indexes:
            self.conn.execute(index_sql)


def main() -> None:
    """Create the database."""
    parser = argparse.ArgumentParser(
        description="Create Consensu.org TCF vendor list database"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path(__file__).parent / "consensu_vendors.db",
        help="Path to SQLite database file (default: consensu_vendors.db in current directory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreation of database if it already exists",
    )

    args = parser.parse_args()

    if args.db_path.exists() and not args.force:
        print(f"Database {args.db_path} already exists. Use --force to recreate.")
        return

    if args.force and args.db_path.exists():
        args.db_path.unlink()
        print(f"Removed existing database {args.db_path}")

    creator = ConsensuDbCreator(args.db_path)
    creator.create_database()


if __name__ == "__main__":
    main()
