from __future__ import annotations

import csv
import io
import json
import os
import tempfile
import threading
import time
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from unittest.mock import patch

from app import db
from app import accounting_export
from app import main as main_module
from app.accounting_export import CUSTOMER_FIELDS, INVOICE_FIELDS, INVOICE_LINE_FIELDS
from app.main import app


EXPECTED_FILES = {
    "accounting_customers.csv",
    "accounting_invoices.csv",
    "accounting_invoice_lines.csv",
}


class AccountingExportTests(unittest.TestCase):
    def setUp(self):
        self.original_edition = os.environ.get("FRAMERSHAVEN_EDITION")
        self.original_export_dir = main_module.EXPORT_DIR
        self.original_db_path = db.DB_PATH
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        db.DB_PATH = root / "studio.db"
        main_module.EXPORT_DIR = root / "exports"
        main_module.EXPORT_DIR.mkdir()
        db.init_db()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        main_module.EXPORT_DIR = self.original_export_dir
        db.DB_PATH = self.original_db_path
        self.tempdir.cleanup()
        if self.original_edition is None:
            os.environ.pop("FRAMERSHAVEN_EDITION", None)
        else:
            os.environ["FRAMERSHAVEN_EDITION"] = self.original_edition

    def _read_bundle(self, response) -> dict[str, str]:
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(set(archive.namelist()), EXPECTED_FILES)
            return {name: archive.read(name).decode("utf-8") for name in EXPECTED_FILES}

    def test_community_accounting_export_is_blocked_without_writing_files(self):
        os.environ.pop("FRAMERSHAVEN_EDITION", None)

        response = self.client.get("/api/accounting/export.zip")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Accounting CSV export is available in Workstation Edition. Community data remains unchanged.",
        )
        self.assertFalse((main_module.EXPORT_DIR / "accounting").exists())

    def test_workstation_exports_header_only_bundle_for_empty_database(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"

        response = self.client.get("/api/accounting/export.zip")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/zip")
        files = self._read_bundle(response)
        expected_headers = {
            "accounting_customers.csv": CUSTOMER_FIELDS,
            "accounting_invoices.csv": INVOICE_FIELDS,
            "accounting_invoice_lines.csv": INVOICE_LINE_FIELDS,
        }
        for name in EXPECTED_FILES:
            disk_path = main_module.EXPORT_DIR / "accounting" / name
            self.assertTrue(disk_path.is_file())
            self.assertEqual(disk_path.read_bytes(), files[name].encode("utf-8"))
            reader = csv.DictReader(io.StringIO(files[name]))
            self.assertEqual(reader.fieldnames, expected_headers[name])
            rows = list(reader)
            self.assertEqual(rows, [])

    def test_workstation_bundle_preserves_schema_totals_and_csv_escaping(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        customer = self.client.post(
            "/api/customers",
            data={
                "name": 'Example, "Quoted" Customer',
                "contact": "555-010-0222",
                "customer_email": "quoted@example.test",
                "notes": "First line\nSecond line",
            },
        )
        self.assertEqual(customer.status_code, 200)
        line_label = 'Custom, "Rush"\nHandling'
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": 'Example, "Quoted" Customer',
                "customer_contact": "555-010-0222",
                "customer_email": "quoted@example.test",
                "payload_json": json.dumps(
                    {
                        "line_items": {
                            "moulding": 50,
                            line_label: 25,
                        },
                        "selected": {
                            "moulding": {"sku": "FRAME-1", "name": 'Frame, "Walnut"'},
                        },
                    }
                ),
                "subtotal": "75",
                "tax": "4.50",
                "total": "79.50",
            },
        )
        self.assertEqual(created.status_code, 200)

        response = self.client.get("/api/accounting/export.zip")

        self.assertEqual(response.status_code, 200)
        files = self._read_bundle(response)
        customer_rows = list(csv.DictReader(io.StringIO(files["accounting_customers.csv"])))
        invoice_rows = list(csv.DictReader(io.StringIO(files["accounting_invoices.csv"])))
        line_rows = list(csv.DictReader(io.StringIO(files["accounting_invoice_lines.csv"])))

        self.assertEqual(customer_rows[0]["customer_name"], 'Example, "Quoted" Customer')
        self.assertEqual(customer_rows[0]["notes"], "First line\nSecond line")
        self.assertEqual(invoice_rows[0]["invoice_number"], f"Q{created.json()['order_id']:05d}")
        self.assertEqual(invoice_rows[0]["status"], "quote")
        self.assertEqual(invoice_rows[0]["subtotal"], "75.00")
        self.assertEqual(invoice_rows[0]["tax"], "4.50")
        self.assertEqual(invoice_rows[0]["total"], "79.50")
        self.assertEqual(invoice_rows[0]["balance_due"], "79.50")
        self.assertEqual(invoice_rows[0]["customer_id"], customer_rows[0]["customer_id"])
        self.assertEqual(len(line_rows), 2)
        self.assertEqual(line_rows[0]["source_sku"], "FRAME-1")
        self.assertEqual(line_rows[0]["category"], "material")
        self.assertEqual(line_rows[1]["item"], line_label)
        self.assertEqual(line_rows[1]["amount"], "25.00")

    def test_malformed_payload_exports_fallback_line_without_modifying_order(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orders
            (customer_name, customer_contact, customer_email, status, payload_json, subtotal, tax, total)
            VALUES ('Fallback Customer', '555-010-0333', '', 'invoice', '{not-json', 40, 2.40, 42.40)
            """
        )
        order_id = cur.lastrowid
        conn.commit()
        conn.close()

        response = self.client.get("/api/accounting/export.zip")

        self.assertEqual(response.status_code, 200)
        files = self._read_bundle(response)
        lines = list(csv.DictReader(io.StringIO(files["accounting_invoice_lines.csv"])))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["invoice_id"], f"INV-{order_id:06d}")
        self.assertEqual(lines[0]["item"], "Order summary")
        self.assertEqual(lines[0]["amount"], "40.00")
        self.assertIn("invalid", lines[0]["description"].lower())

        conn = db.get_connection()
        stored = conn.execute("SELECT payload_json, total FROM orders WHERE id = ?", (order_id,)).fetchone()
        conn.close()
        self.assertEqual(stored["payload_json"], "{not-json")
        self.assertEqual(stored["total"], 42.40)

    def test_non_finite_line_amounts_fall_back_without_crashing(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        for amount in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(amount=amount):
                conn = db.get_connection()
                conn.execute(
                    """
                    INSERT INTO orders
                    (customer_name, customer_contact, status, payload_json, subtotal, tax, total)
                    VALUES (?, '555-010-0555', 'invoice', ?, 40, 2.40, 42.40)
                    """,
                    (f"Non-finite {amount}", json.dumps({"line_items": {"rush": amount}})),
                )
                conn.commit()
                conn.close()

        response = self.client.get("/api/accounting/export.zip")

        self.assertEqual(response.status_code, 200)
        files = self._read_bundle(response)
        lines = list(csv.DictReader(io.StringIO(files["accounting_invoice_lines.csv"])))
        self.assertEqual([row["item"] for row in lines], ["Order summary"] * 3)
        self.assertEqual([row["amount"] for row in lines], ["40.00"] * 3)

    def test_invalid_or_unreconciled_line_items_use_one_summary_line(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        payloads = [
            {"line_items": {"labor": 50, "rush": -50}},
            {"line_items": {"labor": 50, "rush": "invalid"}},
            {"line_items": {"labor": 50}},
        ]
        conn = db.get_connection()
        for index, payload in enumerate(payloads, start=1):
            conn.execute(
                """
                INSERT INTO orders
                (customer_name, customer_contact, status, payload_json, subtotal, tax, total)
                VALUES (?, '555-010-0666', 'invoice', ?, 100, 6, 106)
                """,
                (f"Reconcile {index}", json.dumps(payload)),
            )
        conn.commit()
        conn.close()

        response = self.client.get("/api/accounting/export.zip")

        self.assertEqual(response.status_code, 200)
        files = self._read_bundle(response)
        lines = list(csv.DictReader(io.StringIO(files["accounting_invoice_lines.csv"])))
        self.assertEqual(len(lines), 3)
        self.assertTrue(all(row["item"] == "Order summary" for row in lines))
        self.assertTrue(all(row["amount"] == "100.00" for row in lines))

    def test_fallback_uses_positive_total_when_subtotal_is_not_positive(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        conn = db.get_connection()
        conn.execute(
            """
            INSERT INTO orders
            (customer_name, customer_contact, status, payload_json, subtotal, tax, total)
            VALUES ('Total Fallback', '555-010-0777', 'invoice', '{bad-json', 0, 0, 42.40)
            """
        )
        conn.commit()
        conn.close()

        response = self.client.get("/api/accounting/export.zip")

        self.assertEqual(response.status_code, 200)
        files = self._read_bundle(response)
        lines = list(csv.DictReader(io.StringIO(files["accounting_invoice_lines.csv"])))
        self.assertEqual(lines[0]["amount"], "42.40")

    def test_duplicate_customer_names_link_by_matching_contact_details(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        conn = db.get_connection()
        first = conn.execute(
            """
            INSERT INTO customers (name, contact, customer_email, notes)
            VALUES ('Sam Lee', '555-010-1001', 'sam.one@example.test', 'First Sam')
            """
        ).lastrowid
        second = conn.execute(
            """
            INSERT INTO customers (name, contact, customer_email, notes)
            VALUES ('Sam Lee', '555-010-1002', 'sam.two@example.test', 'Second Sam')
            """
        ).lastrowid
        conn.execute(
            """
            INSERT INTO orders
            (customer_name, customer_contact, customer_email, status, payload_json, subtotal, tax, total)
            VALUES (
                'Sam Lee', '555-010-1002', 'sam.two@example.test', 'invoice',
                '{"line_items":{"labor":20}}', 20, 1.20, 21.20
            )
            """
        )
        conn.commit()
        conn.close()

        response = self.client.get("/api/accounting/export.zip")

        self.assertEqual(response.status_code, 200)
        files = self._read_bundle(response)
        invoices = list(csv.DictReader(io.StringIO(files["accounting_invoices.csv"])))
        self.assertEqual(invoices[0]["customer_id"], f"CUST-{second:06d}")
        self.assertNotEqual(invoices[0]["customer_id"], f"CUST-{first:06d}")

    def test_orphan_order_customer_id_is_stable_after_contact_edits(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        conn = db.get_connection()
        order_id = conn.execute(
            """
            INSERT INTO orders
            (customer_name, customer_contact, customer_email, status, payload_json, subtotal, tax, total)
            VALUES (
                'Orphan Customer', '555-010-2001', 'before@example.test', 'invoice',
                '{"line_items":{"labor":20}}', 20, 1.20, 21.20
            )
            """
        ).lastrowid
        conn.commit()
        conn.close()

        first_response = self.client.get("/api/accounting/export.zip")
        first_files = self._read_bundle(first_response)
        first_invoice = next(csv.DictReader(io.StringIO(first_files["accounting_invoices.csv"])))

        conn = db.get_connection()
        conn.execute(
            "UPDATE orders SET customer_contact = ?, customer_email = ? WHERE id = ?",
            ("555-010-2999", "after@example.test", order_id),
        )
        conn.commit()
        conn.close()

        second_response = self.client.get("/api/accounting/export.zip")
        second_files = self._read_bundle(second_response)
        second_invoice = next(csv.DictReader(io.StringIO(second_files["accounting_invoices.csv"])))

        self.assertEqual(first_invoice["customer_id"], second_invoice["customer_id"])
        self.assertEqual(first_invoice["customer_id"], f"CUST-ORDER-{order_id:06d}")

    def test_line_tax_rounding_reconciles_to_invoice_tax(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        conn = db.get_connection()
        conn.execute(
            """
            INSERT INTO orders
            (customer_name, customer_contact, status, payload_json, subtotal, tax, total)
            VALUES (
                'Tax Rounding', '555-010-3001', 'invoice',
                '{"line_items":{"one":0.05,"two":0.05}}', 0.10, 0.01, 0.11
            )
            """
        )
        conn.commit()
        conn.close()

        response = self.client.get("/api/accounting/export.zip")

        self.assertEqual(response.status_code, 200)
        files = self._read_bundle(response)
        lines = list(csv.DictReader(io.StringIO(files["accounting_invoice_lines.csv"])))
        self.assertEqual(sum(Decimal(row["tax"]) for row in lines), Decimal("0.01"))

    def test_concurrent_exports_each_return_a_complete_bundle(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        barrier = threading.Barrier(2)

        def export_once() -> bytes:
            with TestClient(app) as client:
                barrier.wait()
                response = client.get("/api/accounting/export.zip")
                self.assertEqual(response.status_code, 200)
                return response.content

        with ThreadPoolExecutor(max_workers=2) as executor:
            bundles = list(executor.map(lambda _: export_once(), range(2)))

        for bundle in bundles:
            with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
                self.assertEqual(set(archive.namelist()), EXPECTED_FILES)

    def test_concurrent_export_generation_is_serialized(self):
        active = 0
        max_active = 0
        counter_lock = threading.Lock()
        original_load_rows = accounting_export._load_rows

        def tracked_load_rows(conn):
            nonlocal active, max_active
            with counter_lock:
                active += 1
                max_active = max(max_active, active)
            try:
                time.sleep(0.05)
                return original_load_rows(conn)
            finally:
                with counter_lock:
                    active -= 1

        def generate_once(_):
            conn = db.get_connection()
            try:
                return accounting_export.generate_accounting_export(conn, main_module.EXPORT_DIR)
            finally:
                conn.close()

        with patch.object(accounting_export, "_load_rows", side_effect=tracked_load_rows):
            with ThreadPoolExecutor(max_workers=2) as executor:
                list(executor.map(generate_once, range(2)))

        self.assertEqual(max_active, 1)

    def test_export_reads_customers_and_orders_in_one_snapshot_transaction(self):
        statements: list[str] = []
        conn = db.get_connection()
        conn.set_trace_callback(statements.append)
        try:
            accounting_export.generate_accounting_export(conn, main_module.EXPORT_DIR)
        finally:
            conn.close()

        normalized = [statement.strip().upper() for statement in statements]
        begin_index = normalized.index("BEGIN")
        customer_index = next(
            index for index, statement in enumerate(normalized) if "FROM CUSTOMERS" in statement
        )
        order_index = next(
            index for index, statement in enumerate(normalized) if "FROM ORDERS" in statement
        )
        rollback_index = normalized.index("ROLLBACK")
        self.assertLess(begin_index, customer_index)
        self.assertLess(customer_index, order_index)
        self.assertLess(order_index, rollback_index)

    def test_export_rejects_symlinked_export_root(self):
        real_root = Path(self.tempdir.name) / "real-exports"
        real_root.mkdir()
        linked_root = Path(self.tempdir.name) / "linked-exports"
        linked_root.symlink_to(real_root, target_is_directory=True)
        conn = db.get_connection()
        try:
            with self.assertRaisesRegex(ValueError, "symlink"):
                accounting_export.generate_accounting_export(conn, linked_root)
        finally:
            conn.close()
        self.assertEqual(list(real_root.iterdir()), [])

    def test_failed_publication_restores_previous_complete_export(self):
        conn = db.get_connection()
        try:
            accounting_export.generate_accounting_export(conn, main_module.EXPORT_DIR)
        finally:
            conn.close()
        output_dir = main_module.EXPORT_DIR / "accounting"
        baseline = {
            path.name: path.read_bytes()
            for path in output_dir.iterdir()
            if path.is_file()
        }

        conn = db.get_connection()
        conn.execute(
            """
            INSERT INTO orders
            (customer_name, customer_contact, status, payload_json, subtotal, tax, total)
            VALUES ('Publication Failure', '555-010-4001', 'invoice',
                    '{"line_items":{"labor":20}}', 20, 1.20, 21.20)
            """
        )
        conn.commit()
        conn.close()

        original_replace = accounting_export.os.replace
        publication_count = 0

        def fail_second_publication(source, destination):
            nonlocal publication_count
            destination_path = Path(destination)
            if destination_path.parent == output_dir and not destination_path.name.startswith(".previous-"):
                publication_count += 1
                if publication_count == 2:
                    raise OSError("simulated publication failure")
            return original_replace(source, destination)

        conn = db.get_connection()
        try:
            with patch.object(accounting_export.os, "replace", side_effect=fail_second_publication):
                with self.assertRaisesRegex(OSError, "simulated publication failure"):
                    accounting_export.generate_accounting_export(conn, main_module.EXPORT_DIR)
        finally:
            conn.close()

        restored = {
            path.name: path.read_bytes()
            for path in output_dir.iterdir()
            if path.is_file()
        }
        self.assertEqual(restored, baseline)

    def test_existing_order_exports_remain_unchanged(self):
        os.environ["FRAMERSHAVEN_EDITION"] = "workstation"
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Existing Export",
                "customer_contact": "555-010-0444",
                "payload_json": json.dumps({"line_items": {"labor": 20}}),
                "subtotal": "20",
                "tax": "1.20",
                "total": "21.20",
            },
        )
        order_id = created.json()["order_id"]

        order_pdf = self.client.get(f"/api/orders/{order_id}/export", params={"format": "pdf"})
        unsupported_csv = self.client.get(f"/api/orders/{order_id}/export", params={"format": "csv"})

        self.assertEqual(order_pdf.status_code, 200)
        self.assertEqual(unsupported_csv.status_code, 400)


if __name__ == "__main__":
    unittest.main()
