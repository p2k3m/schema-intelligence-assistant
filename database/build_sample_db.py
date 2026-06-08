"""Build a local SQLite database with synthetic onboarding data."""

from __future__ import annotations

import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path(__file__).with_name("sample_customer.db")


def build_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    path = Path(db_path)
    if path.exists():
        path.unlink()

    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                email_address TEXT NOT NULL,
                mobile_phone TEXT,
                date_of_birth DATE,
                shipping_address TEXT,
                cust_acct_no TEXT,
                account_status TEXT NOT NULL
            );

            CREATE TABLE payments (
                payment_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                credit_card_number TEXT,
                billing_account_number TEXT,
                card_type TEXT,
                transaction_id INTEGER NOT NULL,
                order_total REAL NOT NULL
            );

            CREATE TABLE audit_log (
                event_id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                last_login_ip TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE applicants (
                applicant_id INTEGER PRIMARY KEY,
                national_insurance_number TEXT,
                passport_number TEXT,
                ref_code TEXT
            );
            """
        )
        connection.executemany(
            """
            INSERT INTO customers (
                full_name, email_address, mobile_phone, date_of_birth,
                shipping_address, cust_acct_no, account_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "Jane Doe",
                    "jane.doe@example.com",
                    "+1 415-555-0199",
                    "1980-04-02",
                    "123 Main Street",
                    "ACC-98765",
                    "ACTIVE",
                ),
                (
                    "Arun Mehta",
                    "arun.mehta@example.in",
                    "+91 98765 43210",
                    "1975-11-30",
                    "44 Market Road",
                    "****1234",
                    "SUSPENDED",
                ),
            ],
        )
        connection.executemany(
            """
            INSERT INTO payments (
                customer_id, credit_card_number, billing_account_number,
                card_type, transaction_id, order_total
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "4111 1111 1111 1111", "ACC-11111", "VISA", 100001, 42.50),
                (2, "5555-5555-5555-4444", "ACC-22222", "MASTERCARD", 100002, 109.99),
            ],
        )
        connection.executemany(
            """
            INSERT INTO audit_log (
                customer_id, last_login_ip, error_message, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            [
                (1, "192.168.1.22", "Login succeeded", "2026-05-27T10:00:00Z"),
                (2, "2001:db8::1", "Invalid request state", "2026-05-28T11:00:00Z"),
            ],
        )
        connection.executemany(
            """
            INSERT INTO applicants (
                national_insurance_number, passport_number, ref_code
            ) VALUES (?, ?, ?)
            """,
            [
                ("QQ123456C", "A1234567", "C-2024-001"),
                ("AB123456D", "B7654321", "C-2024-002"),
            ],
        )

    return path


if __name__ == "__main__":
    print(build_database())

