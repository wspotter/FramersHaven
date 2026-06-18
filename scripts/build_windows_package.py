#!/usr/bin/env python3
"""Build a Windows-ready ZIP package for FramersHaven."""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
DEFAULT_OUTPUT_DIR = ROOT / "dist"

INCLUDE_DIRS = ["app", "docs", "scripts", "tests"]
INCLUDE_FILES = [
    "VERSION",
    "README.md",
    "START_HERE_WINDOWS.txt",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "requirements.txt",
    "requirements-dev.txt",
    "run_windows.bat",
]

EXCLUDED_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
}

EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".zip", ".log", ".tmp", ".swp", ".swo"}

FORBIDDEN_FILES = {
    "studio.db",
}

FORBIDDEN_DIRS = {
    "uploads",
    "exports",
    "backups",
    "catalog_previews",
    "catalog_imports",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Windows-ready ZIP package")
    parser.add_argument("--version", help="Version string (e.g., v0.1.0)")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR), help="Output directory")
    return parser.parse_args()


def read_version() -> str:
    version_path = ROOT / "VERSION"
    version = version_path.read_text(encoding="utf-8").strip()
    if not version:
        raise RuntimeError(f"Version file is empty: {version_path}")
    return version


def get_zip_name(version: str | None) -> str:
    base = "FramersHaven-windows-preview"
    package_version = version or f"v{read_version()}"
    base = f"{base}-{package_version}"
    return f"{base}.zip"


def validate_required_files(staging_dir: Path) -> bool:
    missing = []
    for name in INCLUDE_FILES:
        if not (staging_dir / name).exists():
            missing.append(name)
    if missing:
        print(f"Missing required files: {', '.join(missing)}", file=sys.stderr)
        return False
    return True


def validate_no_forbidden(staging_dir: Path) -> bool:
    issues: list[str] = []
    forbidden_names = EXCLUDED_NAMES | FORBIDDEN_FILES | FORBIDDEN_DIRS
    for path in staging_dir.rglob("*"):
        relative = path.relative_to(staging_dir).as_posix()
        if path.name in forbidden_names or path.suffix in EXCLUDED_SUFFIXES:
            issues.append(relative)
    if issues:
        print(f"Forbidden files/dirs found in staging: {', '.join(issues)}", file=sys.stderr)
        return False
    return True


def ignore_names(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        path = Path(name)
        if name in EXCLUDED_NAMES or name in FORBIDDEN_FILES or name in FORBIDDEN_DIRS:
            ignored.add(name)
        elif path.suffix in EXCLUDED_SUFFIXES:
            ignored.add(name)
    return ignored


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output)
    zip_name = get_zip_name(args.version)
    zip_path = output_dir / zip_name
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="framershaven-package-") as tempdir:
        staging_dir = Path(tempdir) / "FramersHaven"
        staging_dir.mkdir()
        for dirname in INCLUDE_DIRS:
            src = ROOT / dirname
            dst = staging_dir / dirname
            if src.exists():
                shutil.copytree(src, dst, ignore=ignore_names)

        for filename in INCLUDE_FILES:
            src = ROOT / filename
            dst = staging_dir / filename
            if src.exists():
                shutil.copy2(src, dst)
            else:
                print(f"Warning: {filename} not found, skipping", file=sys.stderr)

        if not validate_required_files(staging_dir):
            return 1

        if not validate_no_forbidden(staging_dir):
            return 1

        zip_path.parent.mkdir(parents=True, exist_ok=True)
        file_count = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in staging_dir.rglob("*"):
                if path.is_file():
                    arcname = path.relative_to(staging_dir).as_posix()
                    zf.write(path, arcname)
                    file_count += 1

        print(f"Created: {zip_path}")
        print(f"File count: {file_count}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
