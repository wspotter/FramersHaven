from __future__ import annotations

import base64
import csv
import io
import json
import re
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from . import db as db_module
from .accounting_export import generate_accounting_export
from .auth import ensure_default_users, get_current_user, require_admin, router as auth_router
from .db import get_connection, init_db
from .db_admin import init_admin_tables
from .edition import (
    check_catalog_item_limit,
    check_catalog_package_import_limit,
    check_saved_orders_quotes_limit,
    get_catalog_imports_count,
    get_edition_info,
    increment_catalog_imports_count,
    require_accounting_csv_export,
)
from .framewise import router as framewise_router
from .pricing import QuoteRequest, calculate_quote

ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT.parent / "uploads"
EXPORT_DIR = ROOT.parent / "exports"
BACKUP_DIR = ROOT.parent / "backups"
PREVIEW_DIR = ROOT.parent / "catalog_previews"
CATALOG_IMPORT_DIR = ROOT.parent / "catalog_imports"
HELP_DIR = ROOT / "static" / "help"
UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)
PREVIEW_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    init_admin_tables()
    ensure_default_users()
    _backfill_catalog_preview_links()
    yield


app = FastAPI(title="FramersHaven", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(framewise_router)

app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/help", StaticFiles(directory=HELP_DIR, html=True), name="help")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/catalog-previews", StaticFiles(directory=PREVIEW_DIR), name="catalog-previews")
templates = Jinja2Templates(directory=str(ROOT / "templates"))

AUTH_EXEMPT_PATHS = {"/login", "/api/auth/login", "/api/health"}
AUTH_EXEMPT_PREFIXES = ("/static/", "/help", "/favicon.ico")
ADMIN_PATH_PREFIXES = (
    "/api/accounting/",
    "/api/backups",
    "/api/catalog/import",
    "/api/catalog/items",
    "/api/framewise/config",
    "/api/framewise/examples/export",
)
ADMIN_MUTATION_PATH_PREFIXES = (
    "/api/services",
    "/api/settings",
    "/api/studio-profile",
)


@app.middleware("http")
async def require_local_login(request: Request, call_next):
    path = request.url.path
    is_exempt = path in AUTH_EXEMPT_PATHS or path.startswith(AUTH_EXEMPT_PREFIXES)
    if not is_exempt and not get_current_user(request):
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Login required"}, status_code=401)
        return RedirectResponse("/login", status_code=303)
    needs_admin = any(path.startswith(prefix) for prefix in ADMIN_PATH_PREFIXES)
    if request.method != "GET" and any(path.startswith(prefix) for prefix in ADMIN_MUTATION_PATH_PREFIXES):
        needs_admin = True
    if needs_admin:
        try:
            require_admin(request)
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return await call_next(request)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(ROOT / "static" / "logo.png", media_type="image/png")

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
STUDIO_LOGO_TYPES = {"image/png": "PNG", "image/webp": "WEBP"}
STUDIO_LOGO_MAX_BYTES = 2 * 1024 * 1024
ALLOWED_STATUSES = ["quote", "work_order", "invoice"]
STATUS_NEXT = {"quote": "work_order", "work_order": "invoice", "invoice": "invoice"}


def _order_balance(row: dict[str, Any]) -> float:
    if row.get("status") == "invoice" and row.get("invoiced_at"):
        return 0.0
    return round(float(row.get("total") or 0), 2)


def _order_next_action(row: dict[str, Any]) -> str:
    status = row.get("status")
    if status == "quote":
        return "approve_quote"
    if status == "work_order":
        return "mark_done"
    if status == "invoice":
        return "view_invoice"
    return "view"


DEFAULT_SETTINGS = {
    "tax_rate": 0.06,
    "markup_moulding": 2.4,
    "markup_mat": 2.1,
    "markup_glazing": 1.9,
    "markup_addons": 1.85,
}

SERVICE_KEYS = [
    "glazing_reg_glass",
    "glazing_anti_reflection_glass",
    "glazing_acrylic",
    "glazing_anti_reflection_acrylic",
    "backing",
    "mounting",
    "frame_mounting",
    "printing",
    "various",
    "assembly",
    "royalties",
    "custom_1",
    "custom_2",
]
GLAZING_SERVICE_KEYS = set(SERVICE_KEYS[:4])
QUOTE_SERVICE_KEYS = [key for key in SERVICE_KEYS if key not in GLAZING_SERVICE_KEYS]
SERVICE_BASIS = {"count", "square_inches", "united_inches"}
CATALOG_CATEGORIES = {"moulding", "mat", "glazing"}
CATALOG_CATEGORY_ALIASES = {
    "mouldings": "moulding",
    "mats": "mat",
    "glazings": "glazing",
}

BRAND = {
    "business_name": "FramersHaven",
    "owner": "Demo Operator",
    "phone": "555-010-2026",
    "email": "hello@example.test",
    "street": "100 Gallery Lane",
    "city": "Cedar Falls",
    "state": "Kentucky",
    "postal_code": "41653",
    "address": "100 Gallery Lane, Cedar Falls, KY 40000",
}

STUDIO_PROFILE_SETTING_KEYS = {
    "business_name": "studio_business_name",
    "contact_name": "studio_contact_name",
    "phone": "studio_phone",
    "email": "studio_email",
    "street": "studio_street",
    "city": "studio_city",
    "state": "studio_state",
    "postal_code": "studio_postal_code",
    "logo_filename": "studio_logo_filename",
}


def _studio_profile_defaults() -> dict[str, str]:
    return {
        "business_name": BRAND["business_name"],
        "contact_name": BRAND["owner"],
        "phone": BRAND["phone"],
        "email": BRAND["email"],
        "street": BRAND["street"],
        "city": BRAND["city"],
        "state": BRAND["state"],
        "postal_code": BRAND["postal_code"],
        "logo_filename": "",
    }


def _get_studio_profile() -> dict[str, Any]:
    defaults = _studio_profile_defaults()
    conn = get_connection()
    cur = conn.cursor()
    keys = tuple(STUDIO_PROFILE_SETTING_KEYS.values())
    placeholders = ",".join("?" for _ in keys)
    cur.execute(f"SELECT key, value FROM settings WHERE key IN ({placeholders})", keys)
    stored = {row["key"]: row["value"] for row in cur.fetchall()}
    conn.close()
    profile = {
        field: str(stored.get(setting_key, defaults[field]) or "").strip()
        for field, setting_key in STUDIO_PROFILE_SETTING_KEYS.items()
    }
    address_parts = [profile["street"]]
    locality = ", ".join(part for part in [profile["city"], profile["state"]] if part)
    if profile["postal_code"]:
        locality = f"{locality} {profile['postal_code']}".strip()
    if locality:
        address_parts.append(locality)
    profile["address"] = ", ".join(part for part in address_parts if part)
    logo_path = UPLOAD_DIR / profile["logo_filename"] if profile["logo_filename"] else None
    profile["logo_url"] = f"/api/studio-profile/logo/file?v={logo_path.stat().st_mtime_ns}" if logo_path and logo_path.is_file() else "/static/logo.png"
    profile["owner"] = profile["contact_name"]
    return profile


def _save_studio_profile_values(values: Mapping[str, str]) -> dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    for field, value in values.items():
        setting_key = STUDIO_PROFILE_SETTING_KEYS[field]
        cur.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (setting_key, value),
        )
    conn.commit()
    conn.close()
    return _get_studio_profile()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "index.html", {"brand": _get_studio_profile(), "current_user": user})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/edition")
def edition() -> dict[str, object]:
    return get_edition_info()


@app.get("/api/edition/status")
def edition_status() -> dict[str, object]:
    info = get_edition_info()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE active = 1")
        active_catalog = cur.fetchone()["count"]
        cur.execute("SELECT COUNT(*) as count FROM orders")
        saved_orders_quotes = cur.fetchone()["count"]
        imports_used = get_catalog_imports_count(conn)
    finally:
        conn.close()
    return {
        "edition": info["edition"],
        "label": info["label"],
        "limits": info["limits"],
        "features": info["features"],
        "usage": {
            "active_catalog_items": active_catalog,
            "saved_orders_quotes": saved_orders_quotes,
            "catalog_package_imports": imports_used,
        },
    }


@app.get("/api/accounting/export.zip")
def export_accounting_csv_bundle() -> Response:
    require_accounting_csv_export()
    conn = get_connection()
    try:
        result = generate_accounting_export(conn, EXPORT_DIR)
    finally:
        conn.close()
    return Response(
        content=result.bundle_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{result.bundle_path.name}"',
            "X-FramersHaven-Customers": str(result.customer_count),
            "X-FramersHaven-Invoices": str(result.invoice_count),
            "X-FramersHaven-Lines": str(result.line_count),
            "X-FramersHaven-Fallback-Lines": str(result.fallback_line_count),
        },
    )


@app.get("/api/config")
def config() -> dict[str, Any]:
    return {"brand": _get_studio_profile(), "statuses": ALLOWED_STATUSES, "pricing": _get_settings()}


@app.get("/api/studio-profile")
def get_studio_profile() -> dict[str, Any]:
    return {"profile": _get_studio_profile()}


@app.post("/api/studio-profile")
def update_studio_profile(
    business_name: str = Form(...),
    contact_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    street: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    postal_code: str = Form(...),
) -> dict[str, Any]:
    values = {
        "business_name": business_name.strip(),
        "contact_name": contact_name.strip(),
        "phone": phone.strip(),
        "email": email.strip(),
        "street": street.strip(),
        "city": city.strip(),
        "state": state.strip(),
        "postal_code": postal_code.strip(),
    }
    for field, value in values.items():
        if not value:
            raise HTTPException(status_code=400, detail=f"{field.replace('_', ' ').title()} is required")
        if len(value) > 160:
            raise HTTPException(status_code=400, detail=f"{field.replace('_', ' ').title()} is too long")
    if "@" not in values["email"]:
        raise HTTPException(status_code=400, detail="Email must be valid")
    return {"profile": _save_studio_profile_values(values)}


@app.post("/api/studio-profile/logo")
async def upload_studio_logo(file: UploadFile = File(...)) -> dict[str, Any]:
    expected_format = STUDIO_LOGO_TYPES.get(file.content_type or "")
    if not expected_format:
        raise HTTPException(status_code=400, detail="Studio logo must be PNG or WebP")
    raw = await file.read(STUDIO_LOGO_MAX_BYTES + 1)
    if len(raw) > STUDIO_LOGO_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Studio logo must be 2 MB or smaller")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            actual_format = str(image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Studio logo is not a valid image") from exc
    if actual_format != expected_format:
        raise HTTPException(status_code=400, detail="Studio logo content must match its PNG or WebP file type")
    if not (300 <= width <= 1600 and 100 <= height <= 800):
        raise HTTPException(status_code=400, detail="Studio logo must be 300-1600 px wide and 100-800 px tall")
    ratio = width / height
    if not 2 <= ratio <= 5:
        raise HTTPException(status_code=400, detail="Studio logo aspect ratio must be between 2:1 and 5:1")
    extension = ".png" if actual_format == "PNG" else ".webp"
    filename = f"studio-logo{extension}"
    for existing in UPLOAD_DIR.glob("studio-logo.*"):
        existing.unlink(missing_ok=True)
    (UPLOAD_DIR / filename).write_bytes(raw)
    profile = _save_studio_profile_values({"logo_filename": filename})
    return {"profile": profile, "width": width, "height": height}


@app.get("/api/studio-profile/logo/file")
def studio_logo_file() -> FileResponse:
    profile = _get_studio_profile()
    filename = profile["logo_filename"]
    target = UPLOAD_DIR / filename if filename else None
    if not target or not target.is_file():
        raise HTTPException(status_code=404, detail="Studio logo not found")
    media_type = "image/png" if target.suffix.lower() == ".png" else "image/webp"
    return FileResponse(target, media_type=media_type)


