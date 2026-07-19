import sqlite3
import tempfile
import unittest
import json
from pathlib import Path

from PIL import Image

from scripts.seed_demo import ROOT, create_demo_data


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
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM catalog_items WHERE category = 'moulding'").fetchone()[0], 50)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM catalog_items WHERE category = 'mat'").fetchone()[0], 50)
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

    def test_seed_links_the_public_demo_moulding_preview_samples(self):
        create_demo_data(self.db_path, self.upload_dir)

        conn = sqlite3.connect(self.db_path)
        previews = dict(conn.execute("SELECT sku, preview_filename FROM catalog_items WHERE category = 'moulding'"))
        conn.close()

        self.assertEqual(len(previews), 50)
        self.assertTrue(all(filename.startswith("mouldings/demo-") for filename in previews.values()))
        for preview_filename in previews.values():
            self.assertTrue((ROOT / "catalog_previews" / preview_filename).is_file())

    def test_primary_demo_art_centers_the_oval_horizontally(self):
        create_demo_data(self.db_path, self.upload_dir)

        with Image.open(self.upload_dir / "demo-art-1.png") as image:
            cream_pixels = [
                (x, y)
                for y in range(image.height)
                for x in range(image.width)
                if image.getpixel((x, y)) == (244, 236, 219)
            ]

        left = min(x for x, _ in cream_pixels)
        right = max(x for x, _ in cream_pixels)
        self.assertAlmostEqual((left + right) / 2, image.width / 2, delta=1)


if __name__ == "__main__":
    unittest.main()
