from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import db
from app import main as main_module
from app.main import app


class FramewiseTests(unittest.TestCase):
    def setUp(self):
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

    def test_framewise_defaults_are_public_local_and_disabled(self):
        response = self.client.get("/api/framewise/config")
        self.assertEqual(response.status_code, 200)
        config = response.json()["config"]
        self.assertFalse(config["enabled"])
        self.assertEqual(config["assistant_name"], "Framewise")
        self.assertEqual(config["provider_type"], "ollama")
        self.assertEqual(config["base_url"], "http://127.0.0.1:11434/v1")
        self.assertEqual(config["model"], "llama3.2:3b")
        self.assertNotIn("Ollie", str(config))
        self.assertNotIn("Printery", str(config))

    def test_framewise_config_round_trips_without_exposing_api_key(self):
        saved = self.client.post(
            "/api/framewise/config",
            data={
                "enabled": "on",
                "assistant_name": "Framewise",
                "provider_type": "openai-compatible",
                "base_url": "http://127.0.0.1:1234/v1",
                "model": "qwen2.5:3b-instruct",
                "api_key": "secret-test-key",
                "context_tokens": "8192",
                "temperature": "0.35",
            },
        )
        self.assertEqual(saved.status_code, 200)
        config = saved.json()["config"]
        self.assertTrue(config["enabled"])
        self.assertTrue(config["api_key_present"])
        self.assertNotIn("secret-test-key", str(config))

        loaded = self.client.get("/api/framewise/config").json()["config"]
        self.assertEqual(loaded["model"], "qwen2.5:3b-instruct")
        self.assertTrue(loaded["api_key_present"])
        self.assertNotIn("secret-test-key", str(loaded))

    def test_framewise_status_reports_disabled_without_network_call(self):
        with patch("httpx.AsyncClient.get") as mocked_get:
            response = self.client.get("/api/framewise/status")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["available"])
        mocked_get.assert_not_called()

    def test_framewise_admin_controls_are_on_homepage(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn("Framewise Assistant", home.text)
        self.assertIn('id="framewiseProviderType"', home.text)
        self.assertIn("/api/framewise/config", home.text)
        self.assertNotIn("Ask Ollie", home.text)


if __name__ == "__main__":
    unittest.main()