@app.delete("/api/studio-profile/logo")
def delete_studio_logo() -> dict[str, Any]:
    profile = _get_studio_profile()
    if profile["logo_filename"]:
        (UPLOAD_DIR / profile["logo_filename"]).unlink(missing_ok=True)
    return {"profile": _save_studio_profile_values({"logo_filename": ""})}


def _require_positive(value: float, field_name: str) -> float:
    if value <= 0:
        raise HTTPException(status_code=400, detail=f"{field_name} must be positive")
    return value


def _require_non_negative(value: float, field_name: str) -> float:
    if value < 0:
        raise HTTPException(status_code=400, detail=f"{field_name} must be non-negative")
    return value


def _require_service_price(value: float, field_name: str) -> float:
    _require_non_negative(value, field_name)
    if value > 999.99:
        raise HTTPException(status_code=400, detail=f"{field_name} must be 999.99 or less")
    return round(value, 2)


def _parse_json_object(raw: str, field_name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail=f"{field_name} must be a JSON object")
    return parsed


def _safe_json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _image_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload["url"] = f"/uploads/{payload['filename']}"
    payload["crop_json"] = _safe_json_object(payload.get("crop_json"))
    return payload


def _normalize_catalog_category(category: str) -> str:
    cleaned = category.strip().lower()
    cleaned = CATALOG_CATEGORY_ALIASES.get(cleaned, cleaned)
    if cleaned not in CATALOG_CATEGORIES:
        allowed = ", ".join(sorted(CATALOG_CATEGORIES))
        raise HTTPException(status_code=400, detail=f"Catalog category must be one of: {allowed}")
    return cleaned


def _parse_order_payload_for_export(raw: str) -> dict[str, Any]:
    try:
        return _parse_json_object(raw, "payload_json")
    except HTTPException as exc:
        raise HTTPException(status_code=400, detail="Stored order payload is invalid JSON") from exc


def _fetch_image(cur, image_id: int | None) -> dict[str, Any] | None:
    if not image_id:
        return None
    cur.execute("SELECT id, filename, width_in, height_in, ratio_label FROM images WHERE id = ?", (image_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=400, detail=f"Image {image_id} not found")
    return dict(row)


def _get_settings() -> dict[str, float]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM settings")
    rows = {row["key"]: row["value"] for row in cur.fetchall()}
    conn.close()
    return {
        "tax_rate": float(rows.get("tax_rate", DEFAULT_SETTINGS["tax_rate"])),
        "markup_moulding": float(rows.get("markup_moulding", DEFAULT_SETTINGS["markup_moulding"])),
        "markup_mat": float(rows.get("markup_mat", DEFAULT_SETTINGS["markup_mat"])),
        "markup_glazing": float(rows.get("markup_glazing", DEFAULT_SETTINGS["markup_glazing"])),
        "markup_addons": float(rows.get("markup_addons", DEFAULT_SETTINGS["markup_addons"])),
    }


def _list_backups() -> list[dict[str, Any]]:
    backups = []
    for path in sorted(BACKUP_DIR.glob("framershaven_backup_*.zip"), reverse=True):
        stat = path.stat()
        backups.append(
            {
                "filename": path.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            }
        )
    return backups


def _list_service_options() -> list[dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT key, label, price, cost, markup, basis, active, sort_order, updated_at
        FROM service_options
        ORDER BY sort_order ASC, key ASC
        """
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def _safe_float(raw: str | None, default: float = 0.0) -> float:
    try:
        return float((raw or "").strip() or default)
    except (TypeError, ValueError):
        return default


def _require_customer_phone(raw: str, field_name: str = "customer_contact") -> str:
    clean = raw.strip()
    digits = re.sub(r"\D", "", clean)
    if len(digits) < 7:
        raise HTTPException(status_code=400, detail="Customer phone number is required")
    return clean


def _form_truthy(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "on", "approved", "done"}


def _catalog_preview_url(filename: str | None) -> str | None:
    if not filename:
        return None
    path = PREVIEW_DIR / filename
    if not path.is_file():
        return None
    version = int(path.stat().st_mtime)
    return f"/catalog-previews/{filename}?v={version}"


@lru_cache(maxsize=8)
def _catalog_preview_basename_index(folder: str) -> dict[str, str]:
    root = PREVIEW_DIR / folder
    if not root.is_dir():
        return {}
    index: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        index.setdefault(path.name.lower(), path.relative_to(PREVIEW_DIR).as_posix())
    return index


def _catalog_preview_candidates(row: dict[str, Any]) -> list[str]:
    filename = (row.get("preview_filename") or "").strip()
    category = (row.get("category") or "").strip()
    sku = (row.get("sku") or "").strip()
    folder = "mouldings" if category == "moulding" else "mats" if category == "mat" else category
    names: list[str] = []

    if filename:
        names.append(filename)
    if folder and sku:
        names.append(f"{folder}/{sku}.jpg")
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            indexed = _catalog_preview_basename_index(folder).get(f"{sku}{ext}".lower())
            if indexed:
                names.append(indexed)
        if category == "moulding":
            if sku.startswith("I") and len(sku) > 1:
                names.append(f"{folder}/{sku[1:]}.jpg")
            else:
                names.append(f"{folder}/I{sku}.jpg")

    seen: set[str] = set()
    return [name for name in names if name and not (name in seen or seen.add(name))]


def _catalog_preview_url_for_row(row: dict[str, Any]) -> str | None:
    for candidate in _catalog_preview_candidates(row):
        url = _catalog_preview_url(candidate)
        if url:
            return url
    return None


def _backfill_catalog_preview_links() -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, sku, category
        FROM catalog_items
        WHERE COALESCE(preview_filename, '') = ''
          AND category IN ('mat', 'moulding')
          AND COALESCE(sku, '') != ''
        """
    )
    rows = [dict(row) for row in cur.fetchall()]
    updated = 0
    for row in rows:
        folder = "mouldings" if row["category"] == "moulding" else "mats"
        sku = str(row["sku"]).strip()
        match = None
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            match = _catalog_preview_basename_index(folder).get(f"{sku}{ext}".lower())
            if match:
                break
        if not match:
            continue
        cur.execute("UPDATE catalog_items SET preview_filename = ? WHERE id = ?", (match, row["id"]))
        updated += 1
    conn.commit()
    conn.close()
    if updated:
        _catalog_preview_basename_index.cache_clear()
    return updated


def _extract_catalog_package_preview_assets(zip_path: Path, folder_name: str) -> set[str]:
    target_dir = PREVIEW_DIR / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)
    extracted: set[str] = set()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            if member.endswith("/"):
                continue
            filename = Path(member).name
            if not filename:
                continue
            destination = target_dir / filename
            if not destination.exists():
                destination.write_bytes(zf.read(member))
            extracted.add(f"{folder_name}/{filename}")
    _catalog_preview_basename_index.cache_clear()
    return extracted


def _catalog_package_preview_index(zip_path: Path, folder_name: str) -> set[str]:
    if not zip_path.exists():
        return set()
    with zipfile.ZipFile(zip_path) as zf:
        return {
            f"{folder_name}/{Path(member).name}"
            for member in zf.namelist()
            if not member.endswith("/") and Path(member).name
        }


