# FramersHaven Commercialization Plan

This plan turns FramersHaven from a clean public demo into a small paid Windows workstation product without overreaching into hosted SaaS, bundled vendor data, or direct accounting integrations too early.

Working assumption: Community remains useful and public. Paid Workstation earns money through Windows convenience, unlimited local catalog management, branded shop workflows, setup support, and accounting exports.

## North Star

- [ ] Keep FramersHaven local-first.
- [ ] Keep vendor catalog/image data user-supplied.
- [ ] Avoid claiming POS replacement until the app proves it.
- [ ] Avoid competitor, vendor, or comparison language.
- [ ] Make the paid version feel like convenience and business value, not artificial breakage.

## Product Editions

### Community Edition

Purpose: let users try the app, inspect the source, and run a small demo/shop trial.

- [ ] Manual catalog entry remains available.
- [ ] Demo seed includes fictional starter inventory only.
- [ ] Local quote/order/customer workflow remains useful.
- [ ] Basic PDF/JPG export remains available.
- [ ] Manual backups remain available.
- [ ] Community limits are clear and polite.

Recommended Community limits:

- [ ] 1 studio profile.
- [ ] Up to 50 active catalog items.
- [ ] Up to 25 saved orders/quotes.
- [ ] Up to 1 local catalog package import.
- [ ] No accounting CSV export.
- [ ] No paid Windows packaged release entitlement.

### Workstation Edition

Purpose: paid Windows-ready shop build for actual daily use.

- [ ] Unlimited active catalog items.
- [ ] Unlimited local catalog package imports.
- [ ] Unlimited saved orders/quotes.
- [ ] Branded document templates.
- [ ] Accounting CSV exports.
- [ ] Polished Windows release ZIP.
- [ ] Optional paid setup/support.

## Architecture Decisions

- [ ] Use a local edition flag instead of online license enforcement for v1.
- [ ] Prefer honest source-available packaging over DRM.
- [ ] Store edition state in a small local config file or environment variable.
- [ ] Treat accounting export as CSV files first, not API sync.
- [ ] Keep all accounting export files generated locally under `exports/`.
- [ ] Keep tests able to run in Community mode and Workstation mode.

Recommended edition implementation:

- [ ] Add `app/edition.py`.
- [ ] Default to `community`.
- [ ] Allow `FRAMERSHAVEN_EDITION=workstation`.
- [ ] Add `GET /api/edition`.
- [ ] Add server-side limit checks where data is created/imported.
- [ ] Add UI messaging only at limit boundaries, not constant nagging.

## Phase 1: Edition Foundation

### Task 1: Define Edition Contract

Description: Create the rules for Community and Workstation in code and docs.

Acceptance criteria:

- [ ] `community` and `workstation` are the only recognized edition names.
- [ ] Unknown edition values fall back to `community`.
- [ ] Limits are centralized in one Python module.
- [ ] README and release docs describe the editions without hard-selling.

Verification:

- [ ] Unit tests cover default edition.
- [ ] Unit tests cover `FRAMERSHAVEN_EDITION=workstation`.
- [ ] `./venv/bin/python -m pytest -q tests`.

Suggested files:

- `app/edition.py`
- `app/main.py`
- `tests/test_api.py`
- `README.md`
- `docs/release/PUBLIC_RELEASE_CHECKLIST.md`

Safe for other LLM:

- [ ] Draft edition wording for README.
- [ ] Draft release checklist additions.

Codex/local review required:

- [ ] Any code that controls limits.

### Task 2: Add Edition API

Description: Expose the active edition and limits to the frontend.

Acceptance criteria:

- [ ] `GET /api/edition` returns edition name, display label, and limits.
- [ ] No secrets or machine-specific data are exposed.
- [ ] Tests assert the response shape.

Verification:

- [ ] API test passes for Community.
- [ ] API test passes for Workstation env override.

Suggested files:

- `app/main.py`
- `app/edition.py`
- `tests/test_api.py`

Safe for other LLM:

- [ ] Draft response JSON examples.

Codex/local review required:

- [ ] Endpoint implementation and tests.

### Checkpoint: Edition Foundation

- [ ] Python compile passes.
- [ ] Pytest passes.
- [ ] No UI behavior changed yet.
- [ ] Release/private footprint scans are clean.

## Phase 2: Community Limits

### Task 3: Catalog Limit

