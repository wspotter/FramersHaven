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

DEMO_MOULDINGS = [
    ("DEMO-M-001", "Mahogany Reverse Stairs", 5.00, 1.5, 0.625, "mouldings/demo-0354-3029.jpg", "#5b3825"),
    ("DEMO-M-002", "Distressed Mocha Bevel Edge", 5.15, 1.0, 0.625, "mouldings/demo-1105-45.jpg", "#5b3825"),
    ("DEMO-M-003", "Silver Fillet", 5.20, 0.375, 0.375, "mouldings/demo-1110-80.jpg", "#a7adb2"),
    ("DEMO-M-004", "Light Walnut Faux Burl Scoop", 7.55, 2.625, 0.375, "mouldings/demo-1300-55.jpg", "#5b3825"),
    ("DEMO-M-005", "Dark Brown Chattered Panel", 6.90, 1.125, 0.375, "mouldings/demo-1300-830.jpg", "#5b3825"),
    ("DEMO-M-006", "Light Walnut Faux Burl Distress", 8.05, 1.875, 0.625, "mouldings/demo-1310-90.jpg", "#5b3825"),
    ("DEMO-M-007", "Gold Rubbed Acanthus Carve", 9.80, 3.375, 0.5, "mouldings/demo-1325-60.jpg", "#b08a42"),
    ("DEMO-M-008", "Espresso Two-Tone Reverse", 9.75, 2.625, 0.625, "mouldings/demo-1355-35.jpg", "#5b3825"),
    ("DEMO-M-009", "Dark Bronze Bevel Block", 4.75, 1.875, 0.5, "mouldings/demo-1380-35.jpg", "#b08a42"),
    ("DEMO-M-010", "Veined Gold Streak Slope", 5.20, 1.75, 0.375, "mouldings/demo-1395-85.jpg", "#b08a42"),
    ("DEMO-M-011", "Silver Deep Poly Floater", 5.55, 1.5, 1.875, "mouldings/demo-1425-35.jpg", "#a7adb2"),
    ("DEMO-M-012", "Flat Oak Wood Cube", 5.50, 0.75, 0.5, "mouldings/demo-1605-65.jpg", "#b88b5a"),
    ("DEMO-M-013", "Black Slope with Silver Lip", 6.15, 0.875, 0.5, "mouldings/demo-1610-65.jpg", "#262626"),
    ("DEMO-M-014", "Round Distressed Silver Mini", 6.50, 0.625, 0.5, "mouldings/demo-1615-90.jpg", "#a7adb2"),
    ("DEMO-M-015", "Chalk White Rubbed Scoop", 7.15, 0.75, 0.375, "mouldings/demo-2300-25.jpg", "#f1eadc"),
    ("DEMO-M-016", "Walnut Stained Flat", 8.10, 1.25, 0.625, "mouldings/demo-2400-80.jpg", "#5b3825"),
    ("DEMO-M-017", "Black Notch Lip", 8.45, 1.0, 0.375, "mouldings/demo-2410-05.jpg", "#262626"),
    ("DEMO-M-018", "Espresso Low-Profile", 3.85, 0.75, 0.375, "mouldings/demo-2415-25.jpg", "#5b3825"),
    ("DEMO-M-019", "Black Reverse", 5.00, 1.5, 0.625, "mouldings/demo-2420-40.jpg", "#262626"),
    ("DEMO-M-020", "Black Block Cap", 5.55, 1.5, 2.0, "mouldings/demo-2425-50.jpg", "#262626"),
    ("DEMO-M-021", "Natural Stain Cap", 5.50, 0.75, 1.25, "mouldings/demo-2435-60.jpg", "#b88b5a"),
    ("DEMO-M-022", "Espresso Tall Bevel", 6.15, 0.875, 0.875, "mouldings/demo-2445-10.jpg", "#5b3825"),
    ("DEMO-M-023", "Muted Silver Cap", 7.40, 1.75, 0.625, "mouldings/demo-2450-20.jpg", "#a7adb2"),
    ("DEMO-M-024", "Real Oak Veneer Cap", 7.15, 0.75, 1.5, "mouldings/demo-2460-80.jpg", "#b88b5a"),
    ("DEMO-M-025", "Drift Grey Wormwood Flat", 8.50, 1.75, 0.375, "mouldings/demo-2500-65.jpg", "#a7adb2"),
    ("DEMO-M-026", "Maple Burl Block", 8.75, 1.375, 0.375, "mouldings/demo-2505-95.jpg", "#b88b5a"),
    ("DEMO-M-027", "Black Reverse with Steps", 5.25, 2.5, 0.625, "mouldings/demo-300-105.jpg", "#262626"),
    ("DEMO-M-028", "Black Scoop Bead", 4.60, 1.0, 0.5, "mouldings/demo-300-595.jpg", "#262626"),
    ("DEMO-M-029", "Silver Panel Compo Trim", 5.15, 1.0, 0.375, "mouldings/demo-300-895.jpg", "#a7adb2"),
    ("DEMO-M-030", "Bronze Notch Lip Mini", 5.40, 0.625, 0.5, "mouldings/demo-305-310.jpg", "#b08a42"),
    ("DEMO-M-031", "Black Rounded Reverse", 6.65, 1.5, 0.625, "mouldings/demo-305-565.jpg", "#262626"),
    ("DEMO-M-032", "Silver Metal-Leaf Mini Cube", 6.50, 0.625, 0.5, "mouldings/demo-305-960.jpg", "#a7adb2"),
    ("DEMO-M-033", "Ivory Scroll with Gold Lip", 7.55, 1.25, 0.25, "mouldings/demo-310-285.jpg", "#b08a42"),
    ("DEMO-M-034", "Driftwood Rake Cap", 7.70, 0.75, 1.125, "mouldings/demo-310-425.jpg", "#5b3825"),
    ("DEMO-M-035", "Off-White Distressed Cube", 8.15, 0.625, 0.5, "mouldings/demo-310-570.jpg", "#f1eadc"),
    ("DEMO-M-036", "Gold Pattern Mini", 3.75, 0.625, 0.375, "mouldings/demo-315-035.jpg", "#b08a42"),
    ("DEMO-M-037", "Mahogany Woodtone Scoop", 5.60, 2.25, 0.625, "mouldings/demo-335-90.jpg", "#5b3825"),
    ("DEMO-M-038", "Distressed Silver Fillet", 4.75, 0.5, 0.375, "mouldings/demo-355-80.jpg", "#a7adb2"),
    ("DEMO-M-039", "Antique Wash Gold Bead", 6.90, 2.5, 0.375, "mouldings/demo-385-75.jpg", "#b08a42"),
    ("DEMO-M-040", "Flat Black MDF with Bevel Lip", 7.15, 2.125, 0.5, "mouldings/demo-4100-75.jpg", "#262626"),
    ("DEMO-M-041", "Black Reverse Narrow", 6.80, 1.0, 0.375, "mouldings/demo-460-70.jpg", "#262626"),
    ("DEMO-M-042", "Black Distress with Gold Steps", 8.35, 2.25, 0.75, "mouldings/demo-490-30.jpg", "#262626"),
    ("DEMO-M-043", "Black Rounded Edge Slope", 8.10, 1.25, 0.5, "mouldings/demo-800-140.jpg", "#262626"),
    ("DEMO-M-044", "Black Painted Cap", 8.25, 0.75, 0.875, "mouldings/demo-800-415.jpg", "#262626"),
    ("DEMO-M-045", "Dark Walnut Stain Pine", 4.65, 1.75, 0.625, "mouldings/demo-800-685.jpg", "#5b3825"),
    ("DEMO-M-046", "Grey Woodtone Flat", 4.90, 1.375, 0.625, "mouldings/demo-800-925.jpg", "#a7adb2"),
    ("DEMO-M-047", "Bright Silver Distress", 4.95, 0.75, 0.375, "mouldings/demo-805-315.jpg", "#a7adb2"),
    ("DEMO-M-048", "Grey Wood Floater", 6.20, 1.625, 1.75, "mouldings/demo-805-510.jpg", "#a7adb2"),
    ("DEMO-M-049", "Teak Stain Floater", 6.95, 1.875, 1.125, "mouldings/demo-805-90.jpg", "#5b3825"),
    ("DEMO-M-050", "Mahogany Reverse with Dark Lip", 7.40, 1.75, 0.625, "mouldings/demo-860-50.jpg", "#5b3825"),
]