def _import_local_catalog_package(source: str) -> dict[str, Any]:
    source_key = source.strip().lower()
    if source_key not in {"mats", "mouldings"}:
        raise HTTPException(status_code=400, detail="source must be mats or mouldings")

    csv_path = CATALOG_IMPORT_DIR / ("mats.csv" if source_key == "mats" else "mouldings.csv")
    zip_path = CATALOG_IMPORT_DIR / ("mats.zip" if source_key == "mats" else "mouldings.zip")
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"{csv_path.name} not found in catalog_imports folder")

    conn = get_connection()
    try:
        check_catalog_package_import_limit(conn)
        import_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        preview_index = _catalog_package_preview_index(zip_path, source_key)
        cur = conn.cursor()
        inserted = 0
        updated = 0
        skipped = 0
        duplicate_rows = 0
        bad_rows: list[dict[str, Any]] = []
        seen_keys: set[tuple[str, str]] = set()

        with csv_path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row_num, row in enumerate(reader, start=2):
                sku = (row.get("Code") or "").strip()
                description = (row.get("Description") or "").strip()
                if not sku or not description:
                    skipped += 1
                    bad_rows.append({"row": row_num, "sku": sku, "reason": "missing code or description"})
                    continue

                if source_key == "mats":
                    category = "mat"
                    width_in = _safe_float(row.get("Width"), -1)
                    height_in = _safe_float(row.get("Height"), -1)
                    rabbet_in = 0.0
                    metadata = {
                        "source": "local_catalog_mats",
                        "source_file": csv_path.name,
                        "imported_at": import_at,
                        "vendor_category": (row.get("Category") or "").strip(),
                        "price_code": (row.get("Price Code") or "").strip(),
                        "board_size": f"{format(width_in, 'g')}x{format(height_in, 'g')}" if width_in > 0 and height_in > 0 else "",
                        "core": (row.get("Core") or "").strip(),
                        "thickness": _safe_float(row.get("Thickness")),
                        "available_to": (row.get("Available to") or "").strip(),
                        "system": (row.get("System") or "").strip(),
                    }
                    malformed_fields = [name for name, value in (("Width", width_in), ("Height", height_in)) if value < 0]
                else:
                    style = (row.get("Style") or "").strip().lower()
                    category = "fillet" if "fillet" in style else "moulding"
                    width_in = _safe_float(row.get("Width in."), -1)
                    height_in = _safe_float(row.get("Height in."), -1)
                    rabbet_in = _safe_float(row.get("Rabbet in."), -1)
                    metadata = {
                        "source": "local_catalog_mouldings",
                        "source_file": csv_path.name,
                        "imported_at": import_at,
                        "vendor_category": (row.get("Category") or "").strip(),
                        "price_code": (row.get("Price Code") or "").strip(),
                        "style": (row.get("Style") or "").strip(),
                        "length_in": _safe_float(row.get("Length in.")),
                        "available_to": (row.get("Available to") or "").strip(),
                        "system": (row.get("System") or "").strip(),
                    }
                    malformed_fields = [name for name, value in (("Width in.", width_in), ("Height in.", height_in), ("Rabbet in.", rabbet_in)) if value < 0]

                if malformed_fields:
                    skipped += 1
                    bad_rows.append({"row": row_num, "sku": sku, "reason": f"invalid numeric field(s): {', '.join(malformed_fields)}"})
                    continue

                preview_filename = None
                preview_key = f"{source_key}/{sku}.jpg"
                if preview_key in preview_index:
                    preview_filename = preview_key

                vendor = (row.get("Vendor") or "").strip()
                cost = _safe_float(row.get("Price"), -1)
                if cost < 0:
                    skipped += 1
                    bad_rows.append({"row": row_num, "sku": sku, "reason": "invalid price"})
                    continue

                row_key = (vendor.lower(), sku.lower())
                if row_key in seen_keys:
                    duplicate_rows += 1
                else:
                    seen_keys.add(row_key)

                cur.execute("SELECT id FROM catalog_items WHERE sku = ? AND category = ?", (sku, category))
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE catalog_items
                        SET name = ?, cost = ?, vendor = ?, width_in = ?, height_in = ?, rabbet_in = ?,
                            preview_filename = ?, metadata_json = ?, active = 1
                        WHERE sku = ? AND category = ?
                        """,
                        (
                            description,
                            cost,
                            vendor,
                            width_in,
                            height_in,
                            rabbet_in,
                            preview_filename,
                            json.dumps(metadata),
                            sku,
                            category,
                        ),
                    )
                    updated += 1
                else:
                    check_catalog_item_limit(conn, 1)
                    cur.execute(
                        """
                        INSERT INTO catalog_items
                        (sku, name, category, cost, vendor, width_in, height_in, rabbet_in, preview_filename, metadata_json, active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """,
                        (
                            sku,
                            description,
                            category,
                            cost,
                            vendor,
                            width_in,
                            height_in,
                            rabbet_in,
                            preview_filename,
                            json.dumps(metadata),
                        ),
                    )
                    inserted += 1

        if inserted > 0 or updated > 0:
            if zip_path.exists():
                _extract_catalog_package_preview_assets(zip_path, source_key)
            increment_catalog_imports_count(conn)
        conn.commit()
        return {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "duplicate_rows": duplicate_rows,
            "preview_count": len(preview_index),
            "bad_rows": bad_rows,
        }
    finally:
        conn.close()


def _write_catalog_snapshot(target_dir: Path) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, sku, name, category, cost, vendor, width_in, height_in, rabbet_in,
               preview_filename, metadata_json, active, created_at
        FROM catalog_items
        ORDER BY id ASC
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    snapshot = target_dir / "catalog_items.csv"
    with snapshot.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id", "sku", "name", "category", "cost", "vendor", "width_in", "height_in",
                "rabbet_in", "preview_filename", "metadata_json", "active", "created_at",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def _build_order_handoff(order: dict[str, Any]) -> dict[str, str]:
    brand = _get_studio_profile()
    payload = order.get("payload", {})
    customer_name = order["customer_name"]
    quote_number = order["quote_number"]
    total = f"${order['total']:.2f}"
    layout = payload.get("design_state", {}).get("opening_layout", "single")
    layout_label = "2 openings" if layout == "diptych" else "single opening"
    subject = f"{brand['business_name']} quote {quote_number} for {customer_name}"
    email_body = (
        f"Hello {customer_name},\n\n"
        f"Your framing quote {quote_number} is ready.\n"
        f"Layout: {layout_label}\n"
        f"Total: {total}\n\n"
        f"Please attach the PDF quote and mockup JPG before sending this message.\n\n"
        f"Reply with any changes or approval.\n\n"
        f"{brand['owner']}\n{brand['phone']}\n{brand['email']}"
    )
    sms_body = (
        f"{brand['business_name']} quote {quote_number} is ready for {customer_name}. "
        f"Layout: {layout_label}. Total: {total}. "
        f"{brand['business_name']} can send the PDF quote and mockup JPG separately."
    )
    return {"email_subject": subject, "email_body": email_body, "sms_body": sms_body}


def _format_mat_layers(selected: dict[str, Any]) -> str:
    layers = selected.get("mats") or []
    if layers:
        formatted = []
        for layer in layers:
            item = layer.get("item") or {}
            label = f"{item.get('sku', '')} {item.get('name', '')}".strip() or "Not selected"
            if layer.get("slot") == "top":
                formatted.append(f"Top {label}")
            else:
                formatted.append(f"{layer.get('slot', '').title()} {label} ({float(layer.get('reveal_in', 0)):.2f} in reveal)")
        return " | ".join(formatted)
    item = selected.get("mat")
    if not item:
        return "Not selected"
    return f"{item.get('sku', '')} {item.get('name', '')}".strip()


@app.get("/api/settings")
def get_settings() -> dict[str, dict[str, float]]:
    return {"pricing": _get_settings()}


@app.post("/api/settings")
def update_settings(
    tax_rate: float = Form(...),
    markup_moulding: float = Form(...),
    markup_mat: float = Form(...),
    markup_glazing: float = Form(...),
    markup_addons: float = Form(DEFAULT_SETTINGS["markup_addons"]),
) -> dict[str, dict[str, float]]:
    _require_non_negative(tax_rate, "tax_rate")
    _require_non_negative(markup_moulding, "markup_moulding")
    _require_non_negative(markup_mat, "markup_mat")
    _require_non_negative(markup_glazing, "markup_glazing")
    _require_non_negative(markup_addons, "markup_addons")

    values = {
        "tax_rate": tax_rate,
        "markup_moulding": markup_moulding,
        "markup_mat": markup_mat,
        "markup_glazing": markup_glazing,
        "markup_addons": markup_addons,
    }
    conn = get_connection()
    cur = conn.cursor()
    for key, value in values.items():
        cur.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, str(value)),
        )
    conn.commit()
    conn.close()
    return {"pricing": values}


@app.get("/api/services")
def get_services() -> dict[str, list[dict[str, Any]]]:
    return {"services": _list_service_options()}


@app.post("/api/services")
async def update_services(request: Request) -> dict[str, list[dict[str, Any]]]:
    form = await request.form()
    conn = get_connection()
    cur = conn.cursor()

    for index, key in enumerate(SERVICE_KEYS):
        current = cur.execute("SELECT label, cost, markup, basis, active, sort_order FROM service_options WHERE key = ?", (key,)).fetchone()
        label_default = current["label"] if current else key.replace("_", " ").title()
        cost_default = float(current["cost"] if current else 0)
        markup_default = float(current["markup"] if current else 1)
        basis_default = str(current["basis"] if current else ("square_inches" if key == "backing" or key in GLAZING_SERVICE_KEYS else "count"))
        sort_default = int(current["sort_order"] if current else (index + 1) * 10)

        label = str(form.get(f"{key}_label") or label_default).strip()
        if not label:
            conn.close()
            raise HTTPException(status_code=400, detail=f"{key}_label is required")

        raw_cost = form.get(f"{key}_cost", form.get(f"{key}_price", cost_default))
        raw_markup = form.get(f"{key}_markup", markup_default)
        raw_basis = str(form.get(f"{key}_basis") or basis_default).strip()
        cost = _require_service_price(_safe_float(str(raw_cost), cost_default), f"{key}_cost")
        markup = _require_non_negative(_safe_float(str(raw_markup), markup_default), f"{key}_markup")
        basis = raw_basis if raw_basis in SERVICE_BASIS else basis_default
        active = 1 if str(form.get(f"{key}_active", current["active"] if current else 1)) in {"1", "true", "on"} else 0
        price = round(cost * markup, 2)
        cur.execute(
            """
            INSERT INTO service_options (key, label, price, cost, markup, basis, active, sort_order, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                label = excluded.label,
                price = excluded.price,
                cost = excluded.cost,
                markup = excluded.markup,
                basis = excluded.basis,
                active = excluded.active,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, label, price, cost, markup, basis, active, sort_default),
        )
    conn.commit()
    conn.close()
    return {"services": _list_service_options()}


@app.get("/api/backups")
def list_backups() -> dict[str, list[dict[str, Any]]]:
    return {"backups": _list_backups()}


@app.post("/api/backups")
def create_backup() -> dict[str, Any]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"framershaven_backup_{stamp}.zip"
    target = BACKUP_DIR / filename
    snapshot_dir = BACKUP_DIR / f"snapshot_{stamp}"
    snapshot_dir.mkdir(exist_ok=True)
    _write_catalog_snapshot(snapshot_dir)

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "database": str(db_module.DB_PATH),
        "uploads_dir": str(UPLOAD_DIR),
        "exports_dir": str(EXPORT_DIR),
    }
    (snapshot_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if db_module.DB_PATH.exists():
            archive.write(db_module.DB_PATH, arcname="studio.db")
        for base_dir, prefix in ((UPLOAD_DIR, "uploads"), (EXPORT_DIR, "exports"), (snapshot_dir, "snapshot")):
            for path in base_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, arcname=str(Path(prefix) / path.relative_to(base_dir)))

    for path in snapshot_dir.rglob("*"):
        if path.is_file():
            path.unlink()
    snapshot_dir.rmdir()
    return {"filename": filename, "download_url": f"/api/backups/{filename}"}


@app.get("/api/backups/{filename}")
def download_backup(filename: str) -> FileResponse:
    target = BACKUP_DIR / Path(filename).name
    if not target.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    return FileResponse(target, filename=target.name, media_type="application/zip")


@app.post("/api/customers")
def create_customer(
    name: str = Form(...),
    contact: str = Form(""),
    customer_email: str = Form(""),
    notes: str = Form(""),
) -> dict[str, Any]:
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Customer name is required")
    clean_contact = _require_customer_phone(contact)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO customers (name, contact, customer_email, notes, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (clean_name, clean_contact, customer_email.strip(), notes.strip()),
    )
    customer_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"customer_id": customer_id, "name": clean_name}


@app.get("/api/customers")
def list_customers(
    q: str = Query(""),
    limit: int = Query(500, ge=1, le=1000),
) -> dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM customers
        WHERE (? = '' OR name LIKE '%' || ? || '%' OR contact LIKE '%' || ? || '%' OR customer_email LIKE '%' || ? || '%')
        """,
        (q, q, q, q),
    )
    total = cur.fetchone()["count"]
    cur.execute(
        """
        SELECT id, name, contact, customer_email, notes, created_at, updated_at
        FROM customers
        WHERE (? = '' OR name LIKE '%' || ? || '%' OR contact LIKE '%' || ? || '%' OR customer_email LIKE '%' || ? || '%')
        ORDER BY updated_at DESC, id DESC
        LIMIT ?
        """,
        (q, q, q, q, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"customers": rows, "total": total, "limit": limit}


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: int) -> dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, contact, customer_email, notes, created_at, updated_at FROM customers WHERE id = ?",
        (customer_id,),
    )
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Customer not found")

    cur.execute(
        """
        SELECT id, status, total, created_at, updated_at
        FROM orders
        WHERE customer_name = ?
        ORDER BY id DESC
        LIMIT 50
        """,
        (row["name"],),
    )
    orders = [dict(r) for r in cur.fetchall()]
    for order in orders:
        order["quote_number"] = f"Q{order['id']:05d}"

    conn.close()
    return {"customer": dict(row), "orders": orders}


@app.post("/api/customers/{customer_id}")
def update_customer(
    customer_id: int,
    name: str = Form(...),
    contact: str = Form(""),
    customer_email: str | None = Form(None),
    notes: str = Form(""),
) -> dict[str, Any]:
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Customer name is required")
    clean_contact = _require_customer_phone(contact)
    email_supplied = customer_email is not None
    clean_email = customer_email.strip() if customer_email is not None else ""

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM customers WHERE id = ?", (customer_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Customer not found")

    previous_name = row["name"]
    cur.execute(
        """
        UPDATE customers
        SET name = ?, contact = ?,
            customer_email = CASE WHEN ? THEN ? ELSE customer_email END,
            notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (clean_name, clean_contact, email_supplied, clean_email, notes.strip(), customer_id),
    )
    if previous_name != clean_name:
        cur.execute(
            """
            UPDATE orders
            SET customer_name = ?, customer_contact = ?,
                customer_email = CASE WHEN ? THEN ? ELSE customer_email END,
                updated_at = CURRENT_TIMESTAMP
            WHERE customer_name = ?
            """,
            (clean_name, clean_contact, email_supplied, clean_email, previous_name),
        )
    else:
        cur.execute(
            """
            UPDATE orders
            SET customer_contact = ?,
                customer_email = CASE WHEN ? THEN ? ELSE customer_email END,
                updated_at = CURRENT_TIMESTAMP
            WHERE customer_name = ?
            """,
            (clean_contact, email_supplied, clean_email, clean_name),
        )

    conn.commit()
    conn.close()
    return {"customer_id": customer_id, "name": clean_name}


def _fetch_catalog_item(cur, item_id: int | None, category_keyword: str) -> dict[str, Any] | None:
    if not item_id:
        return None
    cur.execute(
        """
        SELECT id, sku, name, category, cost, vendor, width_in, height_in, rabbet_in, preview_filename, metadata_json
        FROM catalog_items
        WHERE id = ?
        """,
        (item_id,),
    )
    item = cur.fetchone()
    if not item:
        raise HTTPException(status_code=400, detail=f"Catalog item {item_id} not found")
    if category_keyword not in item["category"].lower():
        raise HTTPException(status_code=400, detail=f"Item {item_id} is not a {category_keyword} item")
    return dict(item)