Description: Enforce Community catalog limits while keeping manual use pleasant.

Acceptance criteria:

- [ ] Community blocks creating/importing active catalog items past the configured limit.
- [ ] Workstation has no catalog item limit.
- [ ] Error message explains the limit and says existing data is untouched.
- [ ] Existing over-limit databases still boot.

Verification:

- [ ] API test for manual item creation at limit.
- [ ] API test for local package import at limit.
- [ ] Workstation-mode tests prove no limit.

Suggested files:

- `app/main.py`
- `app/edition.py`
- `tests/test_api.py`

Safe for other LLM:

- [ ] Draft user-facing limit copy.

Codex/local review required:

- [ ] Limit enforcement and database-path tests.

### Task 4: Order Limit

Description: Enforce Community saved order/quote limit.

Acceptance criteria:

- [ ] Community blocks saving a new quote after the order limit.
- [ ] Existing orders remain readable/exportable.
- [ ] Workstation has no saved order limit.
- [ ] Error is visible in the normal Design save flow.

Verification:

- [ ] API test for save quote at limit.
- [ ] Browser smoke still saves in default seeded state.
- [ ] Workstation-mode test bypasses limit.

Suggested files:

- `app/main.py`
- `app/static/app.js`
- `tests/test_api.py`
- `scripts/browser_smoke.py`

Safe for other LLM:

- [ ] Draft help/manual language.

Codex/local review required:

- [ ] Save-flow enforcement and browser smoke.

### Task 5: Import Package Count Limit

Description: Let Community try one local catalog package import while keeping unlimited import management in Workstation.

Acceptance criteria:

- [ ] Community tracks successful local package import count.
- [ ] Failed imports do not consume the import allowance.
- [ ] Workstation has unlimited imports.
- [ ] Existing manually added items do not count as package imports.

Verification:

- [ ] API test successful import count increments.
- [ ] API test failed import does not increment.
- [ ] API test second import is blocked in Community.

Suggested files:

- `app/db.py`
- `app/main.py`
- `app/edition.py`
- `tests/test_api.py`

Safe for other LLM:

- [ ] Draft copy explaining "local catalog package".

Codex/local review required:

- [ ] Migration and import-count storage.

### Checkpoint: Community Limits

- [ ] All API tests pass.
- [ ] Browser smoke passes.
- [ ] Community users can still complete a demo quote.
- [ ] Workstation mode removes limits.
- [ ] No hard-coded real vendor names or private terms introduced.

## Phase 3: Edition UI

### Task 6: About/Edition Panel

Description: Add a quiet place in Admin or Help that shows the active edition and current limits.

Acceptance criteria:

- [ ] Active edition is visible.
- [ ] Community limits are visible.
- [ ] Workstation shows "unlimited" where appropriate.
- [ ] No external billing link is required yet.

Verification:

- [ ] Frontend smoke confirms `/api/edition` loads.
- [ ] Manual browser check of Admin/About area.

Suggested files:

- `app/templates/index.html`
- `app/static/app.js`
- `app/main.py`
- `app/static/help/admin-pricing.html`

Safe for other LLM:

- [ ] Draft UI copy.
- [ ] Suggest placement in Admin.

Codex/local review required:

- [ ] Frontend wiring and browser verification.

### Task 7: Limit Boundary Messaging

Description: Show upgrade messaging only when users hit a Community limit.

Acceptance criteria:

- [ ] Catalog limit message appears when adding/importing beyond limit.
- [ ] Order limit message appears when saving beyond limit.
- [ ] Message is factual and non-pushy.
- [ ] Workstation users never see upgrade prompts.

Verification:

- [ ] API tests assert structured error codes.
- [ ] Browser check for visible messages.

Suggested files:

- `app/main.py`
- `app/static/app.js`
- `tests/test_api.py`

Safe for other LLM:

- [ ] Draft exact messages.

Codex/local review required:

- [ ] Error handling and UI integration.

### Checkpoint: Edition UI

- [ ] Help screenshots regenerated if UI changed.
- [ ] Browser smoke passes.
- [ ] README and user manual match the UI.

## Phase 4: Accounting CSV Export

### Task 8: Define Accounting Export Schema

Description: Decide the first export format before writing code.

Recommended v1 export files:

- [x] `accounting_customers.csv`
- [x] `accounting_invoices.csv`
- [x] `accounting_invoice_lines.csv`

