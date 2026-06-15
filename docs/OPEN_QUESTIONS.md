# Open Questions

These are the remaining product and workflow decisions that do not block the current app, but should be resolved in the next pass.

## Operator Workflow

- Should there be a separate `picked_up` state, or is pickup/payment best kept outside the app?

Resolved 2026-06-08: approval and completion are lifecycle gates, not separate statuses. The app keeps `quote -> work_order -> invoice`, requires customer approval before work order creation, and requires marking the work order done before invoice creation.

## Designer Behavior

- What exact multi-opening behaviors matter most after the current diptych groundwork:
  - arbitrary number of openings
  - independent opening sizes
  - independent opening positions
  - V-groove controls
  - preset templates
- Are there must-have shop defaults for mat borders, common aspect ratios, or common frame sizes?

## Pricing and Catalog

- Does the shop need category-specific price tables in addition to the current cost-plus markup rules?
- Do any vendors require extra catalog fields beyond `sku`, `name`, `category`, `cost`, and `width_in`?

## Exports and Branding

- Are there printed quote samples or disclaimers that should be matched more closely in PDF output?
- Should the exported paperwork include logo assets, quote terms, or pickup instructions?

## Messaging

- Which customer handoff path matters more in practice: email or SMS?
- Should the app save a note when handoff text is prepared or copied?

## Recovery and Deployment

- Is the target still a single workstation, or should the app start preparing for a shared internal server?
- What backup cadence is expected in normal operation: manual only, daily reminder, or automated job?