def _fetch_service_option(cur, service_key: str | None) -> dict[str, Any] | None:
    if not service_key:
        return None
    cur.execute(
        "SELECT key, label, price, cost, markup, basis, active, sort_order, updated_at FROM service_options WHERE key = ?",
        (service_key,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=400, detail=f"Service {service_key} not found")
    service = dict(row)
    if not service["active"]:
        raise HTTPException(status_code=400, detail=f"Service {service_key} is inactive")
    return service


def _discount_amount(amount: float, item_discount_pct: float, global_discount_pct: float) -> float:
    discounted = amount * (1 - (item_discount_pct / 100.0))
    discounted *= 1 - (global_discount_pct / 100.0)
    return round(max(discounted, 0.0), 2)


def _service_variable(service: dict[str, Any], outside_w: float, outside_h: float, count: float) -> float:
    basis = str(service.get("basis") or "count")
    if basis == "square_inches":
        return max(outside_w * outside_h, 0.0)
    if basis == "united_inches":
        return max(outside_w + outside_h, 0.0)
    return max(count, 0.0)


def _service_line_amount(service: dict[str, Any], outside_w: float, outside_h: float, count: float) -> tuple[float, float]:
    variable = _service_variable(service, outside_w, outside_h, count)
    amount = float(service.get("cost") or 0) * float(service.get("markup") or 1) * variable
    return round(max(amount, 0.0), 2), round(variable, 2)


def _build_service_selections(
    cur,
    global_discount_pct: float,
    selection_inputs: dict[str, dict[str, Any]],
    other_entries: list[dict[str, Any]],
    outside_w: float,
    outside_h: float,
) -> tuple[dict[str, Any], dict[str, float]]:
    selected: dict[str, Any] = {}
    line_items: dict[str, float] = {}

    for key in QUOTE_SERVICE_KEYS:
        entry = selection_inputs[key]
        service = _fetch_service_option(cur, entry["service_key"])
        count = max(float(entry.get("count", 1.0) or 0), 0.0)
        amount = 0.0
        variable = 0.0
        if service:
            amount, variable = _service_line_amount(service, outside_w, outside_h, count)
        selected[key] = {
            "service": service,
            "discount_pct": entry["discount_pct"],
            "count": count,
            "variable": variable,
            "basis": service.get("basis") if service else None,
        }
        if service and amount > 0:
            line_items[key] = _discount_amount(amount, entry["discount_pct"], global_discount_pct)

    selected["custom"] = []
    for idx, entry in enumerate(other_entries, start=1):
        label = entry["label"].strip()
        amount = round(entry["amount"], 2)
        if not label and amount <= 0:
            continue
        display_label = label or f"Other {idx}"
        discounted = _discount_amount(amount, entry["discount_pct"], global_discount_pct)
        if discounted <= 0:
            continue
        selected["custom"].append(
            {
                "label": display_label,
                "amount": amount,
                "discount_pct": entry["discount_pct"],
            }
        )
        line_items[display_label] = discounted

    return selected, line_items


def _build_mat_layers(
    cur,
    top_mat_id: int | None,
    second_mat_id: int | None,
    third_mat_id: int | None,
    second_reveal_in: float,
    third_reveal_in: float,
) -> list[dict[str, Any]]:
    layers = []
    top_mat = _fetch_catalog_item(cur, top_mat_id, "mat")
    if top_mat:
        layers.append({"slot": "top", "item": top_mat, "reveal_in": 0.0})

    if second_mat_id:
        if not top_mat:
            raise HTTPException(status_code=400, detail="second_mat_id requires top_mat_id")
        layers.append(
            {
                "slot": "second",
                "item": _fetch_catalog_item(cur, second_mat_id, "mat"),
                "reveal_in": second_reveal_in,
            }
        )

    if third_mat_id:
        if not second_mat_id:
            raise HTTPException(status_code=400, detail="third_mat_id requires second_mat_id")
        layers.append(
            {
                "slot": "third",
                "item": _fetch_catalog_item(cur, third_mat_id, "mat"),
                "reveal_in": third_reveal_in,
            }
        )

    return layers


@app.post("/api/catalog/items")
def create_catalog_item(
    sku: str = Form(...),
    name: str = Form(...),
    category: str = Form(...),
    cost: float = Form(...),
    vendor: str = Form(""),
    width_in: float = Form(0.0),
    height_in: float = Form(0.0),
    rabbet_in: float = Form(0.0),
) -> dict[str, Any]:
    clean_sku = sku.strip()
    clean_name = name.strip()
    if not clean_sku or not clean_name or not category.strip():
        raise HTTPException(status_code=400, detail="sku, name, and category are required")
    clean_category = _normalize_catalog_category(category)
    _require_non_negative(cost, "cost")
    _require_non_negative(width_in, "width_in")
    _require_non_negative(height_in, "height_in")
    _require_non_negative(rabbet_in, "rabbet_in")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM catalog_items WHERE sku = ? AND category = ?", (clean_sku, clean_category))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Catalog item already exists for sku/category")
        check_catalog_item_limit(conn, 1)

        cur.execute(
            """
            INSERT INTO catalog_items (sku, name, category, cost, vendor, width_in, height_in, rabbet_in, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (clean_sku, clean_name, clean_category, cost, vendor.strip(), width_in, height_in, rabbet_in),
        )
        item_id = cur.lastrowid
        conn.commit()
        return {"item_id": item_id, "sku": clean_sku}
    finally:
        conn.close()


@app.post("/api/catalog/items/{item_id}")
def update_catalog_item(
    item_id: int,
    sku: str = Form(...),
    name: str = Form(...),
    category: str = Form(...),
    cost: float = Form(...),
    vendor: str = Form(""),
    width_in: float = Form(0.0),
    height_in: float = Form(0.0),
    rabbet_in: float = Form(0.0),
    active: int = Form(1),
) -> dict[str, Any]:
    clean_sku = sku.strip()
    clean_name = name.strip()
    if not clean_sku or not clean_name or not category.strip():
        raise HTTPException(status_code=400, detail="sku, name, and category are required")
    clean_category = _normalize_catalog_category(category)
    _require_non_negative(cost, "cost")
    _require_non_negative(width_in, "width_in")
    _require_non_negative(height_in, "height_in")
    _require_non_negative(rabbet_in, "rabbet_in")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM catalog_items WHERE id = ?", (item_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Catalog item not found")

        cur.execute(
            """
            UPDATE catalog_items
            SET sku = ?, name = ?, category = ?, cost = ?, vendor = ?, width_in = ?, height_in = ?, rabbet_in = ?, active = ?
            WHERE id = ?
            """,
            (clean_sku, clean_name, clean_category, cost, vendor.strip(), width_in, height_in, rabbet_in, 1 if active else 0, item_id),
        )
        conn.commit()
        return {"item_id": item_id, "sku": clean_sku}
    finally:
        conn.close()


@app.post("/api/catalog/items/{item_id}/texture")
async def upload_catalog_texture(item_id: int, file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a texture photo for a moulding catalog item.

    The photo should be a cropped strip of the moulding profile
    (cross-section or flat face) that will be tiled around the frame.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPG/PNG allowed")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, category, sku FROM catalog_items WHERE id = ?", (item_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Catalog item not found")
    category = row["category"]
    sku = row["sku"].replace(" ", "_").replace("/", "_")
    # Save to catalog_previews/{category}/{sku}_texture.jpg
    subdir = PREVIEW_DIR / category
    subdir.mkdir(exist_ok=True)
    ext = ".jpg" if file.content_type == "image/jpeg" else ".png"
    filename = f"{category}/{sku}_texture{ext}"
    dest = PREVIEW_DIR / filename
    data = await file.read()
    with open(dest, "wb") as fh:
        fh.write(data)
    cur.execute(
        "UPDATE catalog_items SET preview_filename = ? WHERE id = ?",
        (filename, item_id),
    )
    conn.commit()
    conn.close()
    _catalog_preview_basename_index.cache_clear()
    return {"item_id": item_id, "preview_url": f"/catalog-previews/{filename}"}


@app.post("/api/catalog/import")
async def import_catalog(file: UploadFile = File(...)) -> dict[str, int]:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV only")

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc
    reader = csv.DictReader(io.StringIO(text))

    required = {"sku", "name", "category", "cost", "width_in"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise HTTPException(status_code=400, detail="Missing CSV headers")

    conn = get_connection()
    try:
        cur = conn.cursor()
        valid_rows: list[dict[str, Any]] = []
        inserted = 0
        updated = 0
        skipped = 0
        for row in reader:
            try:
                name = row.get("name", "").strip()
                sku = row.get("sku", "").strip()
                raw_category = row.get("category", "").strip()
                cost = float(row.get("cost", -1))
                if not name or not sku or not raw_category or cost < 0:
                    skipped += 1
                    continue
                try:
                    category = _normalize_catalog_category(raw_category)
                except HTTPException:
                    skipped += 1
                    continue
                width_in = float(row.get("width_in") or 0)
                valid_rows.append(
                    {
                        "sku": sku,
                        "name": name,
                        "category": category,
                        "cost": cost,
                        "width_in": width_in,
                    }
                )
            except (TypeError, ValueError):
                skipped += 1

        new_catalog_keys: set[tuple[str, str]] = set()
        for row in valid_rows:
            cur.execute("SELECT id FROM catalog_items WHERE sku = ? AND category = ?", (row["sku"], row["category"]))
            if cur.fetchone() is None:
                new_catalog_keys.add((row["sku"], row["category"]))
        check_catalog_item_limit(conn, len(new_catalog_keys))

        for row in valid_rows:
            cur.execute("SELECT id FROM catalog_items WHERE sku = ? AND category = ?", (row["sku"], row["category"]))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE catalog_items
                    SET name = ?, category = ?, cost = ?, width_in = ?, active = 1
                    WHERE sku = ? AND category = ?
                    """,
                    (row["name"], row["category"], row["cost"], row["width_in"], row["sku"], row["category"]),
                )
                updated += 1
            else:
                cur.execute(
                    """
                    INSERT INTO catalog_items (sku, name, category, cost, width_in, active)
                    VALUES (?, ?, ?, ?, ?, 1)
                    """,
                    (row["sku"], row["name"], row["category"], row["cost"], row["width_in"]),
                )
                inserted += 1

        conn.commit()
        return {"inserted": inserted, "updated": updated, "skipped": skipped}
    finally:
        conn.close()


@app.post("/api/catalog/import/package")
def import_local_catalog_package(source: str = Form(...)) -> dict[str, Any]:
    return _import_local_catalog_package(source)


def _normalize_inventory_key(value: str | None) -> str:
    cleaned = (value or "").strip().lower()
    return "".join(ch for ch in cleaned if ch.isalnum())


def _coerce_inventory_count(raw: Any, field_name: str) -> int:
    try:
        count = int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} must be an integer") from exc
    if count < 0:
        raise HTTPException(status_code=400, detail=f"{field_name} must be non-negative")
    return count


def _inventory_match_key(item: dict[str, Any]) -> str:
    for field in ("sku", "shopify_sku", "barcode", "name"):
        key = _normalize_inventory_key(item.get(field))
        if key:
            return key
    return ""


