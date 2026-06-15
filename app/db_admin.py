"""Compatibility schema for the optional table-based pricing engine."""
from __future__ import annotations

from app.db import get_connection


def init_admin_tables() -> None:
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS price_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component_type TEXT NOT NULL UNIQUE,
                pricing_method TEXT NOT NULL,
                markup REAL DEFAULT 4.0,
                factor REAL DEFAULT 0.0,
                costing_method TEXT DEFAULT 'square_area',
                min_price REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS price_table_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                price_code TEXT NOT NULL,
                half_perimeter REAL NOT NULL,
                price REAL NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_price_table_code_perimeter
            ON price_table_entries(price_code, half_perimeter);
            """
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_admin_tables()
    print("Pricing tables initialized.")
