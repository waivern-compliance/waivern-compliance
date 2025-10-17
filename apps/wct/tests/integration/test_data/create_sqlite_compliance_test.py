#!/usr/bin/env python3
"""Create SQLite compliance test database with comprehensive personal data."""

import sqlite3
from pathlib import Path


def create_compliance_test_database():
    """Create SQLite database with comprehensive compliance test data."""

    # Create the test data directory if it doesn't exist
    db_path = Path(__file__).parent / "sqlite_compliance_test.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database to start fresh
    if db_path.exists():
        db_path.unlink()

    # Connect to SQLite database (creates file)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Create customers table
        cursor.execute("""
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone_number TEXT,
                date_of_birth DATE,
                address_line1 TEXT,
                address_line2 TEXT,
                city TEXT,
                postal_code TEXT,
                country TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                gdpr_consent BOOLEAN DEFAULT FALSE,
                marketing_consent BOOLEAN DEFAULT FALSE
            )
        """)

        # Create orders table
        cursor.execute("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_amount DECIMAL(10,2),
                payment_method TEXT,
                card_last_four TEXT,
                billing_address TEXT,
                shipping_address TEXT,
                order_status TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
        """)

        # Create employees table
        cursor.execute("""
            CREATE TABLE employees (
                employee_id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone_number TEXT,
                hire_date DATE,
                department TEXT,
                salary DECIMAL(10,2),
                manager_id INTEGER,
                emergency_contact_name TEXT,
                emergency_contact_phone TEXT,
                national_id TEXT,
                FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
            )
        """)

        # Create support_tickets table
        cursor.execute("""
            CREATE TABLE support_tickets (
                ticket_id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                customer_email TEXT,
                subject TEXT,
                description TEXT,
                priority TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_to INTEGER,
                resolution_notes TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (assigned_to) REFERENCES employees(employee_id)
            )
        """)

        # Insert customer data with international formats
        customers_data = [
            # UK customers
            (
                1,
                "Sarah",
                "Johnson",
                "sarah.johnson@example.co.uk",
                "+44 20 7946 0958",
                "1985-03-15",
                "123 Baker Street",
                "Flat 2A",
                "London",
                "NW1 6XE",
                "United Kingdom",
                True,
                False,
            ),
            (
                2,
                "James",
                "Wilson",
                "j.wilson@gmail.com",
                "+44 161 496 0142",
                "1992-07-22",
                "45 Oxford Road",
                "",
                "Manchester",
                "M1 5QA",
                "United Kingdom",
                True,
                True,
            ),
            (
                3,
                "Emma",
                "Thompson",
                "emma.thompson@hotmail.co.uk",
                "07700 900123",
                "1978-11-08",
                "78 High Street",
                "Suite 5",
                "Edinburgh",
                "EH1 1TH",
                "Scotland",
                False,
                False,
            ),
            # US customers
            (
                4,
                "Michael",
                "Brown",
                "mbrown@company.com",
                "+1-555-0123",
                "1988-05-12",
                "1234 Main Street",
                "Apt 5B",
                "New York",
                "10001",
                "United States",
                True,
                True,
            ),
            (
                5,
                "Jennifer",
                "Davis",
                "jennifer.davis@email.com",
                "(555) 123-4567",
                "1995-09-30",
                "5678 Oak Avenue",
                "",
                "Los Angeles",
                "90210",
                "United States",
                True,
                False,
            ),
            # EU customers with special characters
            (
                6,
                "José María",
                "García",
                "jose.garcia@correo.es",
                "+34 91 123 4567",
                "1983-12-25",
                "Calle de Alcalá 123",
                "2º B",
                "Madrid",
                "28009",
                "Spain",
                True,
                True,
            ),
            (
                7,
                "François",
                "Dupont",
                "f.dupont@example.fr",
                "+33 1 42 34 56 78",
                "1990-02-14",
                "15 Rue de la Paix",
                "",
                "Paris",
                "75001",
                "France",
                False,
                True,
            ),
            (
                8,
                "Müller",
                "Schmidt",
                "mueller.schmidt@test.de",
                "+49 30 12345678",
                "1987-06-18",
                "Unter den Linden 1",
                "Wohnung 3",
                "Berlin",
                "10117",
                "Germany",
                True,
                False,
            ),
            # Other international formats
            (
                9,
                "Hiroshi",
                "Tanaka",
                "h.tanaka@example.jp",
                "+81-3-1234-5678",
                "1991-04-03",
                "1-1-1 Shibuya",
                "Room 401",
                "Tokyo",
                "150-0002",
                "Japan",
                True,
                True,
            ),
            (
                10,
                "Raj",
                "Patel",
                "raj.patel@email.in",
                "+91 98765 43210",
                "1986-08-27",
                "MG Road 456",
                "Flat 2C",
                "Mumbai",
                "400001",
                "India",
                False,
                False,
            ),
            # Edge cases with complex names
            (
                11,
                "Mary-Jane",
                "O'Connor",
                "maryjane.oconnor@test.ie",
                "+353 1 234 5678",
                "1994-01-16",
                "St. Patrick's Square 7",
                "",
                "Dublin",
                "D02 XY45",
                "Ireland",
                True,
                True,
            ),
            (
                12,
                "Van der Berg",
                "Johannes",
                "j.vandenberg@example.nl",
                "+31 20 123 4567",
                "1989-10-11",
                "Prinsengracht 123",
                "2e verdieping",
                "Amsterdam",
                "1015 DX",
                "Netherlands",
                True,
                False,
            ),
            # Test customers for false positive prevention
            (
                13,
                "Test",
                "User",
                "test.user@localhost",
                "555-TEST",
                "2000-01-01",
                "Test Address 1",
                "",
                "Test City",
                "00000",
                "Test Country",
                False,
                False,
            ),
            (
                14,
                "Example",
                "Customer",
                "example@example.com",
                "000-000-0000",
                "1900-01-01",
                "Example Street",
                "",
                "Example Town",
                "EX123",
                "Example Land",
                False,
                False,
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO customers (customer_id, first_name, last_name, email, phone_number, date_of_birth,
                                 address_line1, address_line2, city, postal_code, country, gdpr_consent, marketing_consent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            customers_data,
        )

        # Insert employee data
        employees_data = [
            (
                1,
                "Alice",
                "Smith",
                "alice.smith@company.co.uk",
                "+44 20 7123 4567",
                "2020-01-15",
                "Engineering",
                75000.00,
                None,
                "Bob Smith",
                "+44 7700 900456",
                "NI123456C",
            ),
            (
                2,
                "David",
                "Jones",
                "david.jones@company.co.uk",
                "+44 161 234 5678",
                "2019-03-22",
                "Sales",
                65000.00,
                1,
                "Sarah Jones",
                "+44 7700 900789",
                "NI789123D",
            ),
            (
                3,
                "Lisa",
                "Chen",
                "lisa.chen@company.co.uk",
                "+44 20 7987 6543",
                "2021-06-10",
                "Customer Support",
                45000.00,
                1,
                "Peter Chen",
                "+44 7700 900321",
                "NI456789E",
            ),
            (
                4,
                "Mohammed",
                "Ali",
                "mohammed.ali@company.co.uk",
                "+44 121 345 6789",
                "2018-11-05",
                "Finance",
                55000.00,
                1,
                "Fatima Ali",
                "+44 7700 900654",
                "NI321654F",
            ),
            (
                5,
                "Admin",
                "User",
                "admin@localhost",
                "000-000-0000",
                "2000-01-01",
                "IT",
                1.00,
                None,
                "System Admin",
                "000-000-0000",
                "ADMIN123",
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO employees (employee_id, first_name, last_name, email, phone_number, hire_date,
                                 department, salary, manager_id, emergency_contact_name, emergency_contact_phone, national_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            employees_data,
        )

        # Insert order data
        orders_data = [
            (
                1,
                1,
                "2024-01-15 10:30:00",
                149.99,
                "Credit Card",
                "4567",
                "123 Baker Street, London NW1 6XE",
                "123 Baker Street, London NW1 6XE",
                "Completed",
            ),
            (
                2,
                2,
                "2024-01-16 14:22:00",
                299.50,
                "PayPal",
                "",
                "45 Oxford Road, Manchester M1 5QA",
                "45 Oxford Road, Manchester M1 5QA",
                "Shipped",
            ),
            (
                3,
                4,
                "2024-01-17 09:15:00",
                79.99,
                "Credit Card",
                "1234",
                "1234 Main Street, New York 10001",
                "1234 Main Street, New York 10001",
                "Processing",
            ),
            (
                4,
                6,
                "2024-01-18 16:45:00",
                199.99,
                "Bank Transfer",
                "",
                "Calle de Alcalá 123, Madrid 28009",
                "Calle de Alcalá 123, Madrid 28009",
                "Completed",
            ),
            (
                5,
                9,
                "2024-01-19 11:30:00",
                449.99,
                "Credit Card",
                "9876",
                "1-1-1 Shibuya, Tokyo 150-0002",
                "1-1-1 Shibuya, Tokyo 150-0002",
                "Delivered",
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO orders (order_id, customer_id, order_date, total_amount, payment_method, card_last_four,
                              billing_address, shipping_address, order_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            orders_data,
        )

        # Insert support ticket data
        support_tickets_data = [
            (
                1,
                1,
                "sarah.johnson@example.co.uk",
                "Order delivery issue",
                "My order #1 has not arrived yet. Can you please check the delivery status?",
                "Medium",
                "Open",
                "2024-01-20 09:30:00",
                3,
                "",
            ),
            (
                2,
                2,
                "j.wilson@gmail.com",
                "Account access problem",
                "I cannot log into my account. Please help me reset my password.",
                "High",
                "In Progress",
                "2024-01-21 13:45:00",
                3,
                "Password reset email sent to j.wilson@gmail.com",
            ),
            (
                3,
                None,
                "unknown.customer@test.com",
                "General inquiry",
                "What are your return policies?",
                "Low",
                "Resolved",
                "2024-01-22 10:15:00",
                3,
                "Return policy information provided via email",
            ),
            (
                4,
                4,
                "mbrown@company.com",
                "Billing question",
                "I was charged twice for order #3. My credit card ending in 1234 shows duplicate charges.",
                "High",
                "Resolved",
                "2024-01-23 08:20:00",
                4,
                "Duplicate charge refunded to card ending 1234",
            ),
            (
                5,
                6,
                "jose.garcia@correo.es",
                "Product defect",
                "The product I received from order #4 has a manufacturing defect. Phone: +34 91 123 4567",
                "Medium",
                "Open",
                "2024-01-24 15:30:00",
                3,
                "",
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO support_tickets (ticket_id, customer_id, customer_email, subject, description, priority,
                                       status, created_at, assigned_to, resolution_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            support_tickets_data,
        )

        # Commit all changes
        conn.commit()

        print(f"✅ SQLite compliance test database created successfully at: {db_path}")
        print("📊 Database contains:")
        print(f"   - {len(customers_data)} customers with international formats")
        print(f"   - {len(employees_data)} employees with sensitive HR data")
        print(f"   - {len(orders_data)} orders with payment information")
        print(
            f"   - {len(support_tickets_data)} support tickets with customer communications"
        )
        print("   - Total estimated personal data instances: ~150+")

        return str(db_path)

    except Exception as e:
        print(f"❌ Error creating database: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    create_compliance_test_database()
