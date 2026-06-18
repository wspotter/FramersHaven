# Windows Test Report Template

Use this template when validating the Windows launcher on a real workstation. Fill in every section before treating the release candidate as Windows-ready.

This report is required for the Windows ZIP/folder release candidate.

## Test Environment

- Test date:
- Windows version (edition, build, and architecture):
- Python version:
- Git version (if cloning):
- FramersHaven source (branch, commit, or ZIP identifier):
- Package path on disk:

## Package Contents

- [ ] Source files present.
- [ ] `run_windows.bat` present.
- [ ] `requirements.txt` and `requirements-dev.txt` present.
- [ ] `START_HERE_WINDOWS.txt` present (if added).
- [ ] `.git`, `venv`, `studio.db`, `uploads`, `exports`, `backups`, `catalog_previews`, `catalog_imports` excluded.
- [ ] No real customer data, vendor catalogs, credentials, or private paths present.

## Startup Test

- [ ] Fresh clone or clean unzip starts from `run_windows.bat`.
- [ ] Virtual environment created if missing.
- [ ] Dependencies installed.
- [ ] Demo data created if `studio.db` did not exist.
- [ ] App starts and opens `http://127.0.0.1:8000` in the default browser.
- [ ] `GET /api/health` returns `{ "status": "ok" }`.

## Demo Data Check

- [ ] Only fictional demo data is present.
- [ ] No real customer names, vendor names, or private shop names.
- [ ] No real catalog data or credentials.

## Functional Smoke

- [ ] Design workspace loads.
- [ ] Gallery intake loads.
- [ ] Orders / Quotes workspace loads.
- [ ] Customer workspace loads.
- [ ] Admin workspace loads.
- [ ] Help pages load under `/help/`.
- [ ] A quote can be calculated and saved in the default seeded state.

## Close/Reopen Test

- [ ] Stop the app with `Ctrl-C`.
- [ ] Restart with `run_windows.bat`.
- [ ] Existing `studio.db` is preserved and not overwritten.
- [ ] Saved demo data is still present after restart.

## LAN Test (Optional)

- [ ] Set `HOST=0.0.0.0` and restart.
- [ ] Another computer on the same trusted private LAN can open `http://WORKSTATION-IP:8000`.
- [ ] Do not expose the app to the public internet.

## Issues

| # | Summary | Severity | Repro steps | Resolution |
|---|---------|----------|-------------|------------|
|   |         |          |             |            |

## Screenshots

Attach screenshots for:

- Successful startup browser window.
- Each workspace after launch.
- Any error or unexpected behavior.

## Reviewer

- Reviewer name:
- Reviewer role:
- Verdict (pass / pass with notes / fail):
- Notes:
