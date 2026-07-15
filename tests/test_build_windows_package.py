from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import build_windows_package


class WindowsPackageContentsTests(unittest.TestCase):
    def test_installer_is_a_required_package_file(self):
        self.assertIn("install_windows.ps1", build_windows_package.INCLUDE_FILES)

    def test_archive_contains_exactly_the_three_curated_catalog_previews(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "repo"
            output = Path(tempdir) / "dist"
            for dirname in build_windows_package.INCLUDE_DIRS:
                (root / dirname).mkdir(parents=True)
            for filename in build_windows_package.INCLUDE_FILES:
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"fixture for {filename}\n", encoding="utf-8")

            previews = root / "catalog_previews" / "mouldings"
            previews.mkdir(parents=True)
            curated = {
                "demo-black-tall-cap.jpg",
                "demo-dark-walnut-panel.jpg",
                "demo-gold-tall-cap.jpg",
            }
            for filename in curated | {"real-vendor-fourth-preview.jpg"}:
                (previews / filename).write_bytes(filename.encode("ascii"))

            with (
                patch.object(build_windows_package, "ROOT", root),
                patch(
                    "sys.argv",
                    [
                        "build_windows_package.py",
                        "--version",
                        "v-test",
                        "--output",
                        str(output),
                    ],
                ),
            ):
                self.assertEqual(build_windows_package.main(), 0)

            archive = output / "FramersHaven-windows-preview-v-test.zip"
            with zipfile.ZipFile(archive) as package:
                packaged_previews = {
                    name
                    for name in package.namelist()
                    if name.startswith("catalog_previews/")
                }
            self.assertEqual(
                packaged_previews,
                {f"catalog_previews/mouldings/{filename}" for filename in curated},
            )

    def test_staging_validation_rejects_a_fourth_catalog_preview(self):
        with tempfile.TemporaryDirectory() as tempdir:
            staging = Path(tempdir)
            preview_dir = staging / "catalog_previews" / "mouldings"
            preview_dir.mkdir(parents=True)
            for relative in (
                "demo-black-tall-cap.jpg",
                "demo-dark-walnut-panel.jpg",
                "demo-gold-tall-cap.jpg",
                "real-vendor-fourth-preview.jpg",
            ):
                (preview_dir / relative).write_bytes(b"preview")

            self.assertFalse(build_windows_package.validate_no_forbidden(staging))


class WindowsPackageVersionTests(unittest.TestCase):
    def test_reads_default_version_from_version_file(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "VERSION").write_text("0.2.0-rc1\n", encoding="utf-8")
            with patch.object(build_windows_package, "ROOT", root):
                self.assertEqual(build_windows_package.read_version(), "0.2.0-rc1")

    def test_default_zip_name_uses_version_file(self):
        with patch.object(build_windows_package, "read_version", return_value="0.2.0-rc1"):
            self.assertEqual(
                build_windows_package.get_zip_name(None),
                "FramersHaven-windows-preview-v0.2.0-rc1.zip",
            )


if __name__ == "__main__":
    unittest.main()
