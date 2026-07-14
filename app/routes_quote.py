from fastapi import APIRouter, Request, HTTPException, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from .template_compat import Jinja2Templates
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from .db import get_connection
from .pricing import QuoteRequest, calculate_quote

ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))

quote_router = APIRouter(prefix="/admin")

# SimulArt-style Presets config
PRESETS = [
    {"id": 1000001, "name": "Moulding & Single Mat", "openings": 1, "moulding": "I1100-50", "mat": "A109", "notes": "Basic"},
    {"id": 1000002, "name": "Moulding & Double Mat", "openings": 1, "moulding": "I1100-50", "mat": "A109+A109", "notes": "Double mat"},
    {"id": 1000003, "name": "Moulding Mat & Fillet", "openings": 1, "moulding": "I1100-50", "mat": "A109", "notes": "+ fillet I355-75", "fillet": "I355-75"},
    {"id": 1000004, "name": "Moulding & Liner", "openings": 0, "moulding": "I1100-50", "mat": None, "notes": "+ liner I300-560", "liner": "I300-560"},
    {"id": 1000005, "name": "Frame Only", "openings": 0, "moulding": "I1100-50", "mat": None, "notes": "No mat"},
    {"id": 1000006, "name": "Mat Only", "openings": 1, "moulding": None, "mat": "A109", "notes": "No moulding"},
    {"id": 1000007, "name": "Stretched Canvas - Mirror Side", "openings": 0, "moulding": None, "mat": None, "notes": "Special"},
    {"id": 1000008, "name": "Framed Mirror", "openings": 0, "moulding": "I1100-50", "mat": None, "notes": "Mirror glazing", "glazing": "MIRROR"},
    {"id": 1000009, "name": "Frame & Mat - 2 Openings", "id_simulart": 1000009, "openings": 2, "moulding": "I1100-50", "mat": "A109", "notes": "Split"},
    {"id": 1000010, "name": "Frame & Mat - 3 Openings", "openings": 3, "moulding": "I1100-50", "mat": "A109", "notes": "Triptych"},
    {"id": 1000011, "name": "Frame & Mat - 4 Openings", "openings": 4, "moulding": "I1100-50", "mat": "A109", "notes": "Quad"},
    {"id": 1000012, "name": "Frame & Mat - 12 Openings", "openings": 12, "moulding": "I1100-50", "mat": "A109", "notes": "Gallery wall"},
]

@quote_router.get("/design", response_class=HTMLResponse)
async def design_workspace(request: Request, fromPreset: Optional[int] = None):
    preset = next((p for p in PRESETS if p["id"] == fromPreset), PRESETS[0])
    return templates.TemplateResponse("admin/design.html", {
        "request": request, 
        "preset": preset,
        "presets": PRESETS
    })

@quote_router.post("/design/update")
async def design_update(request: Request):
    # This will return JSON with rendered image URL and calculated price
    # For now, it's a stub that will be filled by frontend logic calling existing /api/frame and /api/quotes/calculate
    data = await request.json()
    return JSONResponse({"status": "ok", "message": "Preview updated"})

@quote_router.post("/design/save")
async def design_save(request: Request):
    # Save design as order item (logic to be implemented with DB subagent's tables)
    data = await request.json()
    return JSONResponse({"status": "ok", "order_id": 123})

@quote_router.post("/quote/save")
async def quote_save(request: Request):
    # Convert current design to a saved quote
    # Create order record status='quote', item with design JSON, calc total
    data = await request.json()
    return JSONResponse({"status": "ok", "order_id": 456})

@quote_router.get("/order/{order_id}", response_class=HTMLResponse)
async def order_detail(request: Request, order_id: int):
    # Mock data for template development
    order = {
        "id": order_id,
        "quote_number": f"Q{order_id:05d}",
        "customer_name": "John Doe",
        "status": "quote",
        "total": 150.00,
        "created_at": "2026-03-31"
    }
    return templates.TemplateResponse("admin/order_detail.html", {"request": request, "order": order})

@quote_router.get("/order/{order_id}/print", response_class=HTMLResponse)
async def order_print(request: Request, order_id: int):
    order = {
        "id": order_id,
        "quote_number": f"Q{order_id:05d}",
        "customer_name": "John Doe",
        "total": 150.00
    }
    return templates.TemplateResponse("admin/order_print.html", {"request": request, "order": order})

@quote_router.post("/orders/{order_id}/assign-customer")
async def assign_customer(order_id: int, customer_id: int = Form(...)):
    return JSONResponse({"status": "ok", "message": f"Customer {customer_id} assigned to order {order_id}"})

@quote_router.get("/gallery", response_class=HTMLResponse)
async def gallery_browse(request: Request):
    return templates.TemplateResponse("admin/gallery.html", {"request": request})

@quote_router.get("/gallery/{image_id}/info")
async def gallery_info(image_id: int):
    return JSONResponse({"id": image_id, "name": "Mona Lisa", "dimensions": "20x30"})
