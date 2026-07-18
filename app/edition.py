from __future__ import annotations

from typing import Any

COMMUNITY = "community"


def get_edition() -> str:
    """FramersHaven Community Edition is now the full free local workstation."""
    return COMMUNITY


def get_edition_info() -> dict[str, object]:
    return {
        "edition": COMMUNITY,
        "label": "Community Edition",
        "description": "Free full local workstation for framing design, quoting, catalog work, backups, and accounting CSV export.",
        "limits": {
            "studio_profiles": "unlimited",
            "active_catalog_items": "unlimited",
            "saved_orders_quotes": "unlimited",
            "local_catalog_package_imports": "unlimited",
        },
        "features": {
            "accounting_csv_export": True,
            "windows_paid_package": False,
            "branded_templates": False,
        },
        "unlimited": [
            "studio_profiles",
            "active_catalog_items",
            "saved_orders_quotes",
            "local_catalog_package_imports",
            "accounting_csv_export",
        ],
    }


def require_accounting_csv_export() -> None:
    return None


def get_catalog_limit() -> int | None:
    return None


def check_catalog_item_limit(conn: Any, new_active_count: int = 1) -> None:
    return None


def get_saved_orders_quotes_limit() -> int | None:
    return None


def check_saved_orders_quotes_limit(conn: Any, new_count: int = 1) -> None:
    return None


def get_catalog_imports_count(conn: Any) -> int:
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = 'local_catalog_package_imports_count'")
    row = cur.fetchone()
    if row is None:
        return 0
    try:
        return int(row["value"])
    except (TypeError, ValueError):
        return 0


def increment_catalog_imports_count(conn: Any) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO settings (key, value, updated_at)
        VALUES ('local_catalog_package_imports_count', '1', CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = CAST(value AS INTEGER) + 1, updated_at = CURRENT_TIMESTAMP
        """,
    )
    return get_catalog_imports_count(conn)


def check_catalog_package_import_limit(conn: Any) -> None:
    return None
