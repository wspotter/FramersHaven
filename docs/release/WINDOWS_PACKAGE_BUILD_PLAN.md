# Windows Package Build Plan

This plan defines the next release step: create a repeatable Windows-ready ZIP/folder package for early testers. This is not an installer, signed executable, hosted service, or standalone desktop app.

## Goal

- [ ] Build a clean `dist/FramersHaven-windows-preview.zip`.
- [ ] Include the app source, launcher, docs, sample-safe assets, and requirements.
- [ ] Exclude runtime data, private data, local virtual environments, caches, Git metadata, and generated output.
- [ ] Make the ZIP usable by a Windows tester with Python 3.11+ installed.
- [ ] Keep the package local-first and truthful: it starts `run_windows.bat` and opens the browser app.

## Package Name

Release-candidate package name:

```text
FramersHaven-windows-preview-v0.2.0-rc1.zip
```

Tagged packages should include the version:

```text
FramersHaven-windows-preview-v0.2.0-rc1.zip
```

## Include

- [ ] `app/`
- [ ] `docs/`
- [ ] `scripts/`
- [ ] `tests/`
- [ ] `.github/workflows/ci.yml` if publishing source snapshots
- [ ] `README.md`
- [ ] `START_HERE_WINDOWS.txt`
- [ ] `WINDOWS_INSTALL.md` if moved or duplicated at package root later
- [ ] `ARCHITECTURE.md`
- [ ] `CHANGELOG.md`
- [ ] `CONTRIBUTING.md`
- [ ] `LICENSE`
- [ ] `SECURITY.md`
- [ ] `THIRD_PARTY_NOTICES.md`
- [ ] `requirements.txt`
- [ ] `requirements-dev.txt`
- [ ] `run_windows.bat`

## Exclude

- [ ] `.git/`
- [ ] `.venv/`
- [ ] `venv/`
- [ ] `__pycache__/`
- [ ] `.pytest_cache/`
- [ ] `node_modules/`
- [ ] `studio.db`
- [ ] `uploads/`
- [ ] `exports/`
- [ ] `backups/`
- [ ] `catalog_previews/`
- [ ] `catalog_imports/`
- [ ] `dist/`
- [ ] Any `.zip` package already generated
- [ ] Any local logs, screenshots, temp files, or editor state

## Script

Create:

```text
scripts/build_windows_package.py
```

Recommended behavior:

- [ ] Remove and recreate a staging directory under `dist/`.
- [ ] Copy included files into the staging directory.
- [ ] Apply exclude rules while copying.
- [ ] Validate that required files exist in the staging directory.
- [ ] Validate that forbidden runtime paths do not exist in the staging directory.
- [ ] Create the ZIP from the staging directory.
- [ ] Print the ZIP path and file count.
- [ ] Exit non-zero if validation fails.

Suggested command:

```bash
python scripts/build_windows_package.py
```

The script reads `VERSION` and includes it in the default ZIP filename.

Optional flags:

```bash
python scripts/build_windows_package.py --version v0.2.0-rc1
python scripts/build_windows_package.py --output dist
```

## Validation

After building the ZIP:

- [ ] Inspect ZIP contents with `unzip -l`.
- [ ] Confirm `run_windows.bat` is at the package root.
- [ ] Confirm `START_HERE_WINDOWS.txt` is at the package root.
- [ ] Confirm `requirements.txt` is at the package root.
- [ ] Confirm `app/main.py` is present.
- [ ] Confirm help images and logo assets are present.
- [ ] Confirm runtime/private directories are absent.
- [ ] Confirm no database file is present.
- [ ] Confirm no real catalog package or preview cache is present.

Suggested checks:

```bash
python scripts/build_windows_package.py
unzip -l dist/FramersHaven-windows-preview.zip | sed -n '1,160p'
unzip -l dist/FramersHaven-windows-preview.zip | rg '(^|/)(studio\.db|uploads/|exports/|backups/|catalog_previews/|catalog_imports/|venv/|\.venv/|\.git/)'
```

The final command should return no matches.

## Release Smoke

Linux-side smoke before Windows testing:

- [ ] Create a temporary extraction folder.
- [ ] Unzip the package there.
- [ ] Confirm no forbidden runtime files are present.
- [ ] Run Python syntax checks from the extracted folder.
- [ ] Run unit tests if dependencies are installed.

Windows-side smoke:

- [ ] Extract the ZIP on Windows 10 or Windows 11.
- [ ] Double-click `run_windows.bat`.
- [ ] Confirm dependencies install.
- [ ] Confirm fictional demo workspace is created on first launch.
- [ ] Confirm app opens at `http://127.0.0.1:8000`.
- [ ] Confirm help pages load.
- [ ] Confirm a quote can be calculated.
- [ ] Stop with `Ctrl-C`.
- [ ] Restart and confirm `studio.db` is preserved.

Use:

```text
docs/release/WINDOWS_TEST_REPORT_TEMPLATE.md
```

## Public Wording

Allowed:

- [ ] Windows-ready ZIP/folder workflow
- [ ] Local-first browser app
- [ ] Starts with `run_windows.bat`
- [ ] Requires Python 3.11 or newer

Avoid:

- [ ] Windows desktop app
- [ ] Standalone executable
- [ ] Installer
- [ ] Signed app
- [ ] One-click install
- [ ] Auto-updater
- [ ] Secure for public internet use

## Done Definition

- [ ] Package build script committed.
- [ ] Package ZIP generated locally.
- [ ] ZIP contents validated.
- [ ] Local tests still pass.
- [ ] GitHub CI passes.
- [ ] One real Windows test report is filled out before tagging or announcing.
