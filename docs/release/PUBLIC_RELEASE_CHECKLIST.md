# Public Release Checklist

Use this checklist before tagging or announcing a public FramersHaven build.

Current release-candidate evidence is recorded in `V0.2.0_RC1_VALIDATION_REPORT.md`.

## Required Before Tagging

- [ ] Fresh clone installs from `requirements-dev.txt`.
- [ ] `python scripts/seed_demo.py` creates fictional demo data only.
- [ ] JavaScript syntax and unit tests pass.
- [ ] Python compile and pytest pass.
- [ ] `npm audit --audit-level=high` passes from `app/`.
- [ ] Browser smoke test passes explicitly in Community and Workstation modes.
- [ ] Windows launcher starts from `run_windows.bat` on a Windows workstation.
- [ ] Windows preview ZIP is built and validated using `docs/release/WINDOWS_PACKAGE_BUILD_PLAN.md`.
- [ ] Help screenshots regenerate from the current demo app.
- [ ] Private footprint scan returns no old names, private paths, copied support links, or customer data.
- [ ] Runtime data remains ignored: `studio.db`, `uploads/`, `exports/`, `backups/`, `catalog_previews/`, `catalog_imports/`, `venv/`.

## Commercialization Wording Review

- [ ] README edition wording is factual, local-first, and not hard-selling.
- [ ] User manual explains Community and Workstation without implying hosted service, accounting sync, or included vendor data.
- [ ] Implemented accounting CSV schema and generated sample files are reviewed before release.
- [ ] Help copy for accounting export explains local CSV generation only.
- [ ] Sales page copy variants and pricing FAQ are reviewed by a human before publication.
- [ ] Windows package copy includes a start-here note and excludes runtime/private data.
- [ ] Private footprint scan checks for competitor names, catalog vendor names, private shop names, real customer data, and real catalog data.

## Manual Review

- [ ] README renders correctly on GitHub.
- [ ] Logo and screenshots load on GitHub.
- [ ] License stance is still intentional.
- [ ] No marketing claims imply hosted, secure, or internet-ready service.
- [ ] SECURITY.md still describes trusted workstation/LAN use.

## Release Commands

```bash
git clone git@github.com:wspotter/FramersHaven.git /tmp/FramersHaven-release-test
cd /tmp/FramersHaven-release-test
python3 -m venv venv
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python scripts/seed_demo.py
node -c app/static/app.js
node --test app/src/*.test.js
./venv/bin/python -m compileall -q app tests scripts
./venv/bin/python -m pytest -q tests
(cd app && npm audit --audit-level=high)
```