Acceptance criteria:

- [x] Fields are documented.
- [x] Export is CSV only, no API sync.
- [x] Tax, subtotal, total, customer name, date, quote/order number, and line-item labels are included.
- [x] Unsupported accounting fields are documented as intentionally omitted.

Verification:

- [ ] Schema doc reviewed by human before implementation.

Suggested files:

- `docs/release/ACCOUNTING_CSV_SCHEMA.md`

Safe for other LLM:

- [ ] Research common accounting CSV import columns.
- [ ] Draft schema doc.

Codex/local review required:

- [x] Final schema decisions.

### Task 9: Build Export Generator

Description: Generate accounting CSV files from local orders/customers.

Acceptance criteria:

- [x] Workstation edition can export CSVs.
- [x] Community edition receives a structured "Workstation feature" error.
- [x] Export files are written under `exports/accounting/`.
- [x] CSV output escapes commas, quotes, and newlines correctly.

Verification:

- [x] Unit tests for CSV formatting.
- [x] API tests for edition gating.
- [x] Manual open of generated CSV files.

Suggested files:

- `app/main.py`
- `app/accounting_export.py`
- `tests/test_api.py`
- `tests/test_accounting_export.py`

Safe for other LLM:

- [ ] Draft sample CSV output using fictional data.

Codex/local review required:

- [x] Export implementation and tests.

### Task 10: Add Export UI

Description: Add a Workstation-only accounting export control in Admin.

Acceptance criteria:

- [x] Admin shows Accounting Export section.
- [x] Community explains the feature is Workstation-only.
- [x] Workstation can generate/download CSV bundle.
- [x] Export never sends data to a third-party service.

Verification:

- [x] Browser smoke or Playwright check for Admin export.
- [x] Generated files exist under `exports/accounting/`.

Suggested files:

- `app/templates/index.html`
- `app/static/app.js`
- `app/main.py`
- `app/static/help/admin-pricing.html`

Safe for other LLM:

- [ ] Draft help copy and labels.

Codex/local review required:

- [x] UI wiring and file download behavior.

### Checkpoint: Accounting CSV

- [x] Community mode blocks export cleanly.
- [x] Workstation mode generates valid CSVs.
- [x] No accounting API sync claims appear in docs.
- [x] Browser smoke passes.

## Phase 5: Windows Paid Package

### Task 11: Create Windows Release ZIP Script

Description: Add a repeatable script that builds a clean Windows-ready folder/ZIP.

Acceptance criteria:

- [ ] Package includes source, `run_windows.bat`, docs, requirements, and app files.
- [ ] Package excludes `.git`, `venv`, `studio.db`, uploads, exports, backups, previews, and import data.
- [ ] Package includes a short `START_HERE_WINDOWS.txt`.
- [ ] Build script can run from a clean checkout.

Verification:

- [ ] Inspect ZIP contents.
- [ ] Unzip into `/tmp` or Windows test machine and run install path.

Suggested files:

- `scripts/build_windows_package.py`
- `docs/WINDOWS_INSTALL.md`
- `START_HERE_WINDOWS.txt`

Safe for other LLM:

- [ ] Draft `START_HERE_WINDOWS.txt`.
- [ ] Draft packaging checklist.

Codex/local review required:

- [ ] Packaging script and exclusion rules.

### Task 12: Windows Manual Test

Description: Validate the launcher on an actual Windows machine.

Acceptance criteria:

- [ ] Fresh Windows clone or ZIP starts from `run_windows.bat`.
- [ ] Browser opens automatically.
- [ ] Demo data exists.
- [ ] App survives close/reopen without overwriting `studio.db`.
- [ ] `HOST=0.0.0.0` LAN mode works on a trusted network if tested.

Verification:

- [ ] Record Python version.
- [ ] Record Windows version.
- [ ] Save a short test report under `docs/release/`.

Suggested files:

- `docs/release/WINDOWS_TEST_REPORT.md`

Safe for other LLM:

- [ ] Draft report template.

Codex/local review required:

- [ ] Interpret failures and patch launcher.

### Checkpoint: Windows Package

- [ ] Windows run path tested.
- [ ] Release ZIP excludes runtime/private data.
- [ ] README instructions match actual behavior.

## Phase 6: Sales Surface

### Task 13: Draft Offer Page Copy

Description: Write public-facing copy that sells the paid build without overclaiming.

