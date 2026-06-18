from __future__ import annotations

import csv
import json
import os
import tempfile
import threading
import zipfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Mapping


CUSTOMER_FIELDS = [
    "customer_id",
    "customer_name",
    "company_name",
    "billing_email",
    "billing_phone",
    "billing_address_line1",
    "billing_address_line2",
    "billing_city",
    "billing_state",
    "billing_postal_code",
    "billing_country",
    "notes",
    "created_at",
    "updated_at",
]

INVOICE_FIELDS = [
    "invoice_id",
    "invoice_number",
    "customer_id",
    "customer_name",
    "invoice_date",
    "due_date",
    "status",
    "subtotal",
    "tax",
    "total",
    "amount_paid",
    "balance_due",
    "currency",
    "memo",
    "source_order_id",
    "approved_at",
    "completed_at",
    "invoiced_at",
]

INVOICE_LINE_FIELDS = [
    "invoice_id",
    "invoice_number",
    "line_number",
    "customer_name",
    "item",
    "description",
    "quantity",
    "rate",
    "amount",
    "tax",
    "taxable",
    "category",
    "source_sku",
    "memo",
]

CSV_FILENAMES = {
    "customers": "accounting_customers.csv",
    "invoices": "accounting_invoices.csv",
    "invoice_lines": "accounting_invoice_lines.csv",
}

MATERIAL_LINE_KEYS = {"moulding", "mat", "glazing"}
LABOR_LINE_KEYS = {"labor", "assembly"}
_EXPORT_LOCK = threading.Lock()


@dataclass(frozen=True)
class AccountingExportResult:
    bundle_path: Path
    bundle_bytes: bytes
    customer_count: int
    invoice_count: int
    line_count: int
    fallback_line_count: int


def _parse_money(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not parsed.is_finite():
        return None
    try:
        return parsed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def _money(value: Any) -> Decimal:
    return _parse_money(value) or Decimal("0.00")


def _money_text(value: Any) -> str:
    return format(_money(value), ".2f")


def _date_text(value: Any) -> str:
    return str(value or "")[:10]


def _customer_id(customer_id: int) -> str:
    return f"CUST-{customer_id:06d}"


def _synthetic_customer_id(order_id: int) -> str:
    return f"CUST-ORDER-{order_id:06d}"


def _order_identifiers(order_id: int) -> tuple[str, str, str]:
    return f"INV-{order_id:06d}", f"Q{order_id:05d}", f"ORD-{order_id:06d}"


def _safe_payload(raw: Any) -> tuple[dict[str, Any], bool]:
    try:
        payload = json.loads(str(raw or ""))
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}, False
    return (payload, True) if isinstance(payload, dict) else ({}, False)


def _display_label(label: str) -> str:
    if label.replace("_", "").isalnum() and label.lower() == label:
        return label.replace("_", " ").title()
    return label