@app.post("/api/inventory/reconcile")
def reconcile_inventory(payload: dict[str, Any]) -> dict[str, Any]:
    shelf_rows = payload.get("shelf_counts")
    shopify_rows = payload.get("shopify_counts")
    discrepancy_threshold = payload.get("threshold", 1)

    if not isinstance(shelf_rows, list) or not isinstance(shopify_rows, list):
        raise HTTPException(status_code=400, detail="shelf_counts and shopify_counts must be arrays")

    try:
        threshold = int(discrepancy_threshold)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="threshold must be an integer") from exc
    if threshold < 0:
        raise HTTPException(status_code=400, detail="threshold must be non-negative")

    shelf_index: dict[str, dict[str, Any]] = {}
    shopify_index: dict[str, dict[str, Any]] = {}
    warnings: list[dict[str, Any]] = []

    for idx, row in enumerate(shelf_rows):
        if not isinstance(row, dict):
            raise HTTPException(status_code=400, detail=f"shelf_counts[{idx}] must be an object")
        key = _inventory_match_key(row)
        if not key:
            warnings.append({"type": "unmatchable_shelf_row", "index": idx, "row": row})
            continue
        if key in shelf_index:
            warnings.append({"type": "duplicate_shelf_match_key", "index": idx, "key": key, "row": row})
            continue
        shelf_index[key] = row

    for idx, row in enumerate(shopify_rows):
        if not isinstance(row, dict):
            raise HTTPException(status_code=400, detail=f"shopify_counts[{idx}] must be an object")
        key = _inventory_match_key(row)
        if not key:
            warnings.append({"type": "unmatchable_shopify_row", "index": idx, "row": row})
            continue
        if key in shopify_index:
            warnings.append({"type": "duplicate_shopify_match_key", "index": idx, "key": key, "row": row})
            continue
        shopify_index[key] = row

    all_keys = sorted(set(shelf_index) | set(shopify_index))
    discrepancies: list[dict[str, Any]] = []
    matched: list[dict[str, Any]] = []

    for key in all_keys:
        shelf = shelf_index.get(key)
        shopify = shopify_index.get(key)
        product_label = (shelf or shopify or {}).get("name") or (shelf or shopify or {}).get("sku") or key
        shelf_count = _coerce_inventory_count((shelf or {}).get("count"), f"shelf_counts[{product_label}].count") if shelf else None
        shopify_count = _coerce_inventory_count((shopify or {}).get("count"), f"shopify_counts[{product_label}].count") if shopify else None
        delta = None if shelf_count is None or shopify_count is None else shelf_count - shopify_count

        record = {
            "match_key": key,
            "product": product_label,
            "shelf_count": shelf_count,
            "shopify_count": shopify_count,
            "delta": delta,
        }

        if shelf is None or shopify is None:
            record["status"] = "missing_match"
            discrepancies.append(record)
            continue

        if abs(delta or 0) > threshold:
            record["status"] = "discrepant"
            discrepancies.append(record)
        else:
            record["status"] = "matched"
            matched.append(record)

    return {
        "threshold": threshold,
        "matched": matched,
        "discrepancies": discrepancies,
        "warnings": warnings,
        "summary": {
            "matched": len(matched),
            "discrepant": len(discrepancies),
            "warnings": len(warnings),
            "total_products": len(all_keys),
        },
    }


@app.get("/api/catalog/search")
def search_catalog(
    q: str = Query(""),
    category: str = Query(""),
    limit: int = Query(300, ge=0),
) -> dict[str, list[dict[str, Any]]]:
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        SELECT id, sku, name, category, cost, vendor, width_in, height_in, rabbet_in, preview_filename, metadata_json
        FROM catalog_items
        WHERE (? = '' OR name LIKE '%' || ? || '%' OR sku LIKE '%' || ? || '%')
          AND (? = '' OR category LIKE '%' || ? || '%')
        ORDER BY id DESC
    """
    params: list[Any] = [q, q, q, category, category]
    if limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    cur.execute(sql, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    for row in rows:
        row["preview_url"] = _catalog_preview_url_for_row(row)
    conn.close()
    return {"items": rows}


@app.post("/api/images/upload")
async def upload_image(
    file: UploadFile = File(...),
    width_in: float = Form(...),
    height_in: float = Form(...),
    ratio_label: str = Form("free"),
    crop_json: str = Form("{}"),
    rotation_deg: int = Form(0),
) -> dict[str, Any]:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPG/PNG allowed")
    _require_positive(width_in, "width_in")
    _require_positive(height_in, "height_in")
    if rotation_deg % 90 != 0:
        raise HTTPException(status_code=400, detail="rotation_deg must be a multiple of 90")
    crop_payload = _parse_json_object(crop_json, "crop_json")
    crop_json = json.dumps(crop_payload)

    ext = Path(file.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png"}:
        raise HTTPException(status_code=400, detail="Only JPG/PNG allowed")

    safe_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}_{Path(file.filename).name}"
    target = UPLOAD_DIR / safe_name
    content = await file.read()

    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image") from exc
    if rotation_deg:
        image = image.rotate(-rotation_deg, expand=True)
    image.save(target)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO images (filename, path, width_in, height_in, ratio_label, crop_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (safe_name, str(target), width_in, height_in, ratio_label, crop_json),
    )
    image_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": image_id,
        "filename": safe_name,
        "url": f"/uploads/{safe_name}",
        "width_in": width_in,
        "height_in": height_in,
        "ratio_label": ratio_label,
        "crop_json": crop_payload,
    }


@app.get("/api/images")
def list_images() -> dict[str, list[dict[str, Any]]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, filename, width_in, height_in, ratio_label, crop_json, created_at
        FROM images
        ORDER BY id DESC
        LIMIT 150
        """
    )
    rows = [_image_payload(r) for r in cur.fetchall()]
    conn.close()
    return {"images": rows}


