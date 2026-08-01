# Public Release Checklist

Use this checklist before tagging or announcing a public FramersHaven build.

## Required Before Tagging

- [ ] Fresh clone installs from `requirements-dev.txt`.
- [ ] `python scripts/seed_demo.py` creates fictional demo data only.
- [ ] JavaScript syntax and unit tests pass.
- [ ] Python compile and pytest pass.
- [ ] `npm audit --audit-level=high` passes from `app/`.
- [ ] Browser smoke test passes against a running demo app.
- [ ] Windows workflow builds `FramersHaven-Setup.exe` and its SHA-256 file.
- [ ] Bundled and installed executable smoke tests pass on `windows-latest`.
- [ ] Clean install, in-place upgrade, uninstall data retention, and reinstall pass.
- [ ] A nontechnical tester completes a normal interactive install on clean Windows 10 or 11.
- [ ] Help screenshots regenerate from the current demo app.
- [ ] Private footprint scan returns no old names, private paths, copied support links, or customer data.
- [ ] Runtime data remains ignored: `studio.db`, `uploads/`, `exports/`, `backups/`, `catalog_previews/`, `catalog_imports/`, `venv/`.

## Manual Review

- [ ] README renders correctly on GitHub.
- [ ] Logo and screenshots load on GitHub.
- [ ] License stance is still intentional.
- [ ] No marketing claims imply hosted, secure, or internet-ready service.
- [ ] SECURITY.md still describes trusted workstation/LAN use.
- [ ] Installer source, publisher links, version, and release notes match the tag.
- [ ] Installer signing/SmartScreen status is stated honestly on the release page.

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

Create the Windows installer with the GitHub Actions `Windows Installer`
workflow. Download the `windows-installer` artifact and complete the manual
interactive install review before attaching the setup executable to a public
release.
