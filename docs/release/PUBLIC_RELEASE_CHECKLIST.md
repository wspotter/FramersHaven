# Public Release Checklist

Use this checklist before tagging or announcing a public FramersHaven build.

## Required Before Tagging

- [ ] Fresh clone installs from `requirements-dev.txt`.
- [ ] `python scripts/seed_demo.py` creates fictional demo data only.
- [ ] JavaScript syntax and unit tests pass.
- [ ] Python compile and pytest pass.
- [ ] `npm audit --audit-level=high` passes from `app/`.
- [ ] Browser smoke test passes against a running demo app.
- [ ] Windows launcher starts from `run_windows.bat` on a Windows workstation.
- [ ] Help screenshots regenerate from the current demo app.
- [ ] Private footprint scan returns no old names, private paths, copied support links, or customer data.
- [ ] Runtime data remains ignored: `studio.db`, `uploads/`, `exports/`, `backups/`, `catalog_previews/`, `catalog_imports/`, `venv/`.

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