DEMO_MATS = [
    ("DEMO-MAT-001", "Warm White", 12.00, "#f2eee2"),
    ("DEMO-MAT-002", "Soft White", 12.25, "#f7f5ee"),
    ("DEMO-MAT-003", "Gallery Cream", 12.50, "#ede2c8"),
    ("DEMO-MAT-004", "Antique Ivory", 12.75, "#e7dcc3"),
    ("DEMO-MAT-005", "Linen Natural", 13.00, "#d9cbb0"),
    ("DEMO-MAT-006", "Parchment", 13.25, "#eadfca"),
    ("DEMO-MAT-007", "Sandstone", 13.50, "#c9b595"),
    ("DEMO-MAT-008", "Oatmeal", 13.75, "#c8bea9"),
    ("DEMO-MAT-009", "Mist Gray", 14.00, "#cfd4d7"),
    ("DEMO-MAT-010", "Dove Gray", 14.25, "#b6bcc1"),
    ("DEMO-MAT-011", "Storm Gray", 14.50, "#7b848c"),
    ("DEMO-MAT-012", "Charcoal", 14.75, "#34373a"),
    ("DEMO-MAT-013", "Graphite", 15.00, "#202328"),
    ("DEMO-MAT-014", "Midnight Black", 15.25, "#101114"),
    ("DEMO-MAT-015", "Deep Blue", 12.00, "#203c55"),
    ("DEMO-MAT-016", "Navy Linen", 12.25, "#25344f"),
    ("DEMO-MAT-017", "Slate Blue", 12.50, "#5d718b"),
    ("DEMO-MAT-018", "Powder Blue", 12.75, "#b8c8d8"),
    ("DEMO-MAT-019", "Sage", 13.00, "#a9b79f"),
    ("DEMO-MAT-020", "Olive Gray", 13.25, "#79816a"),
    ("DEMO-MAT-021", "Forest", 13.50, "#334a39"),
    ("DEMO-MAT-022", "Moss", 13.75, "#687a55"),
    ("DEMO-MAT-023", "Eucalyptus", 14.00, "#bcc8b8"),
    ("DEMO-MAT-024", "Sea Glass", 14.25, "#a9c8bf"),
    ("DEMO-MAT-025", "Teal Shadow", 14.50, "#28575c"),
    ("DEMO-MAT-026", "Aubergine", 14.75, "#4b334f"),
    ("DEMO-MAT-027", "Plum Smoke", 15.00, "#776078"),
    ("DEMO-MAT-028", "Soft Blush", 15.25, "#df9ba7"),
    ("DEMO-MAT-029", "Rose Taupe", 12.00, "#b8898b"),
    ("DEMO-MAT-030", "Terracotta", 12.25, "#a45d43"),
    ("DEMO-MAT-031", "Clay", 12.50, "#b98264"),
    ("DEMO-MAT-032", "Rust", 12.75, "#82442f"),
    ("DEMO-MAT-033", "Burgundy", 13.00, "#632d36"),
    ("DEMO-MAT-034", "Cranberry", 13.25, "#8f3946"),
    ("DEMO-MAT-035", "Ochre", 13.50, "#bd8a3d"),
    ("DEMO-MAT-036", "Gold Wheat", 13.75, "#d6b46a"),
    ("DEMO-MAT-037", "Buttercream", 14.00, "#f1dfac"),
    ("DEMO-MAT-038", "Coffee", 14.25, "#5a4236"),
    ("DEMO-MAT-039", "Espresso", 14.50, "#352620"),
    ("DEMO-MAT-040", "Walnut Brown", 14.75, "#6f5038"),
    ("DEMO-MAT-041", "Warm Taupe", 15.00, "#9a8774"),
    ("DEMO-MAT-042", "Cool Taupe", 15.25, "#8e8a82"),
    ("DEMO-MAT-043", "Silver White", 12.00, "#eef0ef"),
    ("DEMO-MAT-044", "Pearl", 12.25, "#f4f1e6"),
    ("DEMO-MAT-045", "Museum White", 12.50, "#fbfaf6"),
    ("DEMO-MAT-046", "Shadow White", 12.75, "#e9e8e1"),
    ("DEMO-MAT-047", "Blue Black", 13.00, "#161d27"),
    ("DEMO-MAT-048", "Warm Black", 13.25, "#1c1715"),
    ("DEMO-MAT-049", "Pebble", 13.50, "#aaa69c"),
    ("DEMO-MAT-050", "Soft Gold", 13.75, "#c8ad76"),
]


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
                (sku, name, category, cost, vendor, width_in, height_in, rabbet_in, preview_filename, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    sku,
                    name,
                    "moulding",
                    cost,
                    "Framewise Demo",
                    width,
                    None,
                    rabbet,
                    preview_filename,
                    json.dumps({"color": color, "source": "public demo"}),
                )
                for sku, name, cost, width, rabbet, preview_filename, color in DEMO_MOULDINGS
            ]
            + [
                (
                    sku,
                    name,
                    "mat",
                    cost,
                    "Framewise Demo",
                    32.0,
                    40.0,
                    None,
                    None,
                    json.dumps({"color": color, "core": "white", "source": "public demo"}),
                )
                for sku, name, cost, color in DEMO_MATS
            ]
            + [
                ("DEMO-GLZ-1", "Conservation Clear", "glazing", 2.25, "Framewise Demo", None, None, None, None, "{}"),
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
            "moulding": {"sku": "DEMO-M-027", "name": "Black Reverse with Steps"},
            "top_mat": {"sku": "DEMO-MAT-001", "name": "Warm White"},
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
