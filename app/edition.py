from __future__ import annotations

import os

COMMUNITY = "community"
WORKSTATION = "workstation"


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
