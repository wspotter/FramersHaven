import sqlite3
import tempfile
import unittest
import json
from pathlib import Path

from scripts.seed_demo import create_demo_data


class DemoSeedTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.db_path = self.root / "studio.db"
        self.upload_dir = self.root / "uploads"

    def tearDown(self):
        self.tempdir.cleanup()

    def test_seed_is_repeatable_and_contains_only_fictional_demo_records(self):
        create_demo_data(self.db_path, self.upload_dir)
        create_demo_data(self.db_path, self.upload_dir)

        conn = sqlite3.connect(self.db_path)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0], 4)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 3)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM images").fetchone()[0], 2)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM catalog_items WHERE category = 'moulding'").fetchone()[0], 5)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM catalog_items WHERE category = 'mat'").fetchone()[0], 5)
        self.assertEqual(
            {row[0] for row in conn.execute("SELECT status FROM orders")},
            {"quote", "work_order", "invoice"},
        )
        payload = json.loads(conn.execute("SELECT payload_json FROM orders LIMIT 1").fetchone()[0])
        self.assertIsInstance(payload["line_items"], dict)
        emails = {row[0] for row in conn.execute("SELECT customer_email FROM customers")}
        self.assertTrue(all(email.endswith("@example.test") for email in emails))
        conn.close()
        self.assertTrue((self.upload_dir / "demo-art-1.png").is_file())
        self.assertTrue((self.upload_dir / "demo-art-2.png").is_file())

    def test_seed_refuses_to_replace_an_unmarked_database_without_force(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE private_data (value TEXT)")
        conn.commit()
        conn.close()

        with self.assertRaisesRegex(RuntimeError, "Refusing to overwrite non-demo database"):
            create_demo_data(self.db_path, self.upload_dir)


if __name__ == "__main__":
    unittest.main()
