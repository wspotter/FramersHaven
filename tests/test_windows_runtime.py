import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class RuntimePathTests(unittest.TestCase):
    def test_explicit_data_root_keeps_all_mutable_files_together(self):
        from app.runtime_paths import build_runtime_paths

        with tempfile.TemporaryDirectory() as tmp:
            paths = build_runtime_paths({"FRAMERSHAVEN_DATA_DIR": tmp})

            self.assertEqual(paths.data_root, Path(tmp).resolve())
            self.assertEqual(paths.database, paths.data_root / "studio.db")
            self.assertEqual(paths.uploads, paths.data_root / "uploads")
            self.assertEqual(paths.exports, paths.data_root / "exports")
            self.assertEqual(paths.backups, paths.data_root / "backups")
            self.assertEqual(paths.catalog_previews, paths.data_root / "catalog_previews")
            self.assertEqual(paths.pfd, paths.data_root / "pfd")

    def test_runtime_directory_creation_does_not_require_program_directory_writes(self):
        from app.runtime_paths import build_runtime_paths

        with tempfile.TemporaryDirectory() as tmp:
            paths = build_runtime_paths({"FRAMERSHAVEN_DATA_DIR": tmp})
            paths.ensure_directories()

            self.assertTrue(paths.uploads.is_dir())
            self.assertTrue(paths.exports.is_dir())
            self.assertTrue(paths.backups.is_dir())
            self.assertTrue(paths.catalog_previews.is_dir())
            self.assertTrue(paths.pfd.is_dir())


class WindowsLauncherTests(unittest.TestCase):
    def test_default_data_directory_uses_local_app_data(self):
        from framershaven_launcher import default_data_dir

        path = default_data_dir({"LOCALAPPDATA": r"C:\Users\Casey\AppData\Local"})

        self.assertEqual(
            path,
            Path(r"C:\Users\Casey\AppData\Local") / "FramersHaven" / "Data",
        )

    def test_explicit_data_directory_wins_over_windows_default(self):
        from framershaven_launcher import default_data_dir

        path = default_data_dir(
            {
                "LOCALAPPDATA": r"C:\Users\Casey\AppData\Local",
                "FRAMERSHAVEN_DATA_DIR": r"D:\FramersHavenData",
            }
        )

        self.assertEqual(path, Path(r"D:\FramersHavenData"))

    def test_session_secret_is_created_once_and_reused(self):
        from framershaven_launcher import ensure_session_secret

        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            first = ensure_session_secret(data_dir)
            second = ensure_session_secret(data_dir)

            self.assertEqual(first, second)
            self.assertGreaterEqual(len(first), 32)
            self.assertEqual((data_dir / ".session-secret").read_text(encoding="utf-8").strip(), first)

    def test_port_selection_skips_an_occupied_port(self):
        from framershaven_launcher import select_available_port

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen(1)
            occupied_port = occupied.getsockname()[1]

            selected = select_available_port(occupied_port, attempts=5)

        self.assertNotEqual(selected, occupied_port)
        self.assertLessEqual(selected, occupied_port + 4)

    def test_running_state_reopens_only_a_verified_framershaven_server(self):
        from framershaven_launcher import find_running_port, write_server_state

        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            write_server_state(data_dir, port=8765, pid=123)

            self.assertEqual(find_running_port(data_dir, probe=lambda port: port == 8765), 8765)

    def test_stale_running_state_is_removed(self):
        from framershaven_launcher import find_running_port, write_server_state

        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            write_server_state(data_dir, port=8765, pid=123)

            self.assertIsNone(find_running_port(data_dir, probe=lambda _port: False))
            self.assertFalse((data_dir / "server.json").exists())

    def test_runtime_environment_points_application_at_durable_data(self):
        from framershaven_launcher import configure_runtime_environment

        with tempfile.TemporaryDirectory() as tmp:
            env = {}
            configure_runtime_environment(Path(tmp), env)

            self.assertEqual(env["FRAMERSHAVEN_DATA_DIR"], str(Path(tmp).resolve()))
            self.assertEqual(env["FRAMERSHAVEN_SESSION_SECRET"], ensure_text(Path(tmp) / ".session-secret"))


def ensure_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


if __name__ == "__main__":
    unittest.main()
