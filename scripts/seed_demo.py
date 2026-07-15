#!/usr/bin/env python3
"""Create a deterministic, fictional FramersHaven demo workspace."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import db
from app.db_admin import init_admin_tables

DEMO_MARKER_KEY = "demo_seed_version"
DEMO_MARKER_VALUE = "1"


def _is_demo_database(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        conn = sqlite3.connect(path)
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (DEMO_MARKER_KEY,)
        ).fetchone()
        conn.close()
        return bool(row and row[0] == DEMO_MARKER_VALUE)
    except sqlite3.Error:
        return False


def _make_demo_art(upload_dir: Path) -> None:
    upload_dir.mkdir(parents=True, exist_ok=True)
    fixtures = [
        ("demo-art-1.png", (1150, 1450), "Quiet Geometry", (35, 91, 104), (241, 184, 98)),
        ("demo-art-2.png", (1400, 1000), "Color Study", (111, 62, 117), (224, 108, 122)),
    ]
    for filename, size, title, background, accent in fixtures:
        image = Image.new("RGB", size, background)
        draw = ImageDraw.Draw(image)
        margin = min(size) // 10
        draw.rounded_rectangle(
            (margin, margin, size[0] - margin, size[1] - margin),
            radius=margin // 3,
            fill=accent,
        )
        draw.ellipse(
            (size[0] * 0.24, size[1] * 0.22, size[0] * 0.76, size[1] * 0.74),
            fill=(244, 236, 219),
        )
        draw.text((margin, size[1] - margin + 8), title, fill=(255, 255, 255))
        image.save(upload_dir / filename, "PNG", optimize=True)


def create_demo_data(db_path: Path, upload_dir: Path, force: bool = False) -> None:
    if db_path.exists() and not force and not _is_demo_database(db_path):
        raise RuntimeError(
            f"Refusing to overwrite non-demo database: {db_path}. Use --force only on a backup or disposable copy."
        )
    db_path.unlink(missing_ok=True)

    db.DB_PATH = db_path
    db.init_db()
    init_admin_tables()
    _make_demo_art(upload_dir)

    conn = db.get_connection()
    try:
        conn.executemany(
            """
            INSERT INTO catalog_items
                (sku, name, category, cost, vendor, width_in, height_in, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("DEMO-M-101", "Graphite Flat", "moulding", 3.25, "Sample Catalog", 1.50, None, '{"color":"#262626"}'),
                ("DEMO-M-102", "Natural Maple", "moulding", 4.10, "Sample Catalog", 1.25, None, '{"color":"#b88b5a"}'),
                ("DEMO-M-103", "Wide Walnut Panel", "moulding", 7.95, "Sample Catalog", 3.00, None, '{"color":"#5b3825"}'),
                ("DEMO-M-104", "Soft Silver Scoop", "moulding", 5.50, "Sample Catalog", 2.00, None, '{"color":"#a7adb2"}'),
                ("DEMO-M-105", "Antique Gold Bevel", "moulding", 5.75, "Sample Catalog", 1.75, None, '{"color":"#b08a42"}'),
                ("DEMO-MAT-1", "Warm White", "mat", 14.00, "Sample Catalog", 32.0, 40.0, '{"color":"#f2eee2","core":"white"}'),
                ("DEMO-MAT-2", "Deep Blue", "mat", 14.00, "Sample Catalog", 32.0, 40.0, '{"color":"#203c55","core":"white"}'),
                ("DEMO-MAT-3", "Soft Blush", "mat", 14.00, "Sample Catalog", 32.0, 40.0, '{"color":"#df9ba7","core":"white"}'),
                ("DEMO-MAT-4", "Gallery Cream", "mat", 14.00, "Sample Catalog", 32.0, 40.0, '{"color":"#ede2c8","core":"white"}'),
                ("DEMO-MAT-5", "Charcoal", "mat", 14.00, "Sample Catalog", 32.0, 40.0, '{"color":"#34373a","core":"white"}'),
                ("DEMO-GLZ-1", "Conservation Clear", "glazing", 2.25, "Sample Catalog", None, None, "{}"),
            ],
        )
        conn.executemany(
            "UPDATE catalog_items SET preview_filename = ? WHERE sku = ?",
            [
                ("mouldings/demo-black-tall-cap.jpg", "DEMO-M-101"),
                ("mouldings/demo-dark-walnut-panel.jpg", "DEMO-M-103"),
                ("mouldings/demo-gold-tall-cap.jpg", "DEMO-M-105"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO customers (name, contact, customer_email, notes)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("Jane Doe", "555-010-1101", "jane.doe@example.test", "Prefers neutral mats."),
                ("John Doe", "555-010-1102", "john.doe@example.test", "Demo customer."),
                ("Morgan Reed", "555-010-1103", "morgan.reed@example.test", "Prefers natural wood."),
                ("Alex Rivera", "555-010-1104", "alex.rivera@example.test", "Pickup on Saturdays."),
            ],
        )
        conn.executemany(
            """
            INSERT INTO images (filename, path, width_in, height_in, ratio_label, crop_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("demo-art-1.png", "demo-art-1.png", 8, 10, "4:5", "{}"),
                ("demo-art-2.png", "demo-art-2.png", 14, 10, "7:5", "{}"),
            ],
        )

        base_payload = {
            "width_in": 8,
            "height_in": 10,
            "mat_border_in": 2,
            "layout_mode": "single",
            "moulding": {"sku": "DEMO-M-101", "name": "Graphite Flat"},
            "top_mat": {"sku": "DEMO-MAT-1", "name": "Warm White"},
            "line_items": {
                "moulding": 72.00,
                "mat": 18.00,
            },
            "subtotal": 90.00,
            "tax": 5.40,
            "total": 95.40,
        }
        orders = [
            ("Jane Doe", "555-010-1101", "jane.doe@example.test", "quote", None, None, None, "2026-01-10 10:00:00"),
            ("John Doe", "555-010-1102", "john.doe@example.test", "work_order", "2026-01-11 11:00:00", None, None, "2026-01-11 11:00:00"),
            ("Morgan Reed", "555-010-1103", "morgan.reed@example.test", "invoice", "2026-01-12 12:00:00", "2026-01-13 15:00:00", "2026-01-13 15:00:00", "2026-01-12 12:00:00"),
        ]
        for name, phone, email, status, approved, completed, invoiced, created in orders:
            cursor = conn.execute(
                """
                INSERT INTO orders (
                    customer_name, customer_contact, customer_email, status,
                    approved_at, completed_at, invoiced_at, payload_json,
                    subtotal, tax, total, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 90, 5.4, 95.4, ?, ?)
                """,
                (name, phone, email, status, approved, completed, invoiced, json.dumps(base_payload), created, created),
            )
            conn.execute(
                "INSERT INTO order_status_history (order_id, status, note, created_at) VALUES (?, ?, ?, ?)",
                (cursor.lastrowid, status, "Fictional demo record", created),
            )

        settings = {
            DEMO_MARKER_KEY: DEMO_MARKER_VALUE,
            "studio_business_name": "FramersHaven",
            "studio_contact_name": "Demo Operator",
            "studio_phone": "555-010-2026",
            "studio_email": "hello@example.test",
            "studio_street": "100 Gallery Lane",
            "studio_city": "Cedar Falls",
            "studio_state": "KY",
            "studio_postal_code": "40000",
        }
        conn.executemany(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            settings.items(),
        )
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Replace a non-demo database")
    parser.add_argument("--db", type=Path, default=ROOT / "studio.db")
    parser.add_argument("--uploads", type=Path, default=ROOT / "uploads")
    args = parser.parse_args()
    try:
        create_demo_data(args.db.resolve(), args.uploads.resolve(), force=args.force)
    except RuntimeError as exc:
        parser.error(str(exc))
    print(f"Demo workspace ready: {args.db.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
