# FramersHaven Feature Ledger

This file is the source of truth for implemented behavior so sprint work does not get lost.

## Current Implemented Features

### Intake & Gallery
- Upload JPG/PNG artwork files.
- Attach physical artwork size in inches.
- Capture Cropper.js metadata (`x`, `y`, `width`, `height`, `rotate`, ratio fields, source size) and optional upload-time rotation.
- Save uploads to the local gallery and list recent images with thumbnails.
- Gallery uses a two-pane operator layout: saved artwork list on the left, focused editor on the right.
- Saved artwork can be selected and updated in place for size, ratio, rotation, zoom, and crop pan metadata.
- Gallery owns intake and crop work so staging stays separate from quoting.
- Selecting a gallery image restores its saved crop controls and carries its recorded dimensions and crop rectangle back into the design workspace.
- Design mockup rendering honors the saved crop rectangle instead of center-covering the whole image.
- Crop edits are metadata-only; the original uploaded artwork file remains intact.

### Workspace Navigation
- Top-bar workspace navigation separates `Design`, `Gallery`, `Orders / Quotes`, `Customers`, and `Admin`.
- The left sidebar carries the catalog and opening drawers during Design work, then hides on Gallery, Orders / Quotes, Customers, and Admin so those workspaces use the full width.
- Each workspace keeps its own detail panel instead of stacking the full flow on one screen.
- Workspace actions now surface success/error notices instead of relying only on raw JSON output.
- Key operator controls include inline tooltips for less-obvious actions and framing fields.
- Top bar includes a persistent theme selector with a Studio pink/teal palette option.

### Operator Help Site
- A multi-page operator guide is served locally at `/help/`; `/help` redirects to the same guide.
- Help topics cover the Design workspace, Gallery intake, Orders / Quotes, customer management, and Admin pricing/backups.
- Every page uses shared responsive styling, persistent topic navigation, a skip link, and a `Back to App` link.
- Topic pages include fresh screenshots captured from the current live application under `/help/images/`.
- The workstation header includes a `Help` link that opens the guide in a new tab.

### Design Workspace
- Crop preview supports panning and ratio presets for the working image.
- Live framing mockup updates from selected image, moulding width, mat border, and glazing selection.
- Designer includes initial multi-opening groundwork with `single` and `2 openings` layout modes.
- Diptych layout includes draggable divider spacing and synced numeric spacing/offset controls.
- Diptych layout also tracks opening balance and vertical offset controls in saved design state.
- Opening position controls support asymmetrical top/bottom or left/right mat weighting while keeping the outside size fixed.
- Opening position can be adjusted from the mockup directly or with synced horizontal/vertical weight sliders and numeric fields.
- Design workspace now follows a single builder-style worksheet instead of splitting quote setup and materials into unrelated cards.
- Builder controls use a denser, smaller-footprint layout so the material worksheet stays compact beside the mockup.
- Design worksheet now uses compact right-side operator rows for customer info, add-on option dropdowns, discounts, totals, and save actions.
- Mat selection supports a `top`, `2nd`, and `3rd` stack with reveal controls for deeper layers.
- `Select top`, `Select 2nd`, `Select 3rd`, and `Select ext.` open a dedicated side catalog drawer so browsing materials does not overload the worksheet itself.
- The catalog drawer shows the active material slot, keyword filtering, capped result messaging, selected-state treatment, thumbnails or swatches, and useful mat/moulding metadata.
- Multi-opening window art can be assigned from the app gallery with compact in-drawer pickers instead of the desktop file picker.
- Multi-opening batch actions now include a compact window grid selector so align/distribute can target specific windows instead of always affecting the whole set.
- Design workspace changes now support Undo and Redo for common opening, material, customer, and quote-state edits.
- Mat pricing is based on the outside size of the mat board rather than the internal opening.
- Mockup rendering shows stacked mat reveals with white-core cut lines instead of a single flat mat only.
- Material summary shows human-readable SKU/name selections instead of raw IDs.
- Quote panel shows line items alongside subtotal, tax, and total.
- Framewise can analyze the selected artwork image with a vision-capable provider and suggest three customer-facing framing looks from the Design workspace.
- Framewise suggestions are grounded to local catalog IDs/SKUs and can be applied directly to the current design before quote calculation.

### Catalog
- Import catalog data from CSV (`sku,name,category,cost,width_in`).
- Import operator-supplied local catalog packages for mats and mouldings directly from the local `catalog_imports/` folder.
- Import behavior is upsert by `(sku, category)`:
  - new rows are inserted,
  - existing rows are updated,
  - invalid rows are skipped.
