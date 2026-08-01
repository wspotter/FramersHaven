# Changelog

## v0.3.2-open-preview - 2026-08-01

- Use the verified GitHub Pages HTTPS endpoint as the primary in-app update feed.
- Backfill all missing bundled demo mouldings and mats during upgrades without
  overwriting existing catalog records.

## v0.3.1-open-preview - 2026-08-01

- Add a single per-user `FramersHaven-Setup.exe` that bundles the application
  runtime and requires no Python, Git, terminal, or administrator setup.
- Preserve customer data across upgrades and uninstall/reinstall under
  `%LOCALAPPDATA%\FramersHaven\Data`.
- Migrate data from the earlier Windows installer layout on first launch.
- Add Windows CI coverage for the bundle, migration, install, upgrade,
  uninstall data retention, reinstall, and packaged application health.
- Update public Windows help to use the setup executable download path.
- Fix the windowed launcher so Uvicorn does not require a console during startup.

## v0.2.0-rc1 - 2026-06-18

Public release candidate for the local Community and Workstation editions.

- Workstation accounting CSV handoff bundle for customers, invoices, and invoice lines
- Community and Workstation edition limits and usage display
- Defensive accounting export handling for malformed data, duplicate customer names, tax rounding, concurrent requests, and interrupted publication
- Explicit browser smoke coverage for both editions
- Updated API, feature, operator, accounting-schema, and Windows package documentation
- Repeatable Windows preview ZIP build with runtime/private-data exclusions

Remaining release gate: validate `run_windows.bat` and the packaged ZIP on a real Windows 10 or Windows 11 workstation before calling the Windows package final.

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
