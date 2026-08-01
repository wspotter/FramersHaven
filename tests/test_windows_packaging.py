import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsPackagingContractTests(unittest.TestCase):
    def test_installer_is_per_user_and_preserves_customer_data(self):
        installer = (ROOT / "packaging" / "windows" / "FramersHaven.iss").read_text(encoding="utf-8")

        self.assertIn("PrivilegesRequired=lowest", installer)
        self.assertIn(r"DefaultDirName={localappdata}\Programs\FramersHaven", installer)
        self.assertNotIn(r"{app}\Data", installer)
        self.assertIn("CloseApplications=yes", installer)

    def test_pyinstaller_bundle_contains_web_assets(self):
        spec = (ROOT / "packaging" / "windows" / "FramersHaven.spec").read_text(encoding="utf-8")

        self.assertIn("app/templates", spec)
        self.assertIn("app/static", spec)
        self.assertIn("collect_all", spec)

    def test_windows_ci_smoke_tests_the_bundled_executable_and_installer(self):
        workflow = (ROOT / ".github" / "workflows" / "windows-installer.yml").read_text(encoding="utf-8")

        self.assertIn("runs-on: windows-latest", workflow)
        self.assertIn("FramersHaven.exe --smoke-test", workflow)
        self.assertIn("FramersHaven-Setup.exe", workflow)
        self.assertIn("windows-installer", workflow)


if __name__ == "__main__":
    unittest.main()
