from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from .db import get_connection

SESSION_COOKIE = "framershaven_session"
SESSION_DAYS = 14
PBKDF2_ROUNDS = 180_000
ROLES = {"admin", "operator"}

router = APIRouter()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime | None = None) -> str:
    return (value or _utc_now()).isoformat().replace("+00:00", "Z")


def _hash_password(password: str, salt: bytes | None = None) -> str:
    clean = password.encode("utf-8")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", clean, salt, PBKDF2_ROUNDS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ROUNDS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, rounds, salt, digest = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.b64decode(salt.encode("ascii")),
            int(rounds),
        )
        return hmac.compare_digest(expected, base64.b64decode(digest.encode("ascii")))
    except (ValueError, TypeError, OSError):
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def init_auth_tables() -> None:
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'operator')),
                password_hash TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS auth_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_auth_sessions_token_hash
            ON auth_sessions(token_hash);
            """
        )
        conn.commit()
    finally:
        conn.close()


def ensure_default_users() -> None:
    init_auth_tables()
    admin_password = os.environ.get("FRAMERSHAVEN_ADMIN_PASSWORD", "admin")
    operator_password = os.environ.get("FRAMERSHAVEN_OPERATOR_PASSWORD", "operator")
    defaults = [
        ("admin", "Administrator", "admin", admin_password),
        ("operator", "Operator", "operator", operator_password),
    ]
    conn = get_connection()
    try:
        cur = conn.cursor()
        for username, display_name, role, password in defaults:
            cur.execute(
                """
                INSERT OR IGNORE INTO users (username, display_name, role, password_hash, active, updated_at)
                VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                """,
                (username, display_name, role, _hash_password(password)),
            )
        conn.commit()
    finally:
        conn.close()


def auth_required_for_request(request: Request) -> bool:
    if os.environ.get("FRAMERSHAVEN_AUTH_REQUIRED", "1").lower() in {"0", "false", "no", "off"}:
        return False
    if request.client and request.client.host == "testclient":
        return False
    return True


def _public_user(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
    }


def get_current_user(request: Request) -> dict[str, Any] | None:
    if not auth_required_for_request(request):
        return {"id": 0, "username": "test-admin", "display_name": "Test Admin", "role": "admin"}
    existing = getattr(request.state, "current_user", None)
    if existing:
        return existing
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT users.id, users.username, users.display_name, users.role, sessions.expires_at
            FROM auth_sessions AS sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND users.active = 1
            """,
            (_hash_token(token),),
        )
        row = cur.fetchone()
        if not row:
            return None
        if str(row["expires_at"]) < _timestamp():
            cur.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (_hash_token(token),))
            conn.commit()
            return None
        user = _public_user(row)
        request.state.current_user = user
        return user
    finally:
        conn.close()


def require_user(request: Request) -> dict[str, Any]:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user


def require_admin(request: Request) -> dict[str, Any]:
    user = require_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def create_session(response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    expires = _utc_now() + timedelta(days=SESSION_DAYS)
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO auth_sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, _hash_token(token), _timestamp(expires)),
        )
        conn.commit()
    finally:
        conn.close()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=False,
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>FramersHaven Login</title>
            <style>
              body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #f3f5f7; color: #1b2430; font-family: Arial, sans-serif; }
              form { width: min(360px, calc(100vw - 32px)); display: grid; gap: 12px; padding: 24px; background: white; border: 1px solid #d9e0e7; border-radius: 8px; box-shadow: 0 16px 40px rgba(27, 36, 48, .08); }
              h1 { margin: 0; font-size: 22px; }
              p { margin: 0 0 4px; color: #627084; font-size: 13px; line-height: 1.4; }
              label { display: grid; gap: 5px; font-size: 12px; font-weight: 700; text-transform: uppercase; color: #526176; }
              input { min-height: 38px; border: 1px solid #c9d3df; border-radius: 6px; padding: 0 10px; font: inherit; }
              button { min-height: 40px; border: 1px solid #2f64ff; border-radius: 6px; background: #2f64ff; color: white; font-weight: 700; cursor: pointer; }
              small { color: #6c788a; line-height: 1.4; }
            </style>
          </head>
          <body>
            <form method="post" action="/api/auth/login">
              <h1>FramersHaven</h1>
              <p>Sign in to use this workstation.</p>
              <label>Username <input name="username" autocomplete="username" required autofocus /></label>
              <label>Password <input name="password" type="password" autocomplete="current-password" required /></label>
              <button type="submit">Sign In</button>
              <small>First-run demo accounts: admin/admin and operator/operator. Change them before using this outside a trusted workstation.</small>
            </form>
          </body>
        </html>
        """
    )


@router.post("/api/auth/login")
def login(username: str = Form(...), password: str = Form(...)) -> RedirectResponse:
    ensure_default_users()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, password_hash, active FROM users WHERE username = ?",
            (username.strip(),),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if not row or not row["active"] or not _verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    response = RedirectResponse("/", status_code=303)
    create_session(response, int(row["id"]))
    return response


@router.post("/api/auth/logout")
def logout(request: Request) -> RedirectResponse:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (_hash_token(token),))
            conn.commit()
        finally:
            conn.close()
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/api/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return {"user": user}
