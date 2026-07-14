from fastapi import APIRouter, Request, Depends, Form, HTTPException, Response
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse, StreamingResponse
from app.auth import find_user_by_login, get_current_user, login_user, logout_user, verify_password, AdminAuthMiddleware
from app.template_compat import Jinja2Templates
import sqlite3
import json
import re
from pathlib import Path
from app.db import get_connection
from app.pricing import (
    calculate_quote, get_price_table, update_price_table, 
    get_price_rules, update_price_rule
)

ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))

admin_router = APIRouter(prefix="/admin", tags=["admin"])


def _form_truthy(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "on", "approved", "done"}


def _has_customer_phone(raw: str | None) -> bool:
    return len(re.sub(r"\D", "", raw or "")) >= 7

# --- Auth Routes ---
@admin_router.post("/login")
async def admin_login(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/", alias="next"),
):
    user = find_user_by_login(email)
    if user and verify_password(password, user['password_hash']):
        login_user(request, user)
        safe_next = next if next.startswith("/") and not next.startswith("//") else "/"
        return RedirectResponse(url=safe_next, status_code=303)
    
    return RedirectResponse(url=f"/admin/login?error=Invalid credentials&next={next}", status_code=303)

@admin_router.get("/logout")
async def admin_logout(request: Request):
    logout_user(request)
    return RedirectResponse(url="/", status_code=303)

@admin_router.get("/me")
async def admin_me(current_user: dict = Depends(get_current_user)):
    return current_user

