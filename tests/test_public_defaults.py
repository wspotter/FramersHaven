import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import db
from app.auth import normalize_login_identifier
from app.db_admin import init_admin_tables


class PublicDefaultTests(unittest.TestCase):
    def test_fresh_workspace_uses_fictional_framershaven_identity(self):
        original_db_path = db.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as tmp:
                db.DB_PATH = Path(tmp) / "studio.db"
                with patch.dict(
                    os.environ,
                    {
                        "FRAMERSHAVEN_BOOTSTRAP_EMAIL": "",
                        "FRAMERSHAVEN_BOOTSTRAP_PASSWORD": "",
                    },
                    clear=False,
                ):
                    db.init_db()
                    init_admin_tables()

                conn = sqlite3.connect(db.DB_PATH)
                owner = conn.execute(
                    "SELECT email, first_name, last_name FROM users ORDER BY id LIMIT 1"
                ).fetchone()
                company = conn.execute(
                    "SELECT company, address, city, state, zip, phone FROM business_info ORDER BY id LIMIT 1"
                ).fetchone()
                conn.close()

                self.assertEqual(owner, ("admin@framershaven.local", "Studio", "Owner"))
                self.assertEqual(company, ("FramersHaven", "", "", "", "", ""))
        finally:
            db.DB_PATH = original_db_path

    def test_short_admin_login_resolves_to_public_default_domain(self):
        self.assertEqual(normalize_login_identifier("admin"), "admin@framershaven.local")


if __name__ == "__main__":
    unittest.main()