def _line_metadata(label: str, selected: Mapping[str, Any]) -> tuple[str, str, str]:
    normalized = label.strip().lower()
    item = _display_label(label)
    description = item
    source_sku = ""

    if normalized in MATERIAL_LINE_KEYS:
        selected_item = selected.get(normalized)
        if normalized == "mat" and not isinstance(selected_item, dict):
            layers = selected.get("mats")
            if isinstance(layers, list) and layers:
                first_layer = layers[0] if isinstance(layers[0], dict) else {}
                selected_item = first_layer.get("item")
        if isinstance(selected_item, dict):
            source_sku = str(selected_item.get("sku") or "")
            description = str(selected_item.get("name") or selected_item.get("sku") or item)
        return description, "material", source_sku

    addons = selected.get("addons")
    addon = addons.get(normalized) if isinstance(addons, dict) else None
    service = addon.get("service") if isinstance(addon, dict) else None
    if isinstance(service, dict):
        description = str(service.get("label") or item)
        return description, "service", ""

    if normalized in LABOR_LINE_KEYS:
        return description, "labor", ""
    return description, "manual", ""


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _load_rows(conn: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    started_transaction = not conn.in_transaction
    if started_transaction:
        conn.execute("BEGIN")
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, name, contact, customer_email, notes, created_at, updated_at
            FROM customers
            ORDER BY id ASC
            """
        )
        customers = [dict(row) for row in cur.fetchall()]
        cur.execute(
            """
            SELECT id, customer_name, customer_contact, customer_email, status,
                   approved_at, completed_at, invoiced_at, payload_json,
                   subtotal, tax, total, created_at, updated_at
            FROM orders
            ORDER BY id ASC
            """
        )
        orders = [dict(row) for row in cur.fetchall()]
        return customers, orders
    finally:
        if started_transaction:
            conn.rollback()


def _build_customer_rows(
    customers: list[dict[str, Any]],
    orders: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[int, str]]:
    rows: list[dict[str, Any]] = []
    customers_by_name: dict[str, list[dict[str, Any]]] = {}
    customer_ids_by_order: dict[int, str] = {}

    for customer in customers:
        customer_id = _customer_id(int(customer["id"]))
        name_key = str(customer["name"]).strip().casefold()
        customers_by_name.setdefault(name_key, []).append(customer)
        rows.append(
            {
                "customer_id": customer_id,
                "customer_name": customer["name"],
                "company_name": "",
                "billing_email": customer.get("customer_email") or "",
                "billing_phone": customer.get("contact") or "",
                "billing_address_line1": "",
                "billing_address_line2": "",
                "billing_city": "",
                "billing_state": "",
                "billing_postal_code": "",
                "billing_country": "",
                "notes": customer.get("notes") or "",
                "created_at": _date_text(customer.get("created_at")),
                "updated_at": _date_text(customer.get("updated_at")),
            }
        )

    for order in orders:
        order_id = int(order["id"])
        name = str(order.get("customer_name") or "").strip()
        name_key = name.casefold()
        candidates = customers_by_name.get(name_key, [])
        order_phone = str(order.get("customer_contact") or "").strip().casefold()
        order_email = str(order.get("customer_email") or "").strip().casefold()
        exact_matches = [
            candidate
            for candidate in candidates
            if (not order_phone or str(candidate.get("contact") or "").strip().casefold() == order_phone)
            and (
                not order_email
                or str(candidate.get("customer_email") or "").strip().casefold() == order_email
            )
        ]
        if len(exact_matches) == 1:
            customer_ids_by_order[order_id] = _customer_id(int(exact_matches[0]["id"]))
            continue
        if len(candidates) == 1:
            customer_ids_by_order[order_id] = _customer_id(int(candidates[0]["id"]))
            continue
        synthetic_id = _synthetic_customer_id(order_id)
        customer_ids_by_order[order_id] = synthetic_id
        rows.append(
            {
                "customer_id": synthetic_id,
                "customer_name": name or "Unnamed customer",
                "company_name": "",
                "billing_email": order.get("customer_email") or "",
                "billing_phone": order.get("customer_contact") or "",
                "billing_address_line1": "",
                "billing_address_line2": "",
                "billing_city": "",
                "billing_state": "",
                "billing_postal_code": "",
                "billing_country": "",
                "notes": "Created from a saved order during local accounting export.",
                "created_at": _date_text(order.get("created_at")),
                "updated_at": _date_text(order.get("updated_at")),
            }
        )
    return rows, customer_ids_by_order


def _build_invoice_rows(
    orders: list[dict[str, Any]],
    customer_ids: Mapping[int, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    invoices: list[dict[str, Any]] = []
    lines: list[dict[str, Any]] = []
    fallback_count = 0

    for order in orders:
        order_id = int(order["id"])
        invoice_id, invoice_number, source_order_id = _order_identifiers(order_id)
        customer_name = str(order.get("customer_name") or "").strip()
        subtotal = _money(order.get("subtotal"))
        tax = _money(order.get("tax"))
        total = _money(order.get("total"))
        invoices.append(
            {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "customer_id": customer_ids[order_id],
                "customer_name": customer_name,
                "invoice_date": _date_text(order.get("created_at")),
                "due_date": "",
                "status": order.get("status") or "quote",
                "subtotal": _money_text(subtotal),
                "tax": _money_text(tax),
                "total": _money_text(total),
                "amount_paid": "0.00",
                "balance_due": _money_text(total),
                "currency": "USD",
                "memo": "",
                "source_order_id": source_order_id,
                "approved_at": order.get("approved_at") or "",
                "completed_at": order.get("completed_at") or "",
                "invoiced_at": order.get("invoiced_at") or "",
            }
        )

        payload, payload_valid = _safe_payload(order.get("payload_json"))
        line_items = payload.get("line_items") if payload_valid else None
        selected = payload.get("selected") if payload_valid else None
        selected = selected if isinstance(selected, dict) else {}
        usable_items: list[tuple[str, Decimal]] = []
        invalid_items = False
        if isinstance(line_items, dict):
            for label, amount in line_items.items():
                parsed_amount = _parse_money(amount)
                if parsed_amount is None or parsed_amount < 0:
                    invalid_items = True
                    continue
                usable_items.append((str(label), parsed_amount))

        line_total = sum((amount for _, amount in usable_items), Decimal("0.00"))
        if invalid_items or not usable_items or line_total != subtotal:
            fallback_count += 1
            description = (
                "Stored order payload was invalid; exported as one summary line."
                if not payload_valid
                else "Stored order line items did not reconcile; exported as one summary line."
            )
            fallback_amount = subtotal if subtotal > 0 else total
            usable_items = [("Order summary", fallback_amount)]
            selected = {}
        else:
            description = ""

        allocated_tax_total = Decimal("0.00")
        for line_number, (label, amount) in enumerate(usable_items, start=1):
            line_description, category, source_sku = _line_metadata(label, selected)
            if label == "Order summary":
                line_description = description
                category = "manual"
            if line_number == len(usable_items):
                allocated_tax = tax - allocated_tax_total
            elif subtotal > 0:
                allocated_tax = (tax * amount / subtotal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                allocated_tax_total += allocated_tax
            else:
                allocated_tax = Decimal("0.00")
            lines.append(
                {
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "line_number": line_number,
                    "customer_name": customer_name,
                    "item": _display_label(label),
                    "description": line_description,
                    "quantity": "1",
                    "rate": _money_text(amount),
                    "amount": _money_text(amount),
                    "tax": _money_text(allocated_tax),
                    "taxable": "true" if allocated_tax > 0 else "false",
                    "category": category,
                    "source_sku": source_sku,
                    "memo": "",
                }
            )
    return invoices, lines, fallback_count


def _validate_export_path(path: Path, label: str) -> None:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink: {path}")


def _publish_artifacts(staged_paths: list[Path], output_dir: Path, staging: Path) -> None:
    backups: dict[Path, Path] = {}
    published: list[Path] = []
    try:
        for source in staged_paths:
            destination = output_dir / source.name
            if destination.exists():
                backup = staging / f".previous-{source.name}"
                os.replace(destination, backup)
                backups[destination] = backup
            os.replace(source, destination)
            published.append(destination)
    except Exception:
        for destination in published:
            destination.unlink(missing_ok=True)
        for destination, backup in backups.items():
            if backup.exists():
                os.replace(backup, destination)
        raise


def generate_accounting_export(conn: Any, export_root: Path) -> AccountingExportResult:
    _validate_export_path(export_root, "Accounting export root")
    export_root.mkdir(parents=True, exist_ok=True)
    output_dir = export_root / "accounting"
    _validate_export_path(output_dir, "Accounting output directory")
    output_dir.mkdir(parents=True, exist_ok=True)

    with _EXPORT_LOCK:
        customers, orders = _load_rows(conn)
        customer_rows, customer_ids = _build_customer_rows(customers, orders)
        invoice_rows, line_rows, fallback_count = _build_invoice_rows(orders, customer_ids)

        with tempfile.TemporaryDirectory(prefix=".accounting-export-", dir=output_dir) as tempdir:
            staging = Path(tempdir)
            staged_files = {
                "customers": staging / CSV_FILENAMES["customers"],
                "invoices": staging / CSV_FILENAMES["invoices"],
                "invoice_lines": staging / CSV_FILENAMES["invoice_lines"],
            }
            _write_csv(staged_files["customers"], CUSTOMER_FIELDS, customer_rows)
            _write_csv(staged_files["invoices"], INVOICE_FIELDS, invoice_rows)
            _write_csv(staged_files["invoice_lines"], INVOICE_LINE_FIELDS, line_rows)

            staged_bundle = staging / "accounting_csv_export.zip"
            with zipfile.ZipFile(staged_bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in staged_files.values():
                    archive.write(path, path.name)

            _publish_artifacts([*staged_files.values(), staged_bundle], output_dir, staging)
            bundle_path = output_dir / staged_bundle.name
            bundle_bytes = bundle_path.read_bytes()

    return AccountingExportResult(
        bundle_path=bundle_path,
        bundle_bytes=bundle_bytes,
        customer_count=len(customer_rows),
        invoice_count=len(invoice_rows),
        line_count=len(line_rows),
        fallback_line_count=fallback_count,
    )
