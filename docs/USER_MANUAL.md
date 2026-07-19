# FramersHaven User Manual

## Purpose

FramersHaven is a local-first workstation app for intake, framing design, quoting, production tracking, and customer handoff.

The app is organized into separate workspaces so operators do not have to manage the whole workflow on one screen.

## Community Edition

FramersHaven Community Edition is the full free local workstation. Catalog
items, saved orders/quotes, local package imports, backups, PDF/JPG exports, and
accounting CSV export are available without artificial edition limits.

The optional Framewise assistant is configured from Admin. It can point at
Ollama, llama.cpp, LM Studio, or another OpenAI-compatible provider running on
the workstation or trusted private LAN. Framewise stays off until the operator
enables it, and the app does not ship model weights. In Design, Framewise can
analyze the selected artwork image with a vision-capable provider, then suggest
three customer-facing framing looks using real local catalog SKUs. A selected
look can be applied to the live mockup before the operator calculates the quote.
If no model provider is enabled, Framewise uses local starter looks instead of
blocking the workflow.

The recommended local starter is SmolVLM2 through Ollama:

```bash
ollama run hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M
```

The app is local-first. Operator-supplied catalog files, customer records, exports, backups, and previews stay on the workstation or trusted private LAN unless the operator moves them manually.

This is a local-first app. It does not provide payment processing, email/SMS sending, or accounting API sync. Do not expose it directly to the public internet.

## Starting the App

On Windows, double-click `run_windows.bat`.

On macOS or Linux:

1. Activate the virtual environment if needed.
2. Run `./scripts/run.sh`.
3. Open `http://127.0.0.1:8000` in a browser on the workstation.
4. Open `http://127.0.0.1:8000/help/` for the multi-page operator guide.

`./scripts/run.sh` listens on `0.0.0.0:8000`, so another shop computer can open the app using this workstation's LAN IP address.

## Operator Help Site

- The local help home is `/help/`; `/help` redirects there automatically.
- Use the topic navigation for Design, Gallery & Intake, Orders & Quotes, Customer Management, and Admin & Pricing.
- Each help page includes a `Back to App` link.
- Help topics include fresh screenshots from the current application.
- Use the `Help` link in the workstation header to open the guide in a new tab.

## Workspace Overview

- The top bar includes a `Theme` selector. `Studio` applies the shop palette with pink as the main color, teal as the secondary color, and black/white neutrals.
- The top bar switches between the main workspaces. The catalog sidebar is visible only in Design; other workspaces expand to the full window. Returning to Design restores the previous drawer and search state.

### Design
- Use this tab to prepare a quote from a selected gallery image and framing materials.
- Choose a customer, artwork size, moulding, mat stack, glazing, labor, opening layout, and optional add-on rows.
- A quote cannot be saved until the customer has a name and phone number. Walk-in customer placeholders are not accepted.
- Use `Select top`, `Select 2nd`, `Select 3rd`, or `Select ext.` to open the side catalog drawer and browse the full local material catalog.
- The drawer shows the active slot, search results, selected material state, and available preview images or swatches.
- In multi-opening mode, use the `Gallery` button on each window row to pick artwork from the app gallery without opening the desktop file picker.
- The opening controls drawer is intentionally compact so it stays usable in the left sidebar.
- In multi-opening mode, use the `Batch Selection` grid to pick which windows should be affected by `Align` or `Distribute`.
- Leave the batch selection empty if you want the align/distribute buttons to apply to all windows.
- Use `Undo` and `Redo` in the Design workspace to step back through recent design edits.
- Run `Calculate Quote` before saving.
- Use `Save Quote` to send the current quote into the `Orders / Quotes` workspace.

### Gallery
- Use this tab as the intake staging area for uploaded artwork.
- Use the left artwork list to pick an existing saved image.
- Use the right editor to upload new artwork or adjust a saved image's size, ratio, zoom, and crop position.
- Use `Zoom In`, `Zoom Out`, `Reset Crop`, and `Fit Artwork` to adjust the crop box.
- Rotation on a new upload physically saves the uploaded file in that orientation. Rotation on saved artwork is metadata-only and is applied when the artwork is used in Design.
- Use `Save New Artwork` for a desktop JPG/PNG, or `Update Artwork` after changing a saved image.
- Use `Use in Design` to save the current crop metadata, then carry the selected saved image, dimensions, and crop rectangle into the design workspace.

