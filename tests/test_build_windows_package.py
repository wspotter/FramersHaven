from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_windows_package


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
