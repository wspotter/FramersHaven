# Accounting CSV Export Schema

This schema documents the Workstation-only local CSV export implemented by FramersHaven. It is a file handoff, not accounting sync.

The file names and column headers below reference common accounting CSV import patterns. QuickBooks-compatible naming is used as a compatibility reference only; this is not a QuickBooks integration, certified export, or accounting API feature.

## Boundaries

- Export files are CSV only.
- Files are generated locally under `exports/accounting/`.
- No accounting credentials, API tokens, hosted service calls, or automatic reconciliation are included.
- Operators must review generated CSV files before using them in any accounting workflow.
- Demo and test examples must use fictional data only.
- This is the implemented v1 handoff schema. Target-specific mappings may change after operator review.

## Common Import Concepts

Accounting CSV imports commonly expect these concepts:

- transaction date
- customer or payee name
- invoice or reference number
- description or memo
- quantity
- unit rate
- line amount
- tax amount
- subtotal and total
- balance due
- stable customer and invoice identifiers

The first export should produce separate files so an operator or bookkeeper can map them manually without merging unrelated record types.

## Bundle Files

### `accounting_customers.csv`

Purpose: customer list handoff.

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `customer_id` | Yes | Text | Stable internal customer ID. |
| `customer_name` | Yes | Text | Display name from the local customer record. |
| `company_name` | No | Text | Blank unless the customer record stores a company name. |
| `billing_email` | No | Text | Customer email, if present. |
| `billing_phone` | No | Text | Customer phone, if present. |
| `billing_address_line1` | No | Text | Optional address line. |
| `billing_address_line2` | No | Text | Optional address line. |
| `billing_city` | No | Text | Optional address line. |
| `billing_state` | No | Text | Optional address line. |
| `billing_postal_code` | No | Text | Optional address line. |
| `billing_country` | No | Text | Optional address line. |
| `notes` | No | Text | Operator notes only; avoid sensitive details. |
| `created_at` | Yes | Date | Local record creation date. |
| `updated_at` | Yes | Date | Local record update date. |

### `accounting_invoices.csv`

Purpose: invoice header handoff.

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `invoice_id` | Yes | Text | Stable internal invoice/order ID. |
| `invoice_number` | Yes | Text | FramersHaven quote/order number. |
| `customer_id` | Yes | Text | Matches `accounting_customers.csv.customer_id`. |
| `customer_name` | Yes | Text | Snapshot of the customer name at export time. |
| `invoice_date` | Yes | Date | Use a consistent date format such as `YYYY-MM-DD`. |
| `due_date` | No | Date | Optional; blank if not tracked. |
| `status` | Yes | Text | `quote`, `work_order`, or `invoice`. |
| `subtotal` | Yes | Decimal | Numeric value without currency symbols. |
| `tax` | Yes | Decimal | Numeric value without currency symbols. |
| `total` | Yes | Decimal | Numeric value without currency symbols. |
| `amount_paid` | No | Decimal | Default `0` unless payment tracking is added. |
| `balance_due` | Yes | Decimal | `total - amount_paid`. |
| `currency` | No | Text | Default `USD` unless configured otherwise. |
| `memo` | No | Text | Short export note, not a legal invoice term. |
| `source_order_id` | Yes | Text | Internal order ID for traceability. |
| `approved_at` | No | Date/time | Blank when not approved. |
| `completed_at` | No | Date/time | Blank when not completed. |
| `invoiced_at` | No | Date/time | Blank when not invoiced. |

### `accounting_invoice_lines.csv`

Purpose: invoice line-item handoff.

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `invoice_id` | Yes | Text | Matches `accounting_invoices.csv.invoice_id`. |
| `invoice_number` | Yes | Text | Matches `accounting_invoices.csv.invoice_number`. |
| `line_number` | Yes | Integer | Starts at 1 for each invoice. |
| `customer_name` | Yes | Text | Snapshot of the customer name at export time. |
| `item` | Yes | Text | Human-readable label for the line. |
| `description` | Yes | Text | Human-readable detail; escape commas, quotes, and newlines. |
| `quantity` | Yes | Decimal | Use `1` for fixed service or package lines. |
| `rate` | Yes | Decimal | Unit amount before tax. |
| `amount` | Yes | Decimal | `quantity * rate`. |
| `tax` | No | Decimal | Line tax allocation if available. |
| `taxable` | No | Boolean | `true` or `false`. |
| `category` | Yes | Text | `material`, `service`, `labor`, or `manual`. |
| `source_sku` | No | Text | Catalog SKU when the line came from a catalog item. |
| `memo` | No | Text | Optional short note. |

## Intentionally Omitted

The first schema should not claim support for:

- accounting API sync
- product/service item synchronization
- chart of accounts mapping
- payment deposits
- bank feeds
- tax-code registration
- inventory quantity updates
- automatic reconciliation
- hosted document delivery

## Fictional Example

### `accounting_customers.csv`

```csv
customer_id,customer_name,company_name,billing_email,billing_phone,billing_address_line1,billing_address_line2,billing_city,billing_state,billing_postal_code,billing_country,notes,created_at,updated_at
CUST-000001,Example Customer A,,,555-0100,,,,,,,2026-06-01,2026-06-01
```

### `accounting_invoices.csv`

```csv
invoice_id,invoice_number,customer_id,customer_name,invoice_date,due_date,status,subtotal,tax,total,amount_paid,balance_due,currency,memo,source_order_id,approved_at,completed_at,invoiced_at
INV-000001,Q000001,CUST-000001,Example Customer A,2026-06-16,,invoice,125.00,10.00,135.00,0.00,135.00,USD,Customer preview framing package,ORD-000001,2026-06-16T10:00:00,2026-06-16T12:00:00,2026-06-16T12:30:00
```

### `accounting_invoice_lines.csv`

```csv
invoice_id,invoice_number,line_number,customer_name,item,description,quantity,rate,amount,tax,taxable,category,source_sku,memo
INV-000001,Q000001,1,Example Customer A,Frame package,"Custom framing mockup, mat stack, and glazing",1,125.00,125.00,10.00,true,service,,Fictional example line
```

## Validation Checklist

Before release or operational use, confirm:

- [ ] The target accounting import accepts or can map these columns.
- [ ] Date format matches the operator's accounting locale.
- [ ] Decimal fields never include currency symbols.
- [ ] CSV output escapes commas, quotes, and newlines.
- [ ] Exported files use UTF-8 without a byte order mark.
- [ ] Community Edition receives a Workstation-only error.
- [ ] Workstation export remains local and file-based.
- [ ] No accounting credentials, API tokens, or external service calls are included.
