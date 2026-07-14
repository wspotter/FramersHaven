from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "studio.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _add_column_if_missing(cur: sqlite3.Cursor, table: str, column: str, ddl: str) -> None:
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS catalog_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            cost REAL NOT NULL,
            vendor TEXT,
            width_in REAL,
            height_in REAL,
            rabbet_in REAL,
            preview_filename TEXT,
            metadata_json TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            width_in REAL,
            height_in REAL,
            ratio_label TEXT,
            crop_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_contact TEXT,
            customer_email TEXT,
            status TEXT NOT NULL DEFAULT 'quote',
            approved_at TEXT,
            completed_at TEXT,
            invoiced_at TEXT,
            payload_json TEXT NOT NULL,
            subtotal REAL NOT NULL,
            tax REAL NOT NULL,
            total REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS order_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT,
            customer_email TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS service_options (
            key TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            cost REAL NOT NULL DEFAULT 0,
            markup REAL NOT NULL DEFAULT 1,
            basis TEXT NOT NULL DEFAULT 'count',
            active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS printing_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            unit_price REAL NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    _add_column_if_missing(cur, "images", "ratio_label", "ratio_label TEXT")
    _add_column_if_missing(cur, "images", "crop_json", "crop_json TEXT")
    _add_column_if_missing(cur, "orders", "updated_at", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    _add_column_if_missing(cur, "orders", "customer_email", "customer_email TEXT")
    _add_column_if_missing(cur, "orders", "approved_at", "approved_at TEXT")
    _add_column_if_missing(cur, "orders", "completed_at", "completed_at TEXT")
    _add_column_if_missing(cur, "orders", "invoiced_at", "invoiced_at TEXT")
    _add_column_if_missing(cur, "catalog_items", "created_at", "created_at TEXT DEFAULT CURRENT_TIMESTAMP")
    _add_column_if_missing(cur, "catalog_items", "vendor", "vendor TEXT")
    _add_column_if_missing(cur, "catalog_items", "height_in", "height_in REAL")
    _add_column_if_missing(cur, "catalog_items", "rabbet_in", "rabbet_in REAL")
    _add_column_if_missing(cur, "catalog_items", "preview_filename", "preview_filename TEXT")
    _add_column_if_missing(cur, "catalog_items", "metadata_json", "metadata_json TEXT")
    _add_column_if_missing(cur, "customers", "contact", "contact TEXT")
    _add_column_if_missing(cur, "customers", "customer_email", "customer_email TEXT")
    _add_column_if_missing(cur, "customers", "notes", "notes TEXT")
    _add_column_if_missing(cur, "customers", "updated_at", "updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    _add_column_if_missing(cur, "service_options", "cost", "cost REAL NOT NULL DEFAULT 0")
    _add_column_if_missing(cur, "service_options", "markup", "markup REAL NOT NULL DEFAULT 1")
    _add_column_if_missing(cur, "service_options", "basis", "basis TEXT NOT NULL DEFAULT 'count'")
    _add_column_if_missing(cur, "service_options", "pricing_method", "pricing_method TEXT NOT NULL DEFAULT 'cost_markup'")
    _add_column_if_missing(cur, "service_options", "price_code", "price_code TEXT")

    defaults = {
        "tax_rate": "0.06",
        "markup_moulding": "2.4",
        "markup_mat": "2.1",
        "markup_glazing": "1.9",
        "markup_addons": "1.85",
    }
    for key, value in defaults.items():
        cur.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO NOTHING
            """,
            (key, value),
        )

    service_defaults = [
        ("glazing_reg_glass", "Reg glass", 0.0, 1.0, "square_inches", 1, 5),
        ("glazing_anti_reflection_glass", "Anti-reflection glass", 0.0, 1.0, "square_inches", 1, 6),
        ("glazing_acrylic", "Acrylic", 0.0, 1.0, "square_inches", 1, 7),
        ("glazing_anti_reflection_acrylic", "Anti reflection acrylic", 0.0, 1.0, "square_inches", 1, 8),
        ("backing", "Foamboard", 0.0, 1.0, "square_inches", 1, 10),
        ("mounting", "Subject Mounting", 0.0, 1.0, "count", 1, 20),
        ("frame_mounting", "Frame Mounting", 0.0, 1.0, "count", 1, 30),
        ("printing", "Printing", 0.0, 1.0, "count", 1, 40),
        ("various", "Various", 0.0, 1.0, "count", 1, 50),
        ("assembly", "Assembly", 0.0, 1.0, "count", 1, 60),
        ("royalties", "Royalties", 0.0, 1.0, "count", 1, 70),
        ("custom_1", "Custom Service 1", 0.0, 1.0, "count", 0, 80),
        ("custom_2", "Custom Service 2", 0.0, 1.0, "count", 0, 90),
    ]
    for row in service_defaults:
        cur.execute(
            """
            INSERT INTO service_options (key, label, price, cost, markup, basis, active, sort_order)
            VALUES (?, ?, 0, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO NOTHING
            """,
            row,
        )
    cur.execute("UPDATE service_options SET cost = price WHERE cost = 0 AND price != 0")
    cur.execute("UPDATE service_options SET markup = 1 WHERE markup <= 0")
    cur.execute("UPDATE service_options SET basis = 'square_inches', label = 'Foamboard' WHERE key = 'backing' AND label = 'Backing'")

    conn.commit()
    conn.close()
