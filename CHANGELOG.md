# Changelog

## Unreleased

- Add a per-user Windows installer that bundles the application and Python
  runtime, launches from normal shortcuts, and requires no administrator access.
- Store packaged Windows data under `%LOCALAPPDATA%\FramersHaven\Data` so
  upgrades and uninstall/reinstall cycles preserve customer records and assets.
- Add Windows CI coverage for the bundled executable, clean install, upgrade,
  uninstall data retention, reinstall, and packaged application smoke checks.
- Replace private shop identity defaults and internal planning documents with
  neutral FramersHaven distribution defaults and public release safeguards.
- Require an admin session for `/admin/*` by default instead of silently
  granting owner access to anonymous visitors.
- Add the missing admin login page, remove password hashes from `/admin/me`,
  move the session secret to `FRAMERSHAVEN_SESSION_SECRET`, and hide FastAPI API
  docs unless `FRAMERSHAVEN_EXPOSE_API_DOCS=1` is set.
- Keep an explicit `FRAMERSHAVEN_ALLOW_OPEN_ADMIN=1` local/demo escape hatch for
  trusted workstation installs that intentionally want open admin mode.

## v0.1.0 - 2026-06-15

Initial public release of FramersHaven.

- Local-first FastAPI/SQLite framing workstation
- FramersHaven branding, FH logo, and generated demo data
- Design, Gallery, Orders / Quotes, Customers, and Admin workspaces
- Quote/work-order/invoice flow with PDF and JPG previews
- Multi-page local operator help with regenerated screenshots
- Deterministic demo seed script and browser smoke test
- Windows local launcher and install guide
- Public packaging docs, security notes, contribution notes, and dependency notices