# --- User/Business Routes ---
@admin_router.get("/account_edit", response_class=HTMLResponse)
async def account_edit_view(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/admin/login")
    return templates.TemplateResponse("admin/account_edit.html", {
        "request": request, "current_user": current_user, "success": request.query_params.get("success")
    })

@admin_router.post("/account_edit")
async def account_edit_save(
    first_name: str = Form(...), 
    last_name: str = Form(...),
    email: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET first_name = ?, last_name = ?, email = ? WHERE id = ?",
        (first_name, last_name, email, current_user['id'])
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin/account_edit?success=1", status_code=303)

@admin_router.get("/account_password", response_class=HTMLResponse)
async def account_password_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/admin/login")
    return templates.TemplateResponse("admin/account_password.html", {
        "request": request, "current_user": current_user, "success": request.query_params.get("success"), "error": request.query_params.get("error")
    })

@admin_router.post("/account_password")
async def account_password_save(
    old_password: str = Form(...),
    new_password: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    from app.auth import hash_password
    if not verify_password(old_password, current_user['password_hash']):
        return RedirectResponse(url="/admin/account_password?error=Invalid old password", status_code=303)
    
    pwd_hash = hash_password(new_password)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (pwd_hash, current_user['id']))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin/account_password?success=1", status_code=303)

@admin_router.get("/address_book", response_class=HTMLResponse)
async def address_book(request: Request, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM business_info WHERE id = 1")
    info = cur.fetchone()
    conn.close()
    return templates.TemplateResponse("admin/address_book.html", {
        "request": request, "info": dict(info) if info else {}, 
        "current_user": current_user, "success": request.query_params.get("success")
    })

@admin_router.post("/address_book")
async def address_book_save(
    company: str = Form(...), address: str = Form(...), city: str = Form(...),
    state: str = Form(...), zip: str = Form(...), phone: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE business_info SET company=?, address=?, city=?, state=?, zip=?, phone=?
        WHERE id = 1
    """, (company, address, city, state, zip, phone))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin/address_book?success=1", status_code=303)

# --- Settings Routes ---
@admin_router.get("/localization", response_class=HTMLResponse)
async def localization_get(request: Request, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM app_settings")
    settings = {row['key']: row['value'] for row in cur.fetchall()}
    cur.execute("SELECT * FROM order_statuses ORDER BY sort_order")
    statuses = [dict(row) for row in cur.fetchall()]
    conn.close()
    return templates.TemplateResponse("admin/localization.html", {"request": request, "settings": settings, "statuses": statuses, "success": request.query_params.get("success")})

@admin_router.post("/localization")
async def localization_post(
    tax_rate: str = Form(...), currency: str = Form(...), units: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('tax_rate', ?)", (tax_rate,))
    cur.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('currency', ?)", (currency,))
    cur.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('units', ?)", (units,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin/localization?success=1", status_code=303)

@admin_router.get("/settings", response_class=HTMLResponse)
async def settings_get(request: Request, current_user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("admin/settings.html", {"request": request, "current_user": current_user, "success": request.query_params.get("success")})

# --- Pricing Routes ---
@admin_router.get("/prices", response_class=HTMLResponse)
async def prices_get(request: Request, current_user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("admin/prices.html", {"request": request, "rules": get_price_rules(), "success": request.query_params.get("success")})

@admin_router.post("/prices")
async def prices_post(
    component_type: str = Form(...), method: str = Form(...), 
    markup: float = Form(...), factor: float = Form(0),
    costing_method: str = Form('square_area'), min_price: float = Form(0),
    current_user: dict = Depends(get_current_user)
):
    update_price_rule(component_type, method, markup, factor, costing_method, min_price)
    return RedirectResponse(url="/admin/prices?success=1", status_code=303)

@admin_router.get("/prices/table", response_class=HTMLResponse)
async def prices_table_get(request: Request, current_user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("admin/prices.html", {"request": request, "rules": get_price_rules(), "price_table": get_price_table(), "success": request.query_params.get("success")})

@admin_router.post("/prices/table")
async def prices_table_post(
    code: str = Form(...), half_perimeter: float = Form(...), price: float = Form(...),
    current_user: dict = Depends(get_current_user)
):
    update_price_table(code, half_perimeter, price)
    return RedirectResponse(url="/admin/prices/table?success=1", status_code=303)

# --- Catalog Management Routes ---
@admin_router.get("/import_export", response_class=HTMLResponse)
async def import_export_list(request: Request, search: str = "", current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM catalog_items"
    params = []
    if search:
        query += " WHERE sku LIKE ? OR name LIKE ?"
        params = [f"%{search}%", f"%{search}%"]
    cur.execute(query, params)
    items = [dict(row) for row in cur.fetchall()]
    conn.close()
    return templates.TemplateResponse("admin/import_export.html", {"request": request, "items": items, "search": search, "success": request.query_params.get("success")})

# --- Order Routes ---
@admin_router.get("/orders", response_class=HTMLResponse)
async def orders_list(request: Request, status: str = "", current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    params = []
    query = "SELECT * FROM orders"
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    orders = [dict(row) for row in cur.fetchall()]
    cur.execute("SELECT * FROM order_statuses ORDER BY sort_order")
    statuses = [dict(row) for row in cur.fetchall()]
    conn.close()
    return templates.TemplateResponse("admin/orders.html", {"request": request, "orders": orders, "statuses": statuses, "filter_status": status, "success": request.query_params.get("success")})

@admin_router.get("/orders/export")
async def orders_export(current_user: dict = Depends(get_current_user)):
    import csv, io
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, customer_name, customer_contact, total, status, approved_at, completed_at, invoiced_at, created_at, updated_at
        FROM orders
        ORDER BY id DESC
        """
    )
    orders = [dict(row) for row in cur.fetchall()]
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "quote_number", "id", "customer_name", "customer_contact", "total", "status",
        "approved_at", "completed_at", "invoiced_at", "created_at", "updated_at",
    ])
    for order in orders:
        writer.writerow([
            f"Q{order['id']:05d}",
            order["id"],
            order.get("customer_name", ""),
            order.get("customer_contact", ""),
            order.get("total", 0),
            order.get("status", ""),
            order.get("approved_at", ""),
            order.get("completed_at", ""),
            order.get("invoiced_at", ""),
            order.get("created_at", ""),
            order.get("updated_at", ""),
        ])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=orders.csv"})

@admin_router.get("/orders/{id}", response_class=HTMLResponse)
async def order_detail(request: Request, id: int, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE id = ?", (id,))
    order = cur.fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    cur.execute("SELECT * FROM order_items WHERE order_id = ?", (id,))
    items = [dict(row) for row in cur.fetchall()]
    cur.execute("SELECT * FROM order_statuses ORDER BY sort_order")
    statuses = [dict(row) for row in cur.fetchall()]
    conn.close()
    return templates.TemplateResponse("admin/order_detail.html", {"request": request, "order": dict(order), "items": items, "statuses": statuses, "success": request.query_params.get("success")})

@admin_router.post("/orders/{id}/status")
async def order_status_update(
    id: int,
    status: str = Form(...),
    customer_approved: str = Form(""),
    work_completed: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    if status not in {"quote", "work_order", "invoice"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, customer_name, customer_contact, approved_at, completed_at FROM orders WHERE id = ?", (id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    current = row["status"]
    allowed = {current}
    if current == "quote":
        allowed.add("work_order")
    elif current == "work_order":
        allowed.add("invoice")
    elif current == "invoice":
        allowed.add("work_order")
    if status not in allowed:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Transition from {current} cannot go to {status}")
    if status in {"work_order", "invoice"}:
        if not (row["customer_name"] or "").strip():
            conn.close()
            raise HTTPException(status_code=400, detail="Customer name is required")
        if not _has_customer_phone(row["customer_contact"]):
            conn.close()
            raise HTTPException(status_code=400, detail="Customer phone number is required")
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
        (status, id),
    )
    cur.execute("INSERT INTO order_status_history (order_id, status) VALUES (?, ?)", (id, status))
    conn.commit()
    conn.close()
    return {"success": True}

# --- Customer Routes ---
@admin_router.get("/customers", response_class=HTMLResponse)
async def customers_list(request: Request, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY name")
    customers = [dict(row) for row in cur.fetchall()]
    conn.close()
    return templates.TemplateResponse("admin/customers.html", {"request": request, "customers": customers, "success": request.query_params.get("success")})

@admin_router.post("/customers/add")
async def customer_add(name: str = Form(...), email: str = Form(""), phone: str = Form(""), current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO customers (name, email, phone) VALUES (?, ?, ?)", (name, email, phone))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin/customers", status_code=303)

# --- Template Rendering Routes ---

@admin_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return RedirectResponse(url="/", status_code=303)

@admin_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})

@admin_router.get("/store_logo", response_class=HTMLResponse)
async def store_logo_page(request: Request):
    return templates.TemplateResponse("admin/store_logo.html", {"request": request})

@admin_router.get("/system_updates", response_class=HTMLResponse)
async def system_updates_page(request: Request):
    return templates.TemplateResponse("admin/system_updates.html", {"request": request})

@admin_router.get("/customers/{id}", response_class=HTMLResponse)
async def customer_edit_page(request: Request, id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id = ?", (id,))
    customer = cur.fetchone()
    conn.close()
    return templates.TemplateResponse("admin/customer_edit.html", {"request": request, "customer": dict(customer) if customer else None})

@admin_router.get("/customers/import", response_class=HTMLResponse)
async def customers_import_page(request: Request):
    return templates.TemplateResponse("admin/customers.html", {"request": request})
