# Edition Copy Drafts

This file contains draft user-facing copy for the implemented Community and Workstation modes. Distribution, pricing, support, and expanded branding language remains subject to human review.

## Edition Definitions

### Community Edition

Community Edition is the free, source-available snapshot for trying FramersHaven locally. It keeps the core workflow useful: manual catalog entry, local quote and order management, customer records, PDF/JPG exports, and manual backups.

Community Edition is scale-limited so small shops can evaluate the app without losing basic operation.

### Workstation Edition

Workstation Edition is the daily-use mode. It removes the Community catalog, saved order/quote, and package-import limits and includes local CSV export for accounting review. Paid Windows distribution and expanded branded templates remain planned.

Workstation Edition remains local-first. It is not a hosted service and does not include vendor catalogs, customer records, accounting credentials, or accounting API sync.

## Community Limits

The current code enforces:

- 1 studio profile
- Up to 50 active catalog items
- Up to 25 saved orders/quotes
- Up to 1 successful local catalog package import
- No accounting CSV export
- No paid Windows package entitlement

## Catalog Limit Message (Draft)

Community Edition includes up to 50 active catalog items. This item was not added, and existing catalog data was not changed. Workstation Edition removes this local scale limit.

## Order Limit Message (Draft)

Community Edition includes up to 25 saved orders/quotes. This quote was not saved, and existing orders remain available. Workstation Edition removes this local scale limit.

## Local Catalog Package Import Message (Draft)

Community Edition includes one successful local catalog package import. Failed imports do not consume the allowance. Workstation Edition allows unlimited local catalog package imports.

## Local Catalog Package Explanation

A local catalog package is an operator-supplied CSV or ZIP file stored in the local `catalog_imports/` folder. It can update mats, mouldings, glazing, or related preview files. FramersHaven does not ship vendor catalogs or preview images.

## Help Copy: Accounting Export (Draft)

Workstation Edition creates a local ZIP containing customer, invoice, and invoice-line CSV files. The files can help with accounting review, but they do not connect to an accounting service or prove that records were accepted. No accounting credentials or API tokens are included.

## Help Copy: Edition Panel (Draft)

The Edition panel shows whether this workstation is running Community Edition or Workstation Edition. Community Edition shows the current local scale limits. Workstation Edition shows unlimited where those limits do not apply.

## Sales-Friendly Summary (Draft)

FramersHaven helps a framing shop keep intake, design, quoting, production tracking, customer history, and local paperwork in one workstation app. Community Edition is enough to try the workflow. Workstation Edition removes the local scale limits and adds local CSV export for accounting review. Paid Windows distribution and expanded branding remain separate release decisions.
