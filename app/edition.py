from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException

COMMUNITY = "community"
WORKSTATION = "workstation"
CATALOG_ITEM_LIMIT = 50
COMMUNITY_CATALOG_LIMIT_DENIED_DETAIL = (
    "Community edition includes up to 50 active catalog items. "
    "This item was not added, and existing catalog data was not changed."
)

SAVED_ORDERS_QUOTES_LIMIT = 25
COMMUNITY_SAVED_ORDERS_QUOTES_LIMIT_DENIED_DETAIL = (
    "Community edition includes up to 25 saved quotes/orders. "
    "This quote was not saved, and existing records remain available."
)


def get_edition() -> str:
    raw = os.environ.get("FRAMERSHAVEN_EDITION", "").strip().lower()
    if raw == WORKSTATION:
        return WORKSTATION
    return COMMUNITY


def get_edition_info() -> dict[str, object]:
    edition = get_edition()
    if edition == WORKSTATION:
        return {
            "edition": WORKSTATION,
            "label": "Workstation Edition",
            "description": "Planned paid Windows-ready ZIP/folder workflow for daily local use.",
            "limits": {
                "studio_profiles": "unlimited",
                "active_catalog_items": "unlimited",
                "saved_orders_quotes": "unlimited",
                "local_catalog_package_imports": "unlimited",
            },
            "features": {
                "accounting_csv_export": True,
                "windows_paid_package": True,
                "branded_templates": True,
            },
            "unlimited": [
                "studio_profiles",
                "active_catalog_items",
                "saved_orders_quotes",
                "local_catalog_package_imports",
                "accounting_csv_export",
                "windows_paid_package",
            ],
        }
    return {
        "edition": COMMUNITY,
        "label": "Community Edition",
        "description": "Free source-available snapshot for trying FramersHaven locally.",
        "limits": {
            "studio_profiles": 1,
            "active_catalog_items": 50,
            "saved_orders_quotes": 25,
            "local_catalog_package_imports": 1,
        },
        "features": {
            "accounting_csv_export": False,
            "windows_paid_package": False,
            "branded_templates": False,
        },
        "unlimited": [],
    }


def get_catalog_limit() -> int | None:
    return None if get_edition() == WORKSTATION else CATALOG_ITEM_LIMIT


def check_catalog_item_limit(conn: Any, new_active_count: int = 1) -> None:
    if new_active_count <= 0:
        return
    limit = get_catalog_limit()
    if limit is None:
        return
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE active = 1")
    row = cur.fetchone()
    current = row["count"]
    if current + new_active_count > limit:
        raise HTTPException(status_code=403, detail=COMMUNITY_CATALOG_LIMIT_DENIED_DETAIL)


def get_saved_orders_quotes_limit() -> int | None:
    return None if get_edition() == WORKSTATION else SAVED_ORDERS_QUOTES_LIMIT


def check_saved_orders_quotes_limit(conn: Any, new_count: int = 1) -> None:
    if new_count <= 0:
        return
    limit = get_saved_orders_quotes_limit()
    if limit is None:
        return
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM orders")
    row = cur.fetchone()
    current = row["count"]
    if current + new_count > limit:
        raise HTTPException(status_code=403, detail=COMMUNITY_SAVED_ORDERS_QUOTES_LIMIT_DENIED_DETAIL)


CATALOG_IMPORT_LIMIT = 1
COMMUNITY_CATALOG_IMPORT_LIMIT_DENIED_DETAIL = (
    "Community edition includes one successful catalog package import. "
    "This import was not applied. Failed imports do not count toward the allowance."
)


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
    if get_edition() == WORKSTATION:
        return
    current = get_catalog_imports_count(conn)
    if current >= CATALOG_IMPORT_LIMIT:
        raise HTTPException(status_code=403, detail=COMMUNITY_CATALOG_IMPORT_LIMIT_DENIED_DETAIL)