@app.patch("/api/images/{image_id}")
def update_image_metadata(
    image_id: int,
    width_in: float = Form(...),
    height_in: float = Form(...),
    ratio_label: str = Form("free"),
    crop_json: str = Form("{}"),
) -> dict[str, Any]:
    _require_positive(width_in, "width_in")
    _require_positive(height_in, "height_in")
    crop_payload = _parse_json_object(crop_json, "crop_json")
    crop_json = json.dumps(crop_payload)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE images
        SET width_in = ?, height_in = ?, ratio_label = ?, crop_json = ?
        WHERE id = ?
        """,
        (width_in, height_in, ratio_label, crop_json, image_id),
    )
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Image {image_id} not found")
    conn.commit()
    cur.execute(
        """
        SELECT id, filename, width_in, height_in, ratio_label, crop_json, created_at
        FROM images
        WHERE id = ?
        """,
        (image_id,),
    )
    row = cur.fetchone()
    conn.close()
    return _image_payload(row)


@app.post("/api/quotes/calculate")
def calculate(
    width_in: float = Form(...),
    height_in: float = Form(...),
    moulding_cost_ft: float = Form(0),
    mat_cost_sqft: float = Form(0),
    glazing_cost_sqft: float = Form(0.0),
    labor_flat: float = Form(20.0),
    moulding_id: int | None = Form(None),
    mat_id: int | None = Form(None),
    top_mat_id: int | None = Form(None),
    second_mat_id: int | None = Form(None),
    third_mat_id: int | None = Form(None),
    glazing_id: int | None = Form(None),
    glazing_key: str = Form(""),
    backing_key: str = Form(""),
    mounting_key: str = Form(""),
    frame_mounting_key: str = Form(""),
    printing_key: str = Form(""),
    various_key: str = Form(""),
    assembly_key: str = Form(""),
    royalties_key: str = Form(""),
    custom_1_key: str = Form(""),
    custom_2_key: str = Form(""),
    image_id: int | None = Form(None),
    mat_border_in: float = Form(2.0),
    second_mat_reveal_in: float = Form(0.25),
    third_mat_reveal_in: float = Form(0.25),
    global_discount_pct: float = Form(0.0),
    backing_count: float = Form(1.0),
    mounting_count: float = Form(1.0),
    frame_mounting_count: float = Form(1.0),
    printing_count: float = Form(1.0),
    various_count: float = Form(1.0),
    assembly_count: float = Form(1.0),
    royalties_count: float = Form(1.0),
    custom_1_count: float = Form(1.0),
    custom_2_count: float = Form(1.0),
    backing_discount_pct: float = Form(0.0),
    mounting_discount_pct: float = Form(0.0),
    frame_mounting_discount_pct: float = Form(0.0),
    printing_discount_pct: float = Form(0.0),
    various_discount_pct: float = Form(0.0),
    assembly_discount_pct: float = Form(0.0),
    royalties_discount_pct: float = Form(0.0),
    custom_1_discount_pct: float = Form(0.0),
    custom_2_discount_pct: float = Form(0.0),
    other_label: str = Form(""),
    other_amount: float = Form(0.0),
    other_discount_pct: float = Form(0.0),
    other2_label: str = Form(""),
    other2_amount: float = Form(0.0),
    other2_discount_pct: float = Form(0.0),
) -> dict[str, Any]:
    _require_positive(width_in, "width_in")
    _require_positive(height_in, "height_in")
    _require_non_negative(moulding_cost_ft, "moulding_cost_ft")
    _require_non_negative(mat_cost_sqft, "mat_cost_sqft")
    _require_non_negative(glazing_cost_sqft, "glazing_cost_sqft")
    _require_non_negative(labor_flat, "labor_flat")
    _require_non_negative(mat_border_in, "mat_border_in")
    _require_non_negative(second_mat_reveal_in, "second_mat_reveal_in")
    _require_non_negative(third_mat_reveal_in, "third_mat_reveal_in")
    _require_non_negative(global_discount_pct, "global_discount_pct")
    for field_name, value in {
        "backing_discount_pct": backing_discount_pct,
        "mounting_discount_pct": mounting_discount_pct,
        "frame_mounting_discount_pct": frame_mounting_discount_pct,
        "printing_discount_pct": printing_discount_pct,
        "various_discount_pct": various_discount_pct,
        "assembly_discount_pct": assembly_discount_pct,
        "royalties_discount_pct": royalties_discount_pct,
        "custom_1_discount_pct": custom_1_discount_pct,
        "custom_2_discount_pct": custom_2_discount_pct,
        "backing_count": backing_count,
        "mounting_count": mounting_count,
        "frame_mounting_count": frame_mounting_count,
        "printing_count": printing_count,
        "various_count": various_count,
        "assembly_count": assembly_count,
        "royalties_count": royalties_count,
        "custom_1_count": custom_1_count,
        "custom_2_count": custom_2_count,
        "other_amount": other_amount,
        "other_discount_pct": other_discount_pct,
        "other2_amount": other2_amount,
        "other2_discount_pct": other2_discount_pct,
    }.items():
        _require_non_negative(value, field_name)

    settings = _get_settings()
    conn = get_connection()
    cur = conn.cursor()
    moulding_item = _fetch_catalog_item(cur, moulding_id, "mould")
    mat_layers = _build_mat_layers(
        cur,
        top_mat_id or mat_id,
        second_mat_id,
        third_mat_id,
        second_mat_reveal_in,
        third_mat_reveal_in,
    )
    glazing_item = _fetch_catalog_item(cur, glazing_id, "glaz")
    _fetch_image(cur, image_id)
    outside_w = width_in + (2 * mat_border_in)
    outside_h = height_in + (2 * mat_border_in)
    glazing_service = _fetch_service_option(cur, glazing_key)
    glazing_line_items: dict[str, float] = {}
    if glazing_service:
        if glazing_service["key"] not in GLAZING_SERVICE_KEYS:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Service {glazing_key} is not a glazing option")
        glazing_amount, glazing_variable = _service_line_amount(glazing_service, outside_w, outside_h, 1)
        glazing_item = {
            "key": glazing_service["key"],
            "sku": "",
            "name": glazing_service["label"],
            "category": "glazing",
            "cost": glazing_service["cost"],
            "markup": glazing_service["markup"],
            "basis": glazing_service["basis"],
            "variable": glazing_variable,
        }
        if glazing_amount > 0:
            glazing_line_items["glazing"] = _discount_amount(glazing_amount, 0, global_discount_pct)
    addon_selected, addon_line_items = _build_service_selections(
        cur,
        global_discount_pct,
        {
            "backing": {"service_key": backing_key, "discount_pct": backing_discount_pct, "count": backing_count},
            "mounting": {"service_key": mounting_key, "discount_pct": mounting_discount_pct, "count": mounting_count},
            "frame_mounting": {"service_key": frame_mounting_key, "discount_pct": frame_mounting_discount_pct, "count": frame_mounting_count},
            "printing": {"service_key": printing_key, "discount_pct": printing_discount_pct, "count": printing_count},
            "various": {"service_key": various_key, "discount_pct": various_discount_pct, "count": various_count},
            "assembly": {"service_key": assembly_key, "discount_pct": assembly_discount_pct, "count": assembly_count},
            "royalties": {"service_key": royalties_key, "discount_pct": royalties_discount_pct, "count": royalties_count},
            "custom_1": {"service_key": custom_1_key, "discount_pct": custom_1_discount_pct, "count": custom_1_count},
            "custom_2": {"service_key": custom_2_key, "discount_pct": custom_2_discount_pct, "count": custom_2_count},
        },
        [
            {"label": other_label, "amount": other_amount, "discount_pct": other_discount_pct},
            {"label": other2_label, "amount": other2_amount, "discount_pct": other2_discount_pct},
        ],
        outside_w,
        outside_h,
    )
    addon_line_items.update(glazing_line_items)

    if moulding_item:
        moulding_cost_ft = round(moulding_item["cost"] * settings["markup_moulding"], 2)
    if mat_layers:
        mat_cost_sqft = round(
            sum(float(layer["item"]["cost"]) * settings["markup_mat"] for layer in mat_layers),
            2,
        )
    if glazing_item and not glazing_service:
        glazing_cost_sqft = round(glazing_item["cost"] * settings["markup_glazing"], 2)

    try:
        result = calculate_quote(
            QuoteRequest(
                width_in=width_in,
                height_in=height_in,
                moulding_cost_ft=moulding_cost_ft,
                mat_cost_sqft=mat_cost_sqft,
                mat_border_in=mat_border_in,
                glazing_cost_sqft=glazing_cost_sqft,
                labor_flat=labor_flat,
                tax_rate=settings["tax_rate"],
                extra_line_items=addon_line_items,
            )
        )
    except ValueError as exc:
        conn.close()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    conn.close()

    selected = {
        "moulding": moulding_item,
        "mat": mat_layers[0]["item"] if mat_layers else None,
        "mats": mat_layers,
        "glazing": glazing_item,
        "addons": addon_selected,
        "image_id": image_id,
        "mat_border_in": mat_border_in,
        "subject_width_in": width_in,
        "subject_height_in": height_in,
        "outside_width_in": outside_w,
        "outside_height_in": outside_h,
        "global_discount_pct": global_discount_pct,
    }
    return {
        "perimeter_ft": result.perimeter_ft,
        "area_sqft": result.area_sqft,
        "line_items": result.line_items,
        "selected": selected,
        "pricing_rules": settings,
        "subtotal": result.subtotal,
        "tax": result.tax,
        "total": result.total,
    }


@app.post("/api/orders")
def create_order(
    customer_name: str = Form(...),
    customer_contact: str = Form(""),
    customer_email: str | None = Form(None),
    payload_json: str = Form(...),
    subtotal: float = Form(...),
    tax: float = Form(...),
    total: float = Form(...),
) -> dict[str, Any]:
    clean_name = customer_name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Customer name is required")
    clean_contact = _require_customer_phone(customer_contact)
    email_supplied = customer_email is not None
    clean_email = customer_email.strip() if customer_email is not None else ""
    _require_non_negative(subtotal, "subtotal")
    _require_non_negative(tax, "tax")
    _require_non_negative(total, "total")
    _parse_json_object(payload_json, "payload_json")

    conn = get_connection()
    check_saved_orders_quotes_limit(conn, 1)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO orders (customer_name, customer_contact, customer_email, status, payload_json, subtotal, tax, total)
        VALUES (?, ?, ?, 'quote', ?, ?, ?, ?)
        """,
        (clean_name, clean_contact, clean_email, payload_json, subtotal, tax, total),
    )
    oid = cur.lastrowid
    cur.execute("SELECT id FROM customers WHERE name = ?", (clean_name,))
    existing_customer = cur.fetchone()
    if existing_customer:
        cur.execute(
            """
            UPDATE customers
            SET contact = ?,
                customer_email = CASE WHEN ? THEN ? ELSE customer_email END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (clean_contact, email_supplied, clean_email, existing_customer["id"]),
        )
    else:
        cur.execute(
            """
            INSERT INTO customers (name, contact, customer_email, notes, updated_at)
            VALUES (?, ?, ?, '', CURRENT_TIMESTAMP)
            """,
            (clean_name, clean_contact, clean_email),
        )
    cur.execute("INSERT INTO order_status_history (order_id, status, note) VALUES (?, 'quote', 'Quote created')", (oid,))
    conn.commit()
    conn.close()
    return {"order_id": oid, "quote_number": f"Q{oid:05d}", "status": "quote"}


@app.get("/api/orders")
def list_orders(
    q: str = Query(""),
    status: str = Query(""),
    limit: int = Query(500, ge=1, le=1000),
) -> dict[str, Any]:
    if status and status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status filter")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM orders
        WHERE (? = '' OR status = ?)
          AND (? = '' OR customer_name LIKE '%' || ? || '%' OR customer_contact LIKE '%' || ? || '%'
               OR customer_email LIKE '%' || ? || '%' OR id LIKE '%' || ? || '%')
        """,
        (status, status, q, q, q, q, q),
    )
    total = cur.fetchone()["count"]
    cur.execute(
        """
        SELECT id, customer_name, customer_contact, customer_email, status, approved_at, completed_at, invoiced_at,
               subtotal, tax, total, created_at, updated_at
        FROM orders
        WHERE (? = '' OR status = ?)
          AND (? = '' OR customer_name LIKE '%' || ? || '%' OR customer_contact LIKE '%' || ? || '%'
               OR customer_email LIKE '%' || ? || '%' OR id LIKE '%' || ? || '%')
        ORDER BY id DESC
        LIMIT ?
        """,
        (status, status, q, q, q, q, q, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    for row in rows:
        row["quote_number"] = f"Q{row['id']:05d}"
        row["balance"] = _order_balance(row)
        row["next_action"] = _order_next_action(row)
    conn.close()
    return {"orders": rows, "total": total, "limit": limit}


@app.get("/api/orders/{order_id}")
def get_order(order_id: int) -> dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, customer_name, customer_contact, customer_email, status, approved_at, completed_at, invoiced_at,
               payload_json, subtotal, tax, total, created_at, updated_at
        FROM orders
        WHERE id = ?
        """,
        (order_id,),
    )
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    cur.execute("SELECT status, note, created_at FROM order_status_history WHERE order_id = ? ORDER BY id ASC", (order_id,))
    history = [dict(r) for r in cur.fetchall()]
    order = dict(row)
    order["quote_number"] = f"Q{order_id:05d}"
    try:
        order["payload"] = _parse_json_object(order["payload_json"], "payload_json")
    except HTTPException:
        order["payload"] = {"warning": "Stored payload is invalid JSON"}
    conn.close()
    return {"order": order, "history": history}


@app.get("/api/orders/{order_id}/handoff")
def get_order_handoff(order_id: int) -> dict[str, Any]:
    detail = get_order(order_id)
    order = detail["order"]
    handoff = _build_order_handoff(order)
    quote_pdf_url = f"/api/orders/{order_id}/export?format=pdf&document=quote"
    preview_jpg_url = f"/api/orders/{order_id}/export?format=jpg"
    return {
        "order_id": order_id,
        "quote_number": order["quote_number"],
        "customer_contact": order["customer_contact"],
        "customer_email": order["customer_email"] or "",
        "customer_phone": order["customer_contact"] or "",
        "quote_pdf_url": quote_pdf_url,
        "preview_jpg_url": preview_jpg_url,
        "email_subject": handoff["email_subject"],
        "email_body": handoff["email_body"],
        "sms_body": handoff["sms_body"],
    }


@app.post("/api/orders/{order_id}/status")
def update_status(
    order_id: int,
    status: str = Form(...),
    note: str = Form(""),
    customer_approved: str = Form(""),
    work_completed: str = Form(""),
) -> dict[str, Any]:
    if status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, customer_name, customer_contact, approved_at, completed_at FROM orders WHERE id = ?", (order_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    current = row["status"]
    allowed = {current, STATUS_NEXT[current]}
    if current == "invoice":
        allowed.add("work_order")
    if status not in allowed:
        conn.close()
        next_status = STATUS_NEXT[current]
        detail = f"Transition from {current} must go to {next_status}"
        if current == "invoice":
            detail = "Invoice can stay invoice or return to work_order"
        raise HTTPException(status_code=400, detail=detail)

    if status in {"work_order", "invoice"}:
        try:
            _require_customer_phone(row["customer_contact"] or "")
        except HTTPException:
            conn.close()
            raise
        if not (row["customer_name"] or "").strip():
            conn.close()
            raise HTTPException(status_code=400, detail="Customer name is required")
    if current == "quote" and status == "work_order" and not (row["approved_at"] or _form_truthy(customer_approved)):
        conn.close()
        raise HTTPException(status_code=400, detail="Customer approval is required before creating a work order")
    if current == "work_order" and status == "invoice" and not (row["completed_at"] or _form_truthy(work_completed)):
        conn.close()
        raise HTTPException(status_code=400, detail="Work order must be marked done before creating an invoice")

    approved_at_sql = "approved_at"
    completed_at_sql = "completed_at"
    invoiced_at_sql = "invoiced_at"
    if current == "quote" and status == "work_order":
        approved_at_sql = "COALESCE(approved_at, CURRENT_TIMESTAMP)"
    if current == "work_order" and status == "invoice":
        completed_at_sql = "CURRENT_TIMESTAMP"
        invoiced_at_sql = "CURRENT_TIMESTAMP"
    if current == "invoice" and status == "work_order":
        completed_at_sql = "NULL"
        invoiced_at_sql = "NULL"

    cur.execute(
        f"""
        UPDATE orders
        SET status = ?,
            approved_at = {approved_at_sql},
            completed_at = {completed_at_sql},
            invoiced_at = {invoiced_at_sql},
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, order_id),
    )
    cur.execute(
        "INSERT INTO order_status_history (order_id, status, note) VALUES (?, ?, ?)",
        (order_id, status, note or f"Status set to {status}"),
    )
    conn.commit()
    cur.execute("SELECT approved_at, completed_at, invoiced_at FROM orders WHERE id = ?", (order_id,))
    updated = cur.fetchone()
    conn.close()
    return {
        "order_id": order_id,
        "status": status,
        "approved_at": updated["approved_at"],
        "completed_at": updated["completed_at"],
        "invoiced_at": updated["invoiced_at"],
    }


@app.post("/api/orders/{order_id}/notes")
def add_order_note(order_id: int, note: str = Form(...)) -> dict[str, Any]:
    clean_note = note.strip()
    if not clean_note:
        raise HTTPException(status_code=400, detail="Note is required")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    cur.execute(
        "INSERT INTO order_status_history (order_id, status, note) VALUES (?, ?, ?)",
        (order_id, row["status"], clean_note),
    )
    conn.commit()
    conn.close()
    return {"order_id": order_id, "note": clean_note}


