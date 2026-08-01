import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_paths_keep_all_mutable_data_under_one_root():
    from app.runtime_paths import build_runtime_paths

    with tempfile.TemporaryDirectory() as tmp:
        paths = build_runtime_paths({"FRAMERSHAVEN_DATA_DIR": tmp})

        assert paths.database == Path(tmp).resolve() / "studio.db"
        assert paths.uploads == paths.data_root / "uploads"
        assert paths.exports == paths.data_root / "exports"
        assert paths.backups == paths.data_root / "backups"
        assert paths.catalog_previews == paths.data_root / "catalog_previews"
        assert paths.catalog_imports == paths.data_root / "catalog_imports"


def test_legacy_installer_data_moves_without_touching_program_files():
    from framershaven_launcher import migrate_legacy_data

    with tempfile.TemporaryDirectory() as tmp:
        local_app_data = Path(tmp)
        legacy = local_app_data / "FramersHaven"
        target = legacy / "Data"
        legacy.mkdir()
        (legacy / "studio.db").write_bytes(b"customer-data")
        (legacy / "uploads").mkdir()
        (legacy / "uploads" / "art.jpg").write_bytes(b"art")
        (legacy / "run_windows.bat").write_text("old program", encoding="utf-8")

        moved = migrate_legacy_data(local_app_data, target)

        assert set(moved) == {"studio.db", "uploads"}
        assert (target / "studio.db").read_bytes() == b"customer-data"
        assert (target / "uploads" / "art.jpg").read_bytes() == b"art"
        assert (legacy / "run_windows.bat").read_text(encoding="utf-8") == "old program"


def test_existing_new_database_prevents_legacy_overwrite():
    from framershaven_launcher import migrate_legacy_data

    with tempfile.TemporaryDirectory() as tmp:
        local_app_data = Path(tmp)
        legacy = local_app_data / "FramersHaven"
        target = legacy / "Data"
        target.mkdir(parents=True)
        (legacy / "studio.db").write_bytes(b"legacy")
        (target / "studio.db").write_bytes(b"current")

        assert migrate_legacy_data(local_app_data, target) == []
        assert (target / "studio.db").read_bytes() == b"current"
        assert (legacy / "studio.db").read_bytes() == b"legacy"


def test_bundled_demo_previews_copy_only_when_missing():
    from app.runtime_paths import build_runtime_paths, install_bundled_demo_previews

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundled = root / "bundle"
        data = root / "data"
        source = bundled / "mouldings" / "demo-frame.jpg"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"bundled")
        target = data / "catalog_previews" / "mouldings" / source.name
        target.parent.mkdir(parents=True)
        target.write_bytes(b"operator-version")

        copied = install_bundled_demo_previews(
            build_runtime_paths({"FRAMERSHAVEN_DATA_DIR": str(data)}),
            bundled,
        )

        assert copied == 0
        assert target.read_bytes() == b"operator-version"


def test_installer_is_per_user_and_keeps_data_outside_program_files():
    installer = (ROOT / "packaging" / "windows" / "FramersHaven.iss").read_text(encoding="utf-8")

    assert "PrivilegesRequired=lowest" in installer
    assert r"DefaultDirName={localappdata}\Programs\FramersHaven" in installer
    assert r"{app}\Data" not in installer
    assert "CloseApplications=yes" in installer


def test_pyinstaller_bundle_contains_current_app_assets():
    spec = (ROOT / "packaging" / "windows" / "FramersHaven.spec").read_text(encoding="utf-8")

    assert "app/templates" in spec
    assert "app/static" in spec
    assert "catalog_previews" in spec
    assert "VERSION" in spec
    assert "collect_all" in spec


def test_windows_ci_exercises_the_installed_application_lifecycle():
    workflow = (ROOT / ".github" / "workflows" / "windows-installer.yml").read_text(encoding="utf-8")

    assert "runs-on: windows-latest" in workflow
    assert "FramersHaven.exe --smoke-test" in workflow
    assert "FramersHaven-Setup.exe" in workflow
    assert "upgrade-preservation-test.txt" in workflow
    assert "windows-installer" in workflow