### Orders / Quotes
- Use this tab to review saved quotes, move work through statuses, and export paperwork.
- Use `All Jobs`, `Needs Approval`, `Work Orders`, and `Invoices` for quick stage filtering.
- Click any column heading to sort ascending; click it again to sort descending.
- Click a job row to open its inspector. Use the tabs for Overview, Build, History, Files, and Handoff. Close it with `Close`, the backdrop, or `Escape`.
- Status flow is:
  - `quote`
  - customer approval creates the `work_order`
  - marking the work order done creates the `invoice`
- Order detail includes customer info, selected materials, line items, history, and export actions.
- In the `Files` tab, choose Quote PDF, Work Order PDF, Invoice PDF, or Mockup JPG to preview it inside the job inspector.
- After reviewing it, use `Save File`, `Open New Tab`, or `Send`. Send carries the document name into Handoff; download and attach the file manually before sending.
- Orders can move from `invoice` back to `work_order` when a completed invoice needs production changes; the job must be marked done again before it can return to invoice.
- `Handoff` shows editable email and SMS previews. Enter or correct the customer email, review the exact copy, then use Copy Email, Open Email Draft, or Copy SMS.
- Quote PDFs and preview JPGs must be attached manually; the app does not claim that local workstation links are customer-accessible.

### Customers
- Use this tab to search repeat customers and review their prior orders.
- Saving a quote will auto-create or refresh a customer record by name.
- Edit customer details here when contact info changes.

### Admin
- Admin opens on a catalog-first table. Search across SKU, name, vendor, or category, use the material quick filters, and click a column heading to switch ascending/descending sort.
- Select a material row to open its editor drawer; use `New Item` for a missing material. Close the drawer with `Close`, the backdrop, or `Escape`.
- The edition status in the Admin rail shows current catalog, saved order/quote, and package-import usage.
- Use the left utility rail for Import, Pricing, Services, Backups, and Diagnostics instead of scrolling through every tool at once.
- Pricing settings affect future quote calculations.
- Service pricing controls the retail quote rows for backing, mounting, frame mounting, printing, various, assembly, and royalties.
- Accounting generates a local ZIP containing customer, invoice, and invoice-line CSV files. Review those files before using them in any accounting workflow.
- Assistant settings configure Framewise, the optional local AI helper for framing suggestions and quote explanations.
- `Import Mat Package` and `Import Moulding Package` read operator-supplied files from the local `catalog_imports/` folder and attach matching preview images when the zip is present.
- Use the cropped texture uploader after selecting a moulding in the catalog editor when a good moulding strip needs to be attached manually.
- Backups create a zip containing the database, uploads, exports, and catalog snapshot files.

## Workstation Runbook

### Install Or Refresh

1. From the repo root, create a virtual environment if one does not exist: `python -m venv venv`.
2. Install runtime dependencies: `./venv/bin/pip install -r requirements.txt`.
3. For browser smoke testing, install dev tools: `./venv/bin/pip install -r requirements-dev.txt`.
4. Install Chromium for Playwright smoke tests: `./venv/bin/python -m playwright install chromium`.

### Start

1. Run `./scripts/run.sh`.
2. Open `http://127.0.0.1:8000`.
3. Open `http://127.0.0.1:8000/help/` and confirm the operator guide loads.
4. Confirm the app answers with `http://127.0.0.1:8000/api/health` if the browser looks stale.

### Verify Before Shop Use

Run these from the repo root:

```bash
node -c app/static/app.js
./venv/bin/python -m compileall app tests
./venv/bin/python -m pytest -q
./venv/bin/python scripts/browser_smoke.py
```

### Stop Or Restart

- Stop the terminal running the app with `Ctrl-C`.
- Start again with `./scripts/run.sh`.

## Daily Operator Flow

1. Upload artwork in `Gallery`.
2. Review the saved image and move it into `Design`.
3. Select customer, dimensions, and materials.
4. Adjust the mockup and calculate the quote.
5. Save the quote with the customer's name and phone number.
6. Open `Orders / Quotes` to review, export, or prepare customer handoff text.
7. When the customer approves, use `Approve quote -> work order`.
8. After build completion, use `Mark done -> invoice`.

