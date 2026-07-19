from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app import db
from app import framewise
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
        self.original_framewise_upload_dir = framewise.UPLOAD_DIR
        framewise.UPLOAD_DIR = main_module.UPLOAD_DIR
        main_module._catalog_preview_basename_index.cache_clear()
        db.init_db()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        main_module.UPLOAD_DIR = self.original_upload_dir
        framewise.UPLOAD_DIR = self.original_framewise_upload_dir
        main_module._catalog_preview_basename_index.cache_clear()
        self.tempdir.cleanup()

    def _reviewed_example_payload(self):
        return {
            "image_id": None,
            "subject": "Warm landscape photograph",
            "goal": "Present a calm, refined framing direction.",
            "source": "vision-guided",
            "visual_analysis": {
                "summary": "Warm landscape with a moderate contrast range.",
                "dominant_colors": ["gold", "blue"],
            },
            "suggestion": {
                "title": "Sunset Walnut",
                "summary": "Warm walnut with a quiet ivory mat.",
                "why": "The restrained contrast keeps attention on the image.",
            },
            "quote_context": {
                "width_in": 12,
                "height_in": 16,
                "customer_name": "Private Customer",
                "customer_email": "customer-private@example.test",
            },
            "applied_snapshot": {
                "moulding": {"sku": "F1", "name": "Walnut"},
                "top_mat": {"sku": "M1", "name": "Warm White"},
                "private_notes": "Sensitive counter note.",
                "api_key": "framewise-example-secret",
            },
        }

    def _save_reviewed_example(self):
        self.client.post(
            "/api/framewise/config",
            data={
                "enabled": "on",
                "assistant_name": "Framewise",
                "provider_type": "openai-compatible",
                "base_url": "http://127.0.0.1:1234/v1",
                "model": "local-test-model",
                "api_key": "framewise-config-secret",
                "context_tokens": "4096",
                "temperature": "0.2",
            },
        )
        return self.client.post("/api/framewise/examples", json=self._reviewed_example_payload())

    def test_framewise_reviewed_example_saves_applied_look_without_private_response_data(self):
        response = self._save_reviewed_example()

        self.assertIn(response.status_code, (200, 201))
        self.assertNotIn("framewise-config-secret", response.text)
        self.assertNotIn("framewise-example-secret", response.text)
        self.assertNotIn("Private Customer", response.text)
        self.assertNotIn("customer-private@example.test", response.text)

        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT subject, applied_snapshot_json FROM framewise_examples ORDER BY id DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["subject"], "Warm landscape photograph")
        self.assertEqual(json.loads(row["applied_snapshot_json"])["moulding"]["sku"], "F1")

    def test_framewise_reviewed_examples_export_as_redacted_jsonl(self):
        saved = self._save_reviewed_example()
        self.assertIn(saved.status_code, (200, 201))

        response = self.client.get("/api/framewise/examples/export")

        self.assertEqual(response.status_code, 200)
        lines = [line for line in response.text.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        exported = json.loads(lines[0])
        self.assertEqual(exported["version"], "framewise-example-v1")
        self.assertEqual(exported["input"]["subject"], "Warm landscape photograph")
        self.assertEqual(exported["output"]["suggestion"]["title"], "Sunset Walnut")
        self.assertEqual(exported["output"]["applied_snapshot"]["moulding"]["sku"], "F1")

        exported_text = response.text
        for private_term in (
            "framewise-config-secret",
            "framewise-example-secret",
            "api_key",
            "customer_name",
            "customer_email",
            "customer-private@example.test",
            "Private Customer",
            "private_notes",
        ):
            self.assertNotIn(private_term, exported_text)

    def test_framewise_defaults_are_public_local_and_disabled(self):
        response = self.client.get("/api/framewise/config")
        self.assertEqual(response.status_code, 200)
        config = response.json()["config"]
        self.assertFalse(config["enabled"])
        self.assertEqual(config["assistant_name"], "Framewise")
        self.assertEqual(config["provider_type"], "ollama")
        self.assertEqual(config["base_url"], "http://127.0.0.1:11434/v1")
        self.assertEqual(config["model"], "hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M")

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
        self.assertIn("SmolVLM2", home.text)
        self.assertIn('id="framewiseSubjectPrompt"', home.text)
        self.assertIn("Suggest Looks", home.text)
        self.assertIn("Extra details or questions", home.text)
        self.assertIn("/api/framewise/config", home.text)

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
    def test_framewise_design_ideas_recovers_nested_small_model_suggestions(self, mocked_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"visual_analysis":{"summary":"Soft warm portrait.",'
                                    '"dominant_colors":["cream","brown"],'
                                    '"temperature":"warm","contrast":"low","style":"photograph",'
                                    '"framing_notes":["Keep it gentle."],'
                                    '"suggestions":[{"title":"Soft Walnut","summary":"Warm and simple.",'
                                    '"why":"Works with the portrait.","conversation_tip":"A safe first option."}]}}'
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

        response = self.client.post("/api/framewise/design-ideas", json={"subject": "portrait"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "provider-guided")
        self.assertEqual(payload["suggestions"][0]["title"], "Soft Walnut")

    @patch("httpx.AsyncClient.post")
    def test_framewise_design_ideas_uses_vision_analysis_even_without_provider_suggestions(self, mocked_post):
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
                                    '"dominant_colors":["gold","sky blue"],'
                                    '"temperature":"warm","contrast":"medium","style":"photograph",'
                                    '"framing_notes":["Use warm neutrals."]}}'
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

        response = self.client.post("/api/framewise/design-ideas", json={"subject": "safari photo", "image_id": image_id})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "vision-guided")
        self.assertEqual(payload["visual_analysis"]["dominant_colors"], ["gold", "sky blue"])
        self.assertEqual(payload["suggestions"][0]["selections"]["moulding"]["sku"], "F1")

    @patch("httpx.AsyncClient.post")
    def test_framewise_design_ideas_recovers_prose_vision_output(self, mocked_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "This appears to be a warm wedding photograph with soft whites and dark formal clothing."
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
                    "sku,name,category,cost,width_in\nF1,Black Frame,moulding,12,1.5\nM1,Warm White,mat,4,0\n",
                    "text/csv",
                )
            },
        )
        image_bytes = io.BytesIO()
        Image.new("RGB", (120, 80), "#ddd0c0").save(image_bytes, format="PNG")
        uploaded = self.client.post(
            "/api/images/upload",
            data={"width_in": "12", "height_in": "8", "ratio_label": "3:2", "crop_json": "{}"},
            files={"file": ("wedding.png", image_bytes.getvalue(), "image/png")},
        )
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

        response = self.client.post("/api/framewise/design-ideas", json={"subject": "wedding photo", "image_id": image_id})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "vision-guided")
        self.assertIn("warm wedding", payload["visual_analysis"]["summary"])
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

    @patch("httpx.AsyncClient.post")
    def test_framewise_design_ideas_resolves_relative_uploaded_image_path(self, mocked_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"visual_analysis":{"summary":"Graphic color study.",'
                                    '"dominant_colors":["teal","rose"],'
                                    '"temperature":"mixed","contrast":"medium","style":"graphic",'
                                    '"framing_notes":["Keep the frame quiet."]},'
                                    '"suggestions":[{"title":"Clean Color Study","summary":"Simple and polished.",'
                                    '"why":"Lets the color lead.","conversation_tip":"A counter-safe first option."}]}'
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
                    "sku,name,category,cost,width_in\nF1,Graphite,moulding,12,1.5\nM1,Warm White,mat,4,0\n",
                    "text/csv",
                )
            },
        )
        image_path = main_module.UPLOAD_DIR / "relative-demo.png"
        Image.new("RGB", (120, 80), "#1fb7a6").save(image_path, format="PNG")
        conn = db.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO images (filename, path, width_in, height_in, ratio_label, crop_json)
                VALUES (?, ?, 12, 8, '3:2', '{}')
                """,
                ("relative-demo.png", "relative-demo.png"),
            )
            image_id = cur.lastrowid
            conn.commit()
        finally:
            conn.close()
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

        response = self.client.post("/api/framewise/design-ideas", json={"subject": "color study", "image_id": image_id})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "vision-guided")
        self.assertTrue(payload["image"]["available"])
        content = mocked_post.await_args.kwargs["json"]["messages"][1]["content"]
        self.assertIsInstance(content, list)
        self.assertEqual(content[1]["type"], "image_url")


if __name__ == "__main__":
    unittest.main()
