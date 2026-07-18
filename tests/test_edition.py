from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from app import db
from app import main as main_module
from app.edition import get_edition, get_edition_info
from app.main import app
from fastapi.testclient import TestClient


class EditionModuleTests(unittest.TestCase):
    def setUp(self):
        self.original_edition = os.environ.get("FRAMERSHAVEN_EDITION")

    def tearDown(self):
        if self.original_edition is None:
            os.environ.pop("FRAMERSHAVEN_EDITION", None)
        else:
            os.environ["FRAMERSHAVEN_EDITION"] = self.original_edition

    def test_default_edition_is_full_community(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        self.assertEqual(get_edition(), "community")
        info = get_edition_info()
        self.assertEqual(info["label"], "Community Edition")
        self.assertIn("full local workstation", info["description"])
        self.assertEqual(info["limits"]["active_catalog_items"], "unlimited")
        self.assertEqual(info["limits"]["saved_orders_quotes"], "unlimited")
        self.assertEqual(info["limits"]["local_catalog_package_imports"], "unlimited")
        self.assertTrue(info["features"]["accounting_csv_export"])

    def test_workstation_env_is_legacy_alias_for_full_community(self):
        os.environ["FRAMERSHAVEN_EDITION"] = " WorkStation "
        self.assertEqual(get_edition(), "community")
        info = get_edition_info()
        self.assertEqual(info["edition"], "community")
        self.assertEqual(info["limits"]["studio_profiles"], "unlimited")
        self.assertIn("accounting_csv_export", info["unlimited"])

    def test_unknown_env_falls_back_to_community(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "enterprise-plus"
        self.assertEqual(get_edition(), "community")


class EditionApiTests(unittest.TestCase):
    def setUp(self):
        self.original_edition = os.environ.get("FRAMERSHAVEN_EDITION")
        self.tempdir = tempfile.TemporaryDirectory()
        db.DB_PATH = Path(self.tempdir.name) / "test_studio.db"
        main_module.BACKUP_DIR = Path(self.tempdir.name) / "backups"
        main_module.BACKUP_DIR.mkdir(exist_ok=True)
        main_module.PREVIEW_DIR = Path(self.tempdir.name) / "catalog_previews"
        main_module.PREVIEW_DIR.mkdir(exist_ok=True)
        main_module.CATALOG_IMPORT_DIR = Path(self.tempdir.name) / "catalog_imports"
        main_module.CATALOG_IMPORT_DIR.mkdir(exist_ok=True)
        self.original_upload_dir = main_module.UPLOAD_DIR
        main_module.UPLOAD_DIR = Path(self.tempdir.name) / "uploads"
        main_module.UPLOAD_DIR.mkdir(exist_ok=True)
        main_module._catalog_preview_basename_index.cache_clear()
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        db.init_db()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        main_module.UPLOAD_DIR = self.original_upload_dir
        main_module._catalog_preview_basename_index.cache_clear()
        self.tempdir.cleanup()
        if self.original_edition is None:
            os.environ.pop("FRAMERSHAVEN_EDITION", None)
        else:
            os.environ["FRAMERSHAVEN_EDITION"] = self.original_edition

    def test_default_api_edition_is_full_free_community(self):
        response = self.client.get("/api/edition")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["edition"], "community")
        self.assertEqual(data["label"], "Community Edition")
        self.assertEqual(data["limits"]["active_catalog_items"], "unlimited")
        self.assertTrue(data["features"]["accounting_csv_export"])

    def test_catalog_create_does_not_block_after_old_community_limit(self):
        for index in range(51):
            created = self.client.post(
                "/api/catalog/items",
                data={
                    "sku": f"C{index:03d}",
                    "name": f"Catalog {index:03d}",
                    "category": "moulding",
                    "cost": "10",
                    "width_in": "1.5",
                },
            )
            self.assertEqual(created.status_code, 200, f"Item {index} should be accepted: {created.text}")

    def test_saved_orders_quotes_do_not_block_after_old_community_limit(self):
        for index in range(26):
            created = self.client.post(
                "/api/orders",
                data={
                    "customer_name": f"Quote Customer {index:03d}",
                    "customer_contact": "555-010-0100",
                    "payload_json": json.dumps({"subtotal": 10, "tax": 0.6, "total": 10.6}),
                    "subtotal": "10",
                    "tax": "0.6",
                    "total": "10.6",
                },
            )
            self.assertEqual(created.status_code, 200, f"Order {index} should be accepted: {created.text}")

        listed = self.client.get("/api/orders")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["orders"]), 26)

    def test_local_catalog_package_imports_are_unlimited(self):
        csv_path = Path(self.tempdir.name) / "catalog_imports" / "mats.csv"
        csv_path.write_text(
            "Code,Description,Width,Height,Price\nTEST001,Test Mat,32,40,15.50\n",
            encoding="utf-8",
        )

        first = self.client.post("/api/catalog/import/package", data={"source": "mats"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["inserted"], 1)

        second = self.client.post("/api/catalog/import/package", data={"source": "mats"})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["updated"], 1)

    def test_accounting_csv_export_is_available_in_community(self):
        response = self.client.get("/api/accounting/export.zip")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/zip")

    def test_edition_status_endpoint_returns_usage_and_unlimited_limits(self):
        self.client.post(
            "/api/catalog/items",
            data={
                "sku": "S001",
                "name": "Status Test",
                "category": "moulding",
                "cost": "10",
                "width_in": "1.5",
            },
        )
        self.client.post(
            "/api/orders",
            data={
                "customer_name": "Status Quote",
                "customer_contact": "555-010-0100",
                "payload_json": json.dumps({"subtotal": 10, "tax": 0.6, "total": 10.6}),
                "subtotal": "10",
                "tax": "0.6",
                "total": "10.6",
            },
        )

        response = self.client.get("/api/edition/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["edition"], "community")
        self.assertEqual(data["usage"]["active_catalog_items"], 1)
        self.assertEqual(data["usage"]["saved_orders_quotes"], 1)
        self.assertEqual(data["limits"]["active_catalog_items"], "unlimited")
        self.assertEqual(data["limits"]["saved_orders_quotes"], "unlimited")
        self.assertEqual(data["limits"]["local_catalog_package_imports"], "unlimited")


if __name__ == "__main__":
    unittest.main()