## Designer Notes

### Artwork Size
- `Image Size` is the physical artwork size in inches.
- When a gallery image is selected, its recorded size is copied into the design fields.

### Crop Tools
- Ratio presets lock the crop preview to common framing proportions.
- Zoom adjusts the image beneath the crop window.
- Crop metadata is stored with the gallery image for intake reference.

### Opening Layout
- `single opening` centers one opening in the mat.
- `2 openings` enables a basic diptych-style layout.
- `Opening Spacing` controls the gap between the two openings.
- `Opening Balance` controls how much of the total opening width goes to the left opening versus the right opening.
- `Opening Pos. X` shifts the opening group left or right.
- `Opening Pos. Y` shifts the opening vertically within the mat to create more visual weight at the top or bottom.
- The `Horizontal weight` and `Vertical weight` sliders mirror the `Opening Pos.` fields if you want a faster visual adjustment.
- You can also drag the opening inside the mockup instead of typing offsets manually.
- In `2 openings` mode, the divider can also be dragged in the mockup canvas.

### Mat Stack
- `Top mat` is the main visible mat color.
- `2nd mat` and `3rd mat` are deeper layers with smaller openings and visible reveals.
- `Reveal` is the amount of the lower mat that shows around the opening above it.
- The current builder supports one, two, or three mats.
- The builder is intentionally compact: short labels, smaller fields, and a tighter picker layout are expected.
- Mat pricing uses the outside mat size rather than the internal opening size.
- Imported mats can include user-supplied preview thumbnails, so the picker may show an image instead of a generic color dot.

### Quote Options
- The right-side worksheet includes compact service rows for backing, subject mounting, frame mounting, printing, various, assembly, and royalties.
- Each option row supports an optional discount percentage.
- `Global %` applies across the quote after any row-level discounts.
- Two `Other` rows are available for manual charges that are not in the catalog.
- Service rows are priced from the `Admin` tab, not from the materials catalog.
- Option rows are stored with the quote payload and appear in line items/exports after pricing is calculated.

## Quotes and Exports

- Quotes display line items, subtotal, tax, and total.
- PDF export is intended for printable paperwork; quote, work order, and invoice forms can be downloaded independently from the selected order.
- Quote and invoice PDFs show the selected line-item details without per-line item prices; totals remain in the summary area.
- New saved quotes include the current design mockup image on the generated PDF forms.
- JPG export is intended for customer preview and internal reference.
- Order CSV export downloads the current full order list as a spreadsheet.

## Backups and Recovery

- Create backups from the `Admin` tab.
- Each backup zip contains:
  - `studio.db`
  - uploaded artwork files
  - generated exports
  - a catalog snapshot CSV
  - backup metadata
- Create backups before major catalog imports or workstation changes.

### Restoring A Backup

1. Stop the app.
2. Copy the current `studio.db`, `uploads/`, `exports/`, and `catalog_previews/` somewhere safe if they still exist.
3. Unzip the chosen `backups/framershaven_backup_*.zip` into a temporary folder.
4. Replace `studio.db` with the backed-up database file.
5. Restore backed-up `uploads/` and `exports/` files into their matching project folders.
6. Start the app with `./scripts/run.sh`.
7. Open `Admin`, confirm the catalog counts, then open `Orders / Quotes` and spot-check recent jobs.

## Tooltips

Complex controls in the UI include tooltips. Hover over fields like `Opening Balance`, `Opening Offset Y`, backup actions, and handoff actions when the intent is not obvious.

## Known Limits

- Messaging is manual only. The app prepares email and SMS text but does not send messages directly.
- The current multi-opening flow is limited to a basic two-opening layout.
- Payment handling remains outside this app.

## Troubleshooting

### Quote Will Not Save
- Run `Calculate Quote` first.
- Make sure customer name, phone number, dimensions, and pricing inputs are valid.

### Export Action Does Nothing
- Confirm an order is selected in `Orders / Quotes`.
- Try generating the export again after reopening the order detail.

### Customer Record Looks Missing
- Search by name or contact in the `Customers` tab.
- Saving a quote with a matching customer name refreshes that customer record.

### Need a Safer Recovery Point
- Create a backup zip from `Admin` before making large changes.