Acceptance criteria:

- [ ] Describes Community and Workstation clearly.
- [ ] States no vendor catalog/image data is included.
- [ ] States local-first and trusted workstation/LAN limits.
- [ ] Avoids competitor names.
- [ ] Avoids claims of accounting sync; says CSV export.

Suggested sections:

- [ ] What FramersHaven does.
- [ ] Who it is for.
- [ ] Community vs Workstation comparison.
- [ ] Windows setup/support offer.
- [ ] Data safety note.
- [ ] Limitations.

Safe for other LLM:

- [ ] Draft copy variants.
- [ ] Draft comparison table.

Codex/local review required:

- [ ] Legal/risk wording and final product claims.

### Task 14: Pricing Experiment

Description: Pick a simple early-access price and support offer.

Recommended starting offer:

- [ ] Community: free/source-available.
- [ ] Workstation Windows ZIP price decided outside the repo.
- [ ] Setup call price decided outside the repo.
- [ ] Updates through v1.0 included.

Acceptance criteria:

- [ ] Pricing is documented internally.
- [ ] Public copy does not promise indefinite support.
- [ ] Refund/support expectations are written plainly.

Safe for other LLM:

- [ ] Draft pricing FAQ.

Codex/local review required:

- [ ] Final numbers and offer terms.

### Checkpoint: Sales Surface

- [ ] Public wording reviewed.
- [ ] No competitor names.
- [ ] No unsupported legal/security/accounting claims.

## Phase 7: Release Verification

Final checklist before paid early access:

- [ ] Fresh clone installs from `requirements-dev.txt`.
- [ ] `python scripts/seed_demo.py` creates fictional demo data only.
- [ ] Community mode tests pass.
- [ ] Workstation mode tests pass.
- [ ] JavaScript syntax and unit tests pass.
- [ ] Python compile and pytest pass.
- [ ] `npm audit --audit-level=high` passes from `app/`.
- [ ] Browser smoke passes against demo data.
- [ ] Windows launcher starts from `run_windows.bat` on Windows.
- [ ] Windows package excludes runtime/private files.
- [ ] Accounting CSV export creates fictional test files correctly.
- [ ] Private footprint scan returns no old names, private paths, copied support links, or customer data.
- [ ] Runtime data remains ignored.
- [ ] README, user manual, and screenshots match current GUI.
- [ ] License stance is still intentional.

## Work Safe To Offload To Another LLM

Use another LLM for broad, reviewable drafts:

- [ ] README edition wording.
- [ ] User manual wording for Community/Workstation.
- [ ] `docs/release/ACCOUNTING_CSV_SCHEMA.md` first draft.
- [ ] Help copy for accounting export.
- [ ] Sales page copy variants.
- [ ] Pricing FAQ draft.
- [ ] Windows test report template.
- [ ] Release checklist wording.

Rules for offloaded work:

- [ ] Ask for patches only, not direct repo edits.
- [ ] Provide selected files/excerpts, not the full repo.
- [ ] Require fictional data only.
- [ ] Ban competitor names and vendor names in generated copy.
- [ ] Review every patch locally before applying.

## Work Codex Should Keep Local

- [ ] Edition enforcement code.
- [ ] Database migrations/settings.
- [ ] API endpoint implementation.
- [ ] Accounting CSV generator.
- [ ] Windows packaging script.
- [ ] Security/private footprint scans.
- [ ] Final CI and browser verification.
- [ ] Any force-push or release publication.

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Free version feels crippled | Medium | Keep core quote/order workflow useful. Limit scale and exports, not basic operation. |
| Vendor data implication | High | Use "operator-supplied local catalog files" everywhere. Ship no vendor catalogs/images. |
| Accounting import support burden | Medium | Start with CSV export only. Document limitations. |
| Windows launcher fails on real machines | Medium | Add manual Windows test report before selling. |
| Source-available license confusion | Medium | Keep license language explicit and avoid calling it open source unless license changes. |
| Support workload grows faster than revenue | High | Sell setup separately and keep early-access scope narrow. |

## Open Questions

- [ ] Should Workstation be one-time purchase, annual support, or both?
- [ ] What exact Community limits feel fair?
- [ ] Should the paid Windows build be distributed as ZIP first or installer first?
- [ ] Which accounting import target matters first: invoices, sales receipts, or customer list?
- [ ] What support promise is realistic for early access?
