# Changelog

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