@app.post("/api/orders/{order_id}")
def update_order(
    order_id: int,
    customer_name: str = Form(...),
    customer_contact: str = Form(""),
    customer_email: str | None = Form(None),
    note: str = Form("Order details edited"),
    payload_json: str | None = Form(None),
    subtotal: float | None = Form(None),
    tax: float | None = Form(None),
    total: float | None = Form(None),
) -> dict[str, Any]:
    clean_name = customer_name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Customer name is required")
    clean_contact = _require_customer_phone(customer_contact)
    email_supplied = customer_email is not None
    clean_email = customer_email.strip() if customer_email is not None else ""
    updates_quote_payload = payload_json is not None or subtotal is not None or tax is not None or total is not None
    if updates_quote_payload:
        if payload_json is None or subtotal is None or tax is None or total is None:
            raise HTTPException(status_code=400, detail="payload_json, subtotal, tax, and total are required when editing quote contents")
        _parse_json_object(payload_json, "payload_json")
        _require_non_negative(subtotal, "subtotal")
        _require_non_negative(tax, "tax")
        _require_non_negative(total, "total")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, status FROM orders WHERE id = ?", (order_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    if updates_quote_payload:
        cur.execute(
            """
            UPDATE orders
            SET customer_name = ?, customer_contact = ?,
                customer_email = CASE WHEN ? THEN ? ELSE customer_email END,
                payload_json = ?,
                subtotal = ?, tax = ?, total = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (clean_name, clean_contact, email_supplied, clean_email, payload_json, subtotal, tax, total, order_id),
        )
    else:
        cur.execute(
            """
            UPDATE orders
            SET customer_name = ?, customer_contact = ?,
                customer_email = CASE WHEN ? THEN ? ELSE customer_email END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (clean_name, clean_contact, email_supplied, clean_email, order_id),
        )
    cur.execute(
        "INSERT INTO order_status_history (order_id, status, note) VALUES (?, ?, ?)",
        (order_id, row["status"], note or "Order details edited"),
    )

    cur.execute("SELECT id FROM customers WHERE name = ?", (clean_name,))
    existing_customer = cur.fetchone()
    if existing_customer:
        cur.execute(
            """
            UPDATE customers
            SET contact = ?,
                customer_email = CASE WHEN ? THEN ? ELSE customer_email END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (clean_contact, email_supplied, clean_email, existing_customer["id"]),
        )
    else:
        cur.execute(
            """
            INSERT INTO customers (name, contact, customer_email, notes, updated_at)
            VALUES (?, ?, ?, '', CURRENT_TIMESTAMP)
            """,
            (clean_name, clean_contact, clean_email),
        )

    conn.commit()
    conn.close()
    return {"order_id": order_id, "customer_name": clean_name}


@app.get("/api/orders/export.csv")
def export_orders_csv() -> FileResponse:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, customer_name, customer_contact, customer_email, status, approved_at, completed_at, invoiced_at,
               subtotal, tax, total, created_at, updated_at
        FROM orders
        ORDER BY id DESC
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    target = EXPORT_DIR / "orders_export.csv"
    with target.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "quote_number", "id", "customer_name", "customer_contact", "customer_email", "status",
                "approved_at", "completed_at", "invoiced_at",
                "subtotal", "tax", "total", "created_at", "updated_at",
            ],
        )
        writer.writeheader()
        for row in rows:
            row["quote_number"] = f"Q{row['id']:05d}"
            writer.writerow(row)
    return FileResponse(target, filename=target.name, media_type="text/csv")


def _export_quote_image(order: dict[str, Any], payload: dict[str, Any], target: Path) -> None:
    brand = _get_studio_profile()
    def material_label(item: dict[str, Any] | None) -> str:
        if not item:
            return "Not selected"
        return f"{item.get('sku', '')} {item.get('name', '')}".strip()

    img = Image.new("RGB", (1400, 1800), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((40, 40, 1360, 1760), outline="#d7d3ca", width=4)
    draw.rectangle((60, 60, 1340, 260), fill="#f0eadf")
    draw.text((80, 86), brand["business_name"], fill="black")
    draw.text((80, 132), brand["owner"], fill="black")
    draw.text((80, 164), f"{brand['phone']} | {brand['email']}", fill="black")
    draw.text((80, 196), brand["address"], fill="black")
    draw.text((980, 92), f"Quote {order['quote_number']}", fill="black")
    draw.text((980, 132), f"Status: {order['status']}", fill="black")
    draw.text((980, 172), f"Created: {order.get('created_at', '')}", fill="black")
    draw.text((80, 300), f"Customer: {order['customer_name']}", fill="black")
    draw.text((80, 334), f"Contact: {order['customer_contact'] or 'manual handoff'}", fill="black")

    frame = (220, 430, 1180, 1390)
    draw.rectangle(frame, outline="#222", width=20)
    mat = payload.get("selected", {}).get("mat_border_in", 2.0)
    inset = int(max(20, min(180, mat * 20)))
    draw.rectangle((frame[0] + inset, frame[1] + inset, frame[2] - inset, frame[3] - inset), outline="#9f9f9f", width=8)
    inner = (frame[0] + inset + 30, frame[1] + inset + 30, frame[2] - inset - 30, frame[3] - inset - 30)
    image_id = payload.get("selected", {}).get("image_id")
    if image_id:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT filename FROM images WHERE id = ?", (image_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            art = Image.open(UPLOAD_DIR / row["filename"]).convert("RGB")
            art = ImageOps.fit(art, (inner[2] - inner[0], inner[3] - inner[1]))
            img.paste(art, (inner[0], inner[1]))

    selected = payload.get("selected", {})
    line_items = payload.get("line_items", {})
    addons = selected.get("addons", {})
    draw.rectangle((80, 1440, 1320, 1705), outline="#d7d3ca", width=2)
    draw.text((100, 1465), "Selected Components", fill="black")
    design_state = payload.get("design_state", {})
    layout_label = "2 openings" if design_state.get("opening_layout") == "diptych" else "single opening"
    draw.text((100, 1504), f"Layout: {layout_label}", fill="black")
    draw.text((100, 1538), f"Opening Pos X: {float(design_state.get('opening_offset_x', 0)):.2f} in", fill="black")
    draw.text((100, 1572), f"Opening Pos Y: {float(design_state.get('opening_offset_y', 0)):.2f} in", fill="black")
    draw.text((100, 1606), f"Balance: {float(design_state.get('opening_balance', 50)):.0f}%", fill="black")
    draw.text((100, 1640), f"Moulding: {material_label(selected.get('moulding'))}", fill="black")
    draw.text((100, 1674), f"Mats: {_format_mat_layers(selected)}", fill="black")
    draw.text((100, 1708), f"Glazing: {material_label(selected.get('glazing'))}", fill="black")
    draw.text((100, 1742), f"Mat Border: {selected.get('mat_border_in', 2.0)} in", fill="black")
    addon_labels = []
    for key in SERVICE_KEYS:
        service = (addons.get(key) or {}).get("service")
        if service:
            addon_labels.append(f"{service.get('label', key.replace('_', ' ').title())}: ${float(service.get('price', 0)):.2f}")
    for entry in addons.get("custom", []):
        addon_labels.append(f"Other: {entry.get('label', 'Custom')} (${float(entry.get('amount', 0)):.2f})")
    if addon_labels:
        draw.text((560, 1504), addon_labels[0][:48], fill="black")
        if len(addon_labels) > 1:
            draw.text((560, 1538), addon_labels[1][:48], fill="black")

    tax_rate = float(payload.get("pricing_rules", {}).get("tax_rate", DEFAULT_SETTINGS["tax_rate"]))
    tax_label = f"Tax ({tax_rate * 100:.2f}%)"
    draw.rectangle((860, 1440, 1320, 1705), fill="#f7f3eb", outline="#d7d3ca", width=2)
    draw.text((890, 1465), "Pricing", fill="black")
    y = 1504
    for label, value in line_items.items():
        draw.text((890, y), f"{label.replace('_', ' ').title()}: ${float(value):.2f}", fill="black")
        y += 34
        if y > 1662:
            break
    y += 10
    draw.text((890, y), f"Subtotal: ${order['subtotal']:.2f}", fill="black")
    draw.text((890, y + 34), f"{tax_label}: ${order['tax']:.2f}", fill="black")
    draw.text((890, y + 68), f"Total: ${order['total']:.2f}", fill="black")
    img.save(target, quality=95)


def _status_document_label(order: dict[str, Any], document: str | None = None) -> tuple[str, str, bool]:
    status = document or order.get("status", "quote")
    quote_number = _display_form_number(order["quote_number"])
    if status == "invoice":
        return f"Invoice - Order #{quote_number}", "Invoice", True
    if status == "work_order":
        return f"Work Order - Order #{quote_number}", "Work-Order", False
    return f"Quote #{quote_number}", "Quote", True


def _form_filename(order: dict[str, Any], suffix: str, extension: str) -> str:
    return f"{suffix}-{order['quote_number']}.{extension}"


def _display_form_number(quote_number: str) -> str:
    value = str(quote_number or "").strip()
    if len(value) > 1 and value[0].upper() == "Q" and value[1:].isdigit():
        return value[1:].lstrip("0") or "0"
    return value


def _form_date(value: Any) -> str:
    text = str(value or "").strip()
    for parser in (
        lambda raw: datetime.fromisoformat(raw.replace("Z", "+00:00")),
        lambda raw: datetime.strptime(raw, "%Y-%m-%d %H:%M:%S"),
    ):
        try:
            parsed = parser(text)
            return f"{parsed.month}/{parsed.day}/{parsed.year} {parsed:%H:%M:%S}"
        except (TypeError, ValueError):
            continue
    return text


def _draw_wrapped(c: canvas.Canvas, text: str, x: float, y: float, max_width: float, leading: float = 13, max_lines: int = 12) -> float:
    words = str(text or "").split()
    if not words:
        return y
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if c.stringWidth(candidate, "Helvetica", 10) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)

    for line in lines[:max_lines]:
        c.drawString(x, y, line)
        y -= leading
    return y


def _draw_studio_logo(c: canvas.Canvas) -> None:
    profile = _get_studio_profile()
    candidates = []
    if profile["logo_filename"]:
        candidates.append(UPLOAD_DIR / profile["logo_filename"])
    candidates.extend((UPLOAD_DIR / "logo.png", ROOT / "static" / "logo.png"))
    for logo_path in candidates:
        if not logo_path.exists():
            continue
        try:
            c.drawImage(ImageReader(str(logo_path)), 452, 701, width=112, height=62, preserveAspectRatio=True, mask="auto")
            return
        except Exception:
            continue


def _brand_phone_for_forms() -> str:
    phone = _get_studio_profile()["phone"]
    if phone.startswith("1."):
        phone = phone[2:]
    return phone.replace(".", "-")


def _contact_lines(contact: str) -> list[str]:
    lines = [line.strip() for line in str(contact or "").replace("|", "\n").splitlines()]
    return [line for line in lines if line and line.lower() != "manual"][:8]


def _item_label(item: dict[str, Any] | None) -> str:
    if not item:
        return "None"
    sku = str(item.get("sku") or "").strip()
    name = str(item.get("name") or "").strip()
    if sku and name:
        return f"{sku} - {name}"
    return sku or name or "None"


def _size_pair(width: Any, height: Any) -> str:
    try:
        w = format(float(width), ".2f").rstrip("0").rstrip(".")
        h = format(float(height), ".2f").rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return ""
    return f"{w} x {h}"


def _form_sizes(selected: dict[str, Any]) -> dict[str, float | None]:
    def as_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    subject_w = as_float(selected.get("subject_width_in"))
    subject_h = as_float(selected.get("subject_height_in"))
    mat_border = as_float(selected.get("mat_border_in")) or 0.0
    moulding = selected.get("moulding") or {}
    moulding_face = as_float(moulding.get("width_in")) or 0.0
    opening_w = max(subject_w - 0.25, 0) if subject_w is not None else None
    opening_h = max(subject_h - 0.25, 0) if subject_h is not None else None
    board_w = as_float(selected.get("outside_width_in"))
    board_h = as_float(selected.get("outside_height_in"))
    if opening_w is not None:
        board_w = opening_w + (2 * mat_border)
    if opening_h is not None:
        board_h = opening_h + (2 * mat_border)
    total_w = board_w + moulding_face if board_w is not None else None
    total_h = board_h + moulding_face if board_h is not None else None
    return {
        "subject_w": subject_w,
        "subject_h": subject_h,
        "opening_w": opening_w,
        "opening_h": opening_h,
        "board_w": board_w,
        "board_h": board_h,
        "total_w": total_w,
        "total_h": total_h,
        "mat_border": mat_border,
    }


def _order_form_lines(payload: dict[str, Any], include_production: bool) -> list[str]:
    selected = payload.get("selected", {})
    design_state = payload.get("design_state", {})
    item_name = str(design_state.get("item_name") or "Custom Framing").strip()
    sizes = _form_sizes(selected)
    mat_border = float(sizes["mat_border"] or 0)

    lines = [item_name]
    subject_size = _size_pair(sizes["subject_w"], sizes["subject_h"])
    if subject_size:
        lines.append(f"Subject - {subject_size} in.")
    if subject_size:
        if design_state.get("opening_layout") == "diptych":
            spacing = float(design_state.get("opening_spacing") or 0)
            lines.append(f"Opening: 2 openings, {spacing:.2f} in. spacing")
        else:
            border = format(mat_border, ".2f").rstrip("0").rstrip(".")
            lines.append(f"Opening: {_size_pair(sizes['opening_w'], sizes['opening_h'])} in. ({border} - {border} - {border} - {border})")
    board_size = _size_pair(sizes["board_w"], sizes["board_h"])
    total_size = _size_pair(sizes["total_w"], sizes["total_h"]) or board_size
    if total_size:
        lines.append(f"Total Size: {total_size} in.")

    moulding = selected.get("moulding")
    if moulding:
        lines.append(f"Moulding: {_item_label(moulding)}")

    for layer in selected.get("mats") or []:
        item = layer.get("item") or {}
        slot = str(layer.get("slot") or "").title()
        if slot == "Top":
            size_text = f" ({board_size})" if board_size else ""
            lines.append(f"Top Mat: {item.get('sku', '')}{size_text} - {item.get('name', '')}".strip())
        else:
            reveal = float(layer.get("reveal_in") or 0)
            lines.append(f"{slot} Mat: {item.get('sku', '')} ({reveal:.2f}) - {item.get('name', '')}".strip())

    if include_production:
        glazing = selected.get("glazing")
        if glazing:
            size_text = f" ({board_size})" if board_size else ""
            lines.append(f"{glazing.get('name') or glazing.get('sku')}{size_text}")
        addons = selected.get("addons") or {}
        for key in SERVICE_KEYS:
            service = (addons.get(key) or {}).get("service")
            if service:
                lines.append(str(service.get("label") or key.replace("_", " ").title()))
        for entry in addons.get("custom", []):
            label = entry.get("label")
            if label:
                lines.append(str(label))
    return [line for line in lines if line.strip()]


def _mockup_image_reader(payload: dict[str, Any]) -> ImageReader | None:
    data_url = str(payload.get("design_state", {}).get("mockup_image_data_url") or "")
    marker = "base64,"
    if marker not in data_url:
        return None
    try:
        raw = base64.b64decode(data_url.split(marker, 1)[1], validate=True)
        return ImageReader(io.BytesIO(raw))
    except Exception:
        return None


def _draw_form_thumbnail(c: canvas.Canvas, x: float, y: float, width: float, height: float, payload: dict[str, Any]) -> None:
    mockup = _mockup_image_reader(payload)
    if mockup:
        c.drawImage(mockup, x, y, width=width, height=height, preserveAspectRatio=True, anchor="c", mask="auto")
        return

    c.setFillColor(colors.HexColor("#111111"))
    c.rect(x, y, width, height, fill=1, stroke=0)
    lip = 18
    c.setFillColor(colors.HexColor("#050505"))
    c.rect(x + lip, y + lip, width - (2 * lip), height - (2 * lip), fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#2d2d2d"))
    c.setLineWidth(1)
    c.rect(x + lip + 2, y + lip + 2, width - (2 * (lip + 2)), height - (2 * (lip + 2)), fill=0, stroke=1)
    c.setFillColor(colors.white)
    c.rect(x + 30, y + 24, width - 60, height - 48, fill=1, stroke=0)


def _export_order_form_pdf(order: dict[str, Any], payload: dict[str, Any], target: Path, document: str | None = None) -> None:
    brand = _get_studio_profile()
    doc_title, _, show_totals = _status_document_label(order, document)
    c = canvas.Canvas(str(target), pagesize=LETTER)
    page_w, page_h = LETTER
    margin = 28
    table_x = margin
    table_w = page_w - (2 * margin)
    created_at = _form_date(order.get("created_at"))
    tax_rate = float(payload.get("pricing_rules", {}).get("tax_rate", DEFAULT_SETTINGS["tax_rate"]))

    c.setFont("Helvetica", 12)
    c.drawString(margin, 748, brand["business_name"])
    c.drawString(margin, 734, brand["address"])
    c.drawString(margin, 720, _brand_phone_for_forms())
    _draw_studio_logo(c)

    c.setFont("Helvetica", 11)
    c.drawString(margin, 672, "Customer")
    c.line(margin, 670, margin + 36, 670)
    c.setFont("Helvetica", 9)
    y = 652
    c.drawString(margin, y, order["customer_name"])
    y -= 13
    for line in _contact_lines(order.get("customer_contact", "")):
        c.drawString(margin, y, line)
        if "@" in line:
            c.line(margin, y - 1, margin + c.stringWidth(line, "Helvetica", 9), y - 1)
        y -= 13

    c.setFont("Helvetica", 11)
    c.drawRightString(page_w - margin, 672, doc_title)
    c.line(page_w - margin - c.stringWidth(doc_title, "Helvetica", 11), 670, page_w - margin, 670)
    c.setFont("Helvetica", 9)
    c.drawRightString(page_w - margin, 652, f"Date {created_at}")
    c.drawRightString(page_w - margin, 639, f"Created by: {brand['owner']}")

    table_top = 572
    header_h = 22
    row_h = 112 if show_totals else 130
    c.setStrokeColor(colors.HexColor("#d6d6d6"))
    c.setLineWidth(0.5)
    c.roundRect(table_x, table_top - header_h - row_h, table_w, header_h + row_h, 4, stroke=1, fill=0)
    c.setFillColor(colors.HexColor("#f3f3f3"))
    c.rect(table_x + 0.5, table_top - header_h, table_w - 1, header_h - 0.5, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.line(table_x, table_top - header_h, table_x + table_w, table_top - header_h)
    c.setFont("Helvetica", 9)
    c.drawString(table_x + 6, table_top - 15, "Item #1")

    if show_totals:
        product_x = table_x + 174
        qty_x = table_x + table_w - 6
        c.drawString(product_x, table_top - 15, "Product")
        c.drawRightString(qty_x, table_top - 15, "Quantity")
    else:
        product_x = table_x + 210
        qty_x = table_x + table_w - 6
        c.drawString(product_x, table_top - 15, "Product")
        c.drawRightString(qty_x, table_top - 15, "Quantity")

    thumb_y = table_top - header_h - 108
    _draw_form_thumbnail(c, table_x + 6, thumb_y, 120, 104, payload)
    c.setFillColor(colors.black)

    c.setFont("Helvetica", 9)
    lines = _order_form_lines(payload, include_production=not show_totals)
    text_y = table_top - header_h - 14
    for line in lines[:10]:
        text_y = _draw_wrapped(c, line, product_x, text_y, 390 if show_totals else 316, leading=12, max_lines=2)

    c.setFont("Helvetica", 9)
    c.drawRightString(qty_x, table_top - header_h - 14, "1")

    if show_totals:
        c.setFont("Helvetica", 9)
        totals_x = page_w - margin
        totals_y = table_top - header_h - row_h - 22
        c.drawRightString(totals_x - 44, totals_y, "Subtotal")
        c.drawRightString(totals_x, totals_y, f"${order['subtotal']:.2f}")
        c.drawRightString(totals_x - 44, totals_y - 14, f"Sales Tax ({tax_rate * 100:.3f}%)")
        c.drawRightString(totals_x, totals_y - 14, f"${order['tax']:.2f}")
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(totals_x - 44, totals_y - 28, "Total")
        c.drawRightString(totals_x, totals_y - 28, f"${order['total']:.2f}")

    # Draw terms / disclaimer box at the bottom
    doc_type = document or order.get("status", "quote")
    box_y = 45
    box_h = 75
    c.setStrokeColor(colors.HexColor("#d6d6d6"))
    c.setLineWidth(0.5)
    c.roundRect(margin, box_y, table_w, box_h, 4, stroke=1, fill=0)
    
    # Fill header of the box
    c.setFillColor(colors.HexColor("#f8f8f8"))
    c.rect(margin + 0.5, box_y + box_h - 20, table_w - 1, 19.5, fill=1, stroke=0)
    
    # Header label based on document type
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    if doc_type == "quote":
        c.drawString(margin + 10, box_y + box_h - 14, "Terms & Conditions")
        disclaimer_text = "Quotes are valid for 30 days. Material availability is subject to change. A 50% deposit is required to begin custom framing production."
    elif doc_type == "work_order":
        c.drawString(margin + 10, box_y + box_h - 14, "Production Verification Notes")
        disclaimer_text = "Operators: Inspect all joints, miters, and materials before cutting and assembling. Verify glazing is free of dust or smudges. Confirm secure hanging hardware is attached."
    else:  # invoice
        c.drawString(margin + 10, box_y + box_h - 14, "Customer Pickup & Terms")
        disclaimer_text = "Thank you for your business! Please pick up your finished framing work during normal business hours. Orders left over 90 days are subject to storage fees or disposal."
        
    c.setFont("Helvetica", 9)
    _draw_wrapped(c, disclaimer_text, margin + 10, box_y + box_h - 32, table_w - 20, leading=12, max_lines=3)

    c.showPage()
    c.save()


@app.get("/api/orders/{order_id}/export")
def export_order(
    order_id: int,
    format: str = Query("pdf"),
    document: str = Query(""),
    disposition: str = Query("attachment"),
) -> FileResponse:
    if format not in {"pdf", "jpg"}:
        raise HTTPException(status_code=400, detail="format must be pdf or jpg")
    if document and document not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="document must be quote, work_order, or invoice")
    if disposition not in {"inline", "attachment"}:
        raise HTTPException(status_code=400, detail="disposition must be inline or attachment")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, customer_name, customer_contact, status, approved_at, completed_at, invoiced_at,
               payload_json, subtotal, tax, total, created_at
        FROM orders
        WHERE id = ?
        """,
        (order_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")

    order = dict(row)
    order["quote_number"] = f"Q{order_id:05d}"
    payload = _parse_order_payload_for_export(order["payload_json"])

    if format == "jpg":
        target = EXPORT_DIR / f"{order['quote_number']}.jpg"
        _export_quote_image(order, payload, target)
        return FileResponse(
            target,
            filename=target.name,
            media_type="image/jpeg",
            content_disposition_type=disposition,
        )

    document_key = document or order["status"]
    _, suffix, _ = _status_document_label(order, document_key)
    target = EXPORT_DIR / _form_filename(order, suffix, "pdf")
    _export_order_form_pdf(order, payload, target, document_key)
    return FileResponse(
        target,
        filename=target.name,
        media_type="application/pdf",
        content_disposition_type=disposition,
    )
