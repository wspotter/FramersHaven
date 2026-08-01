from __future__ import annotations

import os
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
    pfd: Path

    def ensure_directories(self) -> None:
        self.data_root.mkdir(parents=True, exist_ok=True)
        for directory in (
            self.uploads,
            self.exports,
            self.backups,
            self.catalog_previews,
            self.pfd,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def _normalize_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else path


def build_runtime_paths(env: Mapping[str, str] | None = None) -> RuntimePaths:
    source = os.environ if env is None else env
    configured = str(source.get("FRAMERSHAVEN_DATA_DIR") or "").strip()
    data_root = _normalize_path(configured) if configured else PROJECT_ROOT
    return RuntimePaths(
        data_root=data_root,
        database=data_root / "studio.db",
        uploads=data_root / "uploads",
        exports=data_root / "exports",
        backups=data_root / "backups",
        catalog_previews=data_root / "catalog_previews",
        pfd=data_root / "pfd",
    )


RUNTIME_PATHS = build_runtime_paths()
