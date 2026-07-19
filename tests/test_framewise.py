from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

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
        self.assertIn('id="framewiseSubjectPrompt"', home.text)
        self.assertIn("Suggest Looks", home.text)
        self.assertIn("/api/framewise/config", home.text)
        self.assertNotIn("Ask Ollie", home.text)

    def test_framewise_design_ideas_use_local_catalog_when_provider_is_off(self):
        self.client.post(
            "/api/catalog/import",
            files={
                "file": (
                    "catalog.csv",
                    (
                        "sku,name,category,cost,width_in,vendor\n"
                        "F1,Walnut Gallery,moulding,12,1.5,Demo Vendor\n"
                        "F2,Black Cube,moulding,10,1.25,Demo Vendor\n"
                        "F3,Maple Soft,moulding,9,1.75,Demo Vendor\n"
                        "M1,Warm White,mat,4,0,Demo Vendor\n"
                        "M2,Charcoal,mat,4,0,Demo Vendor\n"
                        "M3,Sage,mat,4,0,Demo Vendor\n"
                    ),
                    "text/csv",
                )
            },
        )

        response = self.client.post(
            "/api/framewise/design-ideas",
            json={
                "subject": "African safari photograph with warm grasses and blue sky",
                "goal": "Give the customer three options before building one.",
                "quote_context": {"width_in": 11, "height_in": 14},
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "local-starter")
        self.assertEqual(len(payload["suggestions"]), 3)
        first = payload["suggestions"][0]
        self.assertEqual(first["selections"]["moulding"]["sku"], "F1")
        self.assertEqual(first["selections"]["top_mat"]["sku"], "M1")
        self.assertIn("conversation_tip", first)
        self.assertNotIn("Ollie", str(payload))
        self.assertNotIn("Printery", str(payload))

    @patch("httpx.AsyncClient.post")
    def test_framewise_design_ideas_can_use_provider_wording_with_catalog_ids(self, mocked_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": '{"suggestions":[{"title":"Museum Calm","summary":"Soft and formal.","why":"Balances the subject.","conversation_tip":"Start here."}]}'
                            }
                        }
                    ]
                }

        mocked_post.return_value = FakeResponse()
        self.client.post(
            "/api/catalog/import",
            files={
                "file": (
                    "catalog.csv",
                    "sku,name,category,cost,width_in\nF1,Frame One,moulding,12,1.5\nM1,Mat One,mat,4,0\n",
                    "text/csv",
                )
            },
        )
        self.client.post(
            "/api/framewise/config",
            data={
                "enabled": "on",
                "assistant_name": "Framewise",
                "provider_type": "ollama",
                "base_url": "http://127.0.0.1:11434/v1",
                "model": "llama3.2:3b",
                "context_tokens": "4096",
                "temperature": "0.35",
            },
        )

        response = self.client.post("/api/framewise/design-ideas", json={"subject": "portrait"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "provider-guided")
        self.assertEqual(payload["suggestions"][0]["title"], "Museum Calm")
        self.assertEqual(payload["suggestions"][0]["selections"]["moulding"]["sku"], "F1")

    @patch("httpx.AsyncClient.post")
    def test_framewise_design_ideas_send_selected_image_to_vision_provider(self, mocked_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"visual_analysis":{"summary":"Warm sunset safari image.",'
                                    '"dominant_colors":["gold","sky blue","umber"],'
                                    '"temperature":"warm","contrast":"medium","style":"photograph",'
                                    '"framing_notes":["Use warm neutrals."]},'
                                    '"suggestions":[{"title":"Sunset Lodge","summary":"Warm and refined.",'
                                    '"why":"Echoes the grasses.","conversation_tip":"Show this first."}]}'
                                )
                            }
                        }
                    ]
                }

        mocked_post.return_value = FakeResponse()
        self.client.post(
            "/api/catalog/import",
            files={
                "file": (
                    "catalog.csv",
                    "sku,name,category,cost,width_in\nF1,Walnut,moulding,12,1.5\nM1,Warm White,mat,4,0\n",
                    "text/csv",
                )
            },
        )
        image_bytes = io.BytesIO()
        Image.new("RGB", (120, 80), "#c99a4a").save(image_bytes, format="PNG")
        uploaded = self.client.post(
            "/api/images/upload",
            data={"width_in": "12", "height_in": "8", "ratio_label": "3:2", "crop_json": "{}"},
            files={"file": ("safari.png", image_bytes.getvalue(), "image/png")},
        )
        self.assertEqual(uploaded.status_code, 200)
        image_id = uploaded.json()["id"]
        self.client.post(
            "/api/framewise/config",
            data={
                "enabled": "on",
                "assistant_name": "Framewise",
                "provider_type": "ollama",
                "base_url": "http://127.0.0.1:11434/v1",
                "model": "smolvlm2:2.2b",
                "context_tokens": "4096",
                "temperature": "0.1",
            },
        )

        response = self.client.post(
            "/api/framewise/design-ideas",
            json={"subject": "safari photo", "image_id": image_id},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "vision-guided")
        self.assertTrue(payload["image"]["available"])
        self.assertEqual(payload["visual_analysis"]["source"], "vision-model")
        self.assertEqual(payload["visual_analysis"]["dominant_colors"], ["gold", "sky blue", "umber"])
        request_payload = mocked_post.await_args.kwargs["json"]
        content = request_payload["messages"][1]["content"]
        self.assertIsInstance(content, list)
        self.assertEqual(content[1]["type"], "image_url")
        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))


if __name__ == "__main__":
    unittest.main()