- Search catalog by query and category.
- Admin workspace supports manual catalog item creation and correction.
- Admin workspace supports cropped moulding texture upload for manually improving preview coverage.
- Catalog items can now store vendor, height, rabbet depth, preview filename, and source metadata.
- Imported local catalog mats/mouldings expose linked preview images in the picker lists when the operator supplies preview files.
- Catalog write paths reject service-like categories so backing, mounting, printing, and similar rows stay in service pricing.

### Admin
- Admin uses a catalog-first command center with one searchable material table, category quick filters, sortable columns, and incremental result loading.
- Selecting a material opens a right-side editor drawer for item fields and moulding texture cropping.
- Import, pricing, service rows, assistant settings, backups, and diagnostics live in a compact utility rail instead of one long stacked page.
- Pricing rules are editable from the admin workspace instead of being hardcoded only in code.
- Tax rate plus moulding/mat/glazing markups are stored in local settings and used by quote calculation.
- Shop service rows for backing, mounting, frame mounting, printing, various, assembly, and royalties now use admin-managed retail prices instead of catalog items.
- Framewise assistant settings support optional local or OpenAI-compatible providers with model, base URL, context, temperature, and local API-key storage.
- Framewise remains useful without a configured provider by falling back to local starter looks from active moulding and mat catalog rows.

### Quote Engine
- Uses perimeter + area calculations.
- Supports linked catalog item IDs for moulding/mat/glazing.
- Supports admin-priced service rows for backing, subject mounting, frame mounting, printing, various, assembly, and royalties.
- Supports per-row discount percentages, one global discount percentage, and two custom manual charge rows.
- Applies pricing markups per material category.
- Uses the admin-configured tax rate in totals.

### Order Workflow
- Save quotes as orders.
- Quote saving requires a real customer name and phone number; walk-in quote records are rejected.
- Sequential quote number format: `Q00001`, `Q00002`, etc.
- Status progression is gated: `quote -> work_order` requires customer approval, and `work_order -> invoice` requires marking the work order done.
- Invoices can return to `work_order` when a job needs production changes; reopening clears the completion marker so the job must be marked done again before invoicing.
- Stores order status history notes/timestamps.
- Stores approval, completion, and invoice timestamps for order audit/export.
- Order detail shows selected components and stored line items, not just order totals.
- Order detail supports editing customer name/contact with an audit note in history.
- Orders list supports status filtering and text search by quote/customer/contact.
- Orders workspace uses a full-width job table with one-click stage filters for all jobs, needs approval, work orders, and invoices.
- Every job column can be sorted ascending or descending without losing the active stage filter or search.
- Selecting a job opens a closeable inspector drawer for overview, build details, history, files, and customer handoff.

### Customers
- Save customer records with contact info and notes.
- Customer records require a name and phone number for quote/work order provisioning.
- Search customer records from a dedicated customer workspace.
- Show prior orders on customer detail.
- Saving a quote auto-links or auto-creates a matching customer record by name.
- Customer detail supports in-place edits for name, contact, and notes.
- Renaming a customer updates linked order customer names.

### Export
- Orders CSV export endpoint for quotes/work orders/invoices.
- Community Edition accounting handoff ZIP containing customer, invoice, and invoice-line CSV files.
- Separate PDF form export for quotes, work orders, and invoices.
- Mockup JPG export.
- PDF/JPG exports show the stored tax-rate label from the quote payload.
- PDF/JPG exports include selected components for operator handoff; quote and invoice PDFs keep item-level prices out of the line-item table.
- PDF/JPG exports also show the stored opening layout label from the quote payload.
- The Orders Files tab previews quote, work-order, invoice, and mockup exports before saving them.
- A preview can be saved, opened in a new tab, or carried into Customer Handoff as the selected manual attachment.

### Handoff
- Orders can generate manual email subject/body and SMS text for operator handoff.
- Handoff drafts are shown in labeled editable preview fields with separate saved email and phone recipients.
- Operators can reset generated copy, copy the email draft, open a local email draft, or copy SMS text.
- PDF/JPG files remain explicit manual attachments; generated customer copy does not expose local workstation URLs.
- History records explicit copy/open actions but does not claim that a message was delivered.

### Persistence
- Admin workspace can create downloadable local backup zips.
- Backups include the SQLite database, uploads, exports, and a catalog snapshot for recovery.

### Branding Defaults
- Owner/contact/address values are preloaded from FramersHaven defaults and used by exports/UI.

## Non-Goals in Current Build
- POS integration.
- Native SMS provider integration.
- Fully freeform multi-opening mat designer with arbitrary openings, V-grooves, and advanced templates.
- Payment processing, accounting synchronization, and reconciliation.

## Sprint Rule
When features are added/changed/removed, update this file and `docs/API.md` in the same PR.
