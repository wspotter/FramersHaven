import os
from typing import Any
from urllib.parse import urlencode

import bcrypt
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.db import get_connection

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Session management functions
def login_user(request, user):
    request.session["user_id"] = user["id"]
    request.session["user_email"] = user["email"]
    request.session["user_role"] = user["role"]

def logout_user(request):
    request.session.clear()


def open_admin_mode_enabled() -> bool:
    return os.getenv("PRINTERY_ALLOW_OPEN_ADMIN", "").strip().lower() in {"1", "true", "yes", "on"}


def _local_operator_user() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM users
        ORDER BY
            CASE role
                WHEN 'owner' THEN 0
                WHEN 'admin' THEN 1
                ELSE 2
            END,
            id
        LIMIT 1
        """
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "id": 0,
        "email": "local@theprintery.biz",
        "first_name": "Local",
        "last_name": "Operator",
        "role": "owner",
        "password_hash": "",
    }


def get_current_user(request: Request) -> dict[str, Any] | None:
    user_id = request.session.get("user_id")
    if not user_id:
        if open_admin_mode_enabled():
            return _local_operator_user()
        return None
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        if open_admin_mode_enabled():
            return _local_operator_user()
        return None
    return dict(row)

def is_admin(request):
    user = get_current_user(request)
    return bool(user and user.get("role") in {"owner", "admin"})


def require_current_user(request: Request) -> dict[str, Any]:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Admin login required")
    return user

def normalize_login_identifier(identifier: str) -> str:
    value = (identifier or "").strip().lower()
    if "@" not in value and value:
        return f"{value}@theprintery.biz"
    return value

def find_user_by_login(identifier: str):
    login = normalize_login_identifier(identifier)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE lower(email) = ?", (login,))
    user = cur.fetchone()
    conn.close()
    return user

class StudioAuthMiddleware(BaseHTTPMiddleware):
    _PUBLIC_ADMIN_PATHS = {"/admin/login", "/admin/logout"}

    async def dispatch(self, request, call_next):
        path = request.url.path.rstrip("/") or "/"
        if path.startswith("/admin") and path not in self._PUBLIC_ADMIN_PATHS:
            if get_current_user(request) is None:
                if request.method == "GET":
                    next_path = request.url.path
                    if request.url.query:
                        next_path = f"{next_path}?{request.url.query}"
                    return RedirectResponse(url=f"/admin/login?{urlencode({'next': next_path})}", status_code=303)
                return JSONResponse({"detail": "Admin login required"}, status_code=401)
        return await call_next(request)

# Backwards-compatible name for any older imports.
AdminAuthMiddleware = StudioAuthMiddleware
