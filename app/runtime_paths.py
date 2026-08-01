from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class RuntimePaths:
    data_root: Path
    database: Path
    uploads: Path
    exports: Path
    backups: Path
    catalog_previews: Path
    catalog_imports: Path

    def ensure_directories(self) -> None:
        self.data_root.mkdir(parents=True, exist_ok=True)
        for directory in (
            self.uploads,
            self.exports,
            self.backups,
            self.catalog_previews,
            self.catalog_imports,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def build_runtime_paths(env: Mapping[str, str] | None = None) -> RuntimePaths:
    source = os.environ if env is None else env
    configured = str(source.get("FRAMERSHAVEN_DATA_DIR") or "").strip()
    data_root = Path(configured).expanduser().resolve() if configured else PROJECT_ROOT
    return RuntimePaths(
        data_root=data_root,
        database=data_root / "studio.db",
        uploads=data_root / "uploads",
        exports=data_root / "exports",
        backups=data_root / "backups",
        catalog_previews=data_root / "catalog_previews",
        catalog_imports=data_root / "catalog_imports",
    )


def install_bundled_demo_previews(
    paths: RuntimePaths,
    bundled_root: Path | None = None,
) -> int:
    source_root = bundled_root or PROJECT_ROOT / "catalog_previews"
    try:
        if source_root.resolve() == paths.catalog_previews.resolve():
            return 0
    except OSError:
        pass
    if not source_root.is_dir():
        return 0

    copied = 0
    for source in source_root.rglob("demo-*.jpg"):
        relative = source.relative_to(source_root)
        target = paths.catalog_previews / relative
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    return copied


RUNTIME_PATHS = build_runtime_paths()
