from __future__ import annotations

import os
import unittest

from app.edition import get_edition, get_edition_info
from fastapi.testclient import TestClient

from app.main import app


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
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
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


if __name__ == "__main__":
    unittest.main()
