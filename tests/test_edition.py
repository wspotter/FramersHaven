from __future__ import annotations

import json
import os
import tempfile
import unittest
import zipfile
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

    def test_default_edition_is_community(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        self.assertEqual(get_edition(), "community")

    def test_workstation_env_sets_workstation(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        self.assertEqual(get_edition(), "workstation")

    def test_workstation_env_is_case_and_whitespace_insensitive(self):
        os.environ["FRAMERSHAVEN_EDITION"] = " WorkStation "
        self.assertEqual(get_edition(), "workstation")

    def test_unknown_env_falls_back_to_community(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "enterprise-plus"
        self.assertEqual(get_edition(), "community")

    def test_community_info_has_limits_and_features(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        info = get_edition_info()
        self.assertEqual(info["edition"], "community")
        self.assertEqual(info["label"], "Community Edition")
        self.assertIn("source-available", info["description"])
        self.assertEqual(info["limits"]["studio_profiles"], 1)
        self.assertEqual(info["limits"]["active_catalog_items"], 50)
        self.assertEqual(info["limits"]["saved_orders_quotes"], 25)
        self.assertEqual(info["limits"]["local_catalog_package_imports"], 1)
        self.assertFalse(info["features"]["accounting_csv_export"])
        self.assertFalse(info["features"]["windows_paid_package"])
        self.assertEqual(info["unlimited"], [])

    def test_workstation_info_removes_limits(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        info = get_edition_info()
        self.assertEqual(info["edition"], "workstation")
        self.assertEqual(info["label"], "Workstation Edition")
        self.assertEqual(info["limits"]["studio_profiles"], "unlimited")
        self.assertEqual(info["limits"]["active_catalog_items"], "unlimited")
        self.assertEqual(info["limits"]["saved_orders_quotes"], "unlimited")
        self.assertEqual(info["limits"]["local_catalog_package_imports"], "unlimited")
        self.assertTrue(info["features"]["accounting_csv_export"])
        self.assertTrue(info["features"]["windows_paid_package"])
        self.assertIn("active_catalog_items", info["unlimited"])


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

    def test_get_api_edition_defaults_to_community(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        response = self.client.get("/api/edition")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["edition"], "community")
        self.assertIn("label", data)
        self.assertIn("limits", data)
        self.assertIn("features", data)

    def test_get_api_edition_workstation(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        response = self.client.get("/api/edition")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["edition"], "workstation")
        self.assertEqual(data["limits"]["active_catalog_items"], "unlimited")

    def test_get_api_edition_unknown_falls_back_to_community(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "legacy"
        response = self.client.get("/api/edition")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["edition"], "community")

    def test_catalog_create_allows_up_to_50_in_community(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        for index in range(50):
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

        blocked = self.client.post(
            "/api/catalog/items",
            data={
                "sku": "OVER",
                "name": "OverLimit",
                "category": "moulding",
                "cost": "10",
                "width_in": "1.5",
            },
        )
        self.assertEqual(blocked.status_code, 403)
        self.assertIn("Community edition includes up to 50 active catalog items", blocked.json()["detail"])

    def test_catalog_create_allows_unlimited_in_workstation(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        for index in range(51):
            created = self.client.post(
                "/api/catalog/items",
                data={
                    "sku": f"W{index:03d}",
                    "name": f"Work {index:03d}",
                    "category": "moulding",
                    "cost": "10",
                    "width_in": "1.5",
                },
            )
            self.assertEqual(created.status_code, 200, f"Workstation item {index} should be accepted: {created.text}")

    def test_catalog_update_to_active_does_not_count_against_limit(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        created = self.client.post(
            "/api/catalog/items",
            data={
                "sku": "UPDATE1",
                "name": "Update One",
                "category": "moulding",
                "cost": "10",
                "width_in": "1.5",
            },
        )
        self.assertEqual(created.status_code, 200)
        item_id = created.json()["item_id"]

        self.client.post(
            f"/api/catalog/items/{item_id}",
            data={
                "sku": "UPDATE1",
                "name": "Update One",
                "category": "moulding",
                "cost": "10",
                "width_in": "1.5",
                "active": "0",
            },
        )
        response = self.client.post(
            f"/api/catalog/items/{item_id}",
            data={
                "sku": "UPDATE1",
                "name": "Update One",
                "category": "moulding",
                "cost": "10",
                "width_in": "1.5",
                "active": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["item_id"], item_id)

    def test_catalog_duplicate_create_is_checked_before_limit(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        for index in range(50):
            created = self.client.post(
                "/api/catalog/items",
                data={
                    "sku": f"D{index:03d}",
                    "name": f"Duplicate {index:03d}",
                    "category": "moulding",
                    "cost": "10",
                    "width_in": "1.5",
                },
            )
            self.assertEqual(created.status_code, 200)

        duplicate = self.client.post(
            "/api/catalog/items",
            data={
                "sku": "D000",
                "name": "Duplicate Zero",
                "category": "moulding",
                "cost": "10",
                "width_in": "1.5",
            },
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("already exists", duplicate.json()["detail"])

    def test_workstation_batch_import_can_insert_new_catalog_items(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        csv_text = "\n".join(
            [
                "sku,name,category,cost,width_in",
                *(f"I{i:03d},Frame {i:03d},moulding,{10 + i},1.5" for i in range(1, 6)),
            ]
        )

        imported = self.client.post(
            "/api/catalog/import",
            files={"file": ("catalog.csv", csv_text, "text/csv")},
        )
        self.assertEqual(imported.status_code, 200)
        self.assertEqual(imported.json()["inserted"], 5)

    def test_community_batch_import_allows_exact_remaining_catalog_slots(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        for index in range(49):
            created = self.client.post(
                "/api/catalog/items",
                data={
                    "sku": f"E{index:03d}",
                    "name": f"Exact {index:03d}",
                    "category": "moulding",
                    "cost": "10",
                    "width_in": "1.5",
                },
            )
            self.assertEqual(created.status_code, 200)

        csv_text = "\n".join(["sku,name,category,cost,width_in", "E999,Exact Fill,moulding,12,1.5"])
        imported = self.client.post(
            "/api/catalog/import",
            files={"file": ("catalog.csv", csv_text, "text/csv")},
        )
        self.assertEqual(imported.status_code, 200)
        self.assertEqual(imported.json()["inserted"], 1)

    def test_community_batch_import_blocks_new_catalog_items_past_limit_without_partial_insert(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        for index in range(49):
            created = self.client.post(
                "/api/catalog/items",
                data={
                    "sku": f"B{index:03d}",
                    "name": f"Blocked {index:03d}",
                    "category": "moulding",
                    "cost": "10",
                    "width_in": "1.5",
                },
            )
            self.assertEqual(created.status_code, 200)

        csv_text = "\n".join(
            [
                "sku,name,category,cost,width_in",
                "B999,Blocked First,moulding,12,1.5",
                "B998,Blocked Second,moulding,13,1.5",
            ]
        )
        blocked = self.client.post(
            "/api/catalog/import",
            files={"file": ("catalog.csv", csv_text, "text/csv")},
        )
        self.assertEqual(blocked.status_code, 403)
        self.assertIn("Community edition includes up to 50 active catalog items", blocked.json()["detail"])

        search = self.client.get("/api/catalog/search", params={"category": "moulding", "limit": 0})
        self.assertEqual(search.status_code, 200)
        skus = {item["sku"] for item in search.json()["items"]}
        self.assertNotIn("B999", skus)
        self.assertNotIn("B998", skus)

    def test_community_allows_up_to_25_saved_orders_quotes(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        for index in range(25):
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

        blocked = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Over Limit Customer",
                "customer_contact": "555-010-0100",
                "payload_json": json.dumps({"subtotal": 10, "tax": 0.6, "total": 10.6}),
                "subtotal": "10",
                "tax": "0.6",
                "total": "10.6",
            },
        )
        self.assertEqual(blocked.status_code, 403)
        self.assertIn("Community edition includes up to 25 saved quotes/orders", blocked.json()["detail"])

        listed = self.client.get("/api/orders")
        self.assertEqual(listed.status_code, 200)
        orders = listed.json()["orders"]
        self.assertEqual(len(orders), 25)

    def test_workstation_has_no_saved_orders_quotes_limit(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        for index in range(26):
            created = self.client.post(
                "/api/orders",
                data={
                    "customer_name": f"WS Customer {index:03d}",
                    "customer_contact": "555-010-0100",
                    "payload_json": json.dumps({"subtotal": 10, "tax": 0.6, "total": 10.6}),
                    "subtotal": "10",
                    "tax": "0.6",
                    "total": "10.6",
                },
            )
            self.assertEqual(created.status_code, 200, f"Workstation order {index} should be accepted: {created.text}")

        listed = self.client.get("/api/orders")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["orders"]), 26)

    def test_existing_orders_remain_readable_and_exportable_at_community_limit(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        for index in range(25):
            self.client.post(
                "/api/orders",
                data={
                    "customer_name": f"Read Test {index:03d}",
                    "customer_contact": "555-010-0100",
                    "payload_json": json.dumps({
                        "subtotal": 10,
                        "tax": 0.6,
                        "total": 10.6,
                        "design_state": {"opening_layout": "single"},
                        "selected": {},
                        "line_items": {},
                    }),
                    "subtotal": "10",
                    "tax": "0.6",
                    "total": "10.6",
                },
            )

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM orders ORDER BY id ASC LIMIT 1")
        first_order_id = cur.fetchone()["id"]
        cur.execute("SELECT id FROM orders ORDER BY id DESC LIMIT 1")
        last_order_id = cur.fetchone()["id"]
        conn.close()

        detail = self.client.get(f"/api/orders/{first_order_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["order"]["customer_name"], "Read Test 000")

        exported = self.client.get(f"/api/orders/{last_order_id}/export", params={"format": "pdf"})
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.headers["content-type"], "application/pdf")

    def test_community_allows_one_local_catalog_package_import(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        csv_path = self.tempdir.name + "/catalog_imports/mats.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Code,Description,Width,Height,Price\n")
            f.write("TEST001,Test Mat,32,40,15.50\n")

        first = self.client.post("/api/catalog/import/package", data={"source": "mats"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["inserted"], 1)

        second = self.client.post("/api/catalog/import/package", data={"source": "mats"})
        self.assertEqual(second.status_code, 403)
        self.assertIn("one successful catalog package import", second.json()["detail"])

    def test_workstation_has_unlimited_local_catalog_package_imports(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        csv_path = self.tempdir.name + "/catalog_imports/mouldings.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Code,Description,Width in.,Height in.,Rabbet in.,Price\n")
            f.write("WTEST001,Test Moulding,2,1,0.5,8.00\n")
            f.write("WTEST002,Test Moulding 2,2,1,0.5,8.50\n")

        first = self.client.post("/api/catalog/import/package", data={"source": "mouldings"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["inserted"], 2)

        second = self.client.post("/api/catalog/import/package", data={"source": "mouldings"})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["updated"], 2)

    def test_failed_imports_do_not_consume_allowance(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        csv_path = self.tempdir.name + "/catalog_imports/mats.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Code,Description,Width,Height,Price\n")
            f.write(",No Code,32,40,15.50\n")

        failed = self.client.post("/api/catalog/import/package", data={"source": "mats"})
        self.assertEqual(failed.status_code, 200)
        self.assertEqual(failed.json()["skipped"], 1)

        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Code,Description,Width,Height,Price\n")
            f.write("GOOD001,Good Mat,32,40,15.50\n")

        success = self.client.post("/api/catalog/import/package", data={"source": "mats"})
        self.assertEqual(success.status_code, 200)
        self.assertEqual(success.json()["inserted"], 1)

        blocked = self.client.post("/api/catalog/import/package", data={"source": "mats"})
        self.assertEqual(blocked.status_code, 403)

    def test_import_count_persists_in_database(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        csv_path = self.tempdir.name + "/catalog_imports/mats.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Code,Description,Width,Height,Price\n")
            f.write("PERSIST01,Persist Test,32,40,15.50\n")

        first = self.client.post("/api/catalog/import/package", data={"source": "mats"})
        self.assertEqual(first.status_code, 200)

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = 'local_catalog_package_imports_count'")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(int(row["value"]), 1)
        conn.close()

    def test_blocked_catalog_package_import_does_not_extract_previews(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        csv_path = Path(self.tempdir.name) / "catalog_imports" / "mats.csv"
        zip_path = Path(self.tempdir.name) / "catalog_imports" / "mats.zip"
        csv_path.write_text(
            "Code,Description,Width,Height,Price\nFIRST01,First Mat,32,40,15.50\n",
            encoding="utf-8",
        )
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("FIRST01.jpg", b"first-preview")

        first = self.client.post("/api/catalog/import/package", data={"source": "mats"})
        self.assertEqual(first.status_code, 200)

        csv_path.write_text(
            "Code,Description,Width,Height,Price\nSECOND01,Second Mat,32,40,16.50\n",
            encoding="utf-8",
        )
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("SECOND01.jpg", b"second-preview")

        blocked = self.client.post("/api/catalog/import/package", data={"source": "mats"})
        self.assertEqual(blocked.status_code, 403)
        self.assertFalse((main_module.PREVIEW_DIR / "mats" / "SECOND01.jpg").exists())

    def test_catalog_package_import_respects_community_active_item_limit(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)
        conn = db.get_connection()
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO catalog_items (sku, name, category, cost, active)
            VALUES (?, ?, 'moulding', 10, 1)
            """,
            [(f"LIMIT{index:03d}", f"Limit {index:03d}") for index in range(50)],
        )
        conn.commit()
        conn.close()

        csv_path = Path(self.tempdir.name) / "catalog_imports" / "mats.csv"
        csv_path.write_text(
            "Code,Description,Width,Height,Price\nOVER50,Over Fifty,32,40,15.50\n",
            encoding="utf-8",
        )

        blocked = self.client.post("/api/catalog/import/package", data={"source": "mats"})
        self.assertEqual(blocked.status_code, 403)
        self.assertIn("50 active catalog items", blocked.json()["detail"])

        conn = db.get_connection()
        count = conn.execute(
            "SELECT value FROM settings WHERE key = 'local_catalog_package_imports_count'"
        ).fetchone()["value"]
        inserted = conn.execute("SELECT id FROM catalog_items WHERE sku = 'OVER50'").fetchone()
        conn.close()
        self.assertEqual(int(count), 0)
        self.assertIsNone(inserted)


if __name__ == "__main__":
    unittest.main()
