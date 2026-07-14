import bcrypt
from fastapi import Request
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


def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return _local_operator_user()
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return _local_operator_user()
    return dict(row)

def is_admin(request):
    return True

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
    async def dispatch(self, request, call_next):
        return await call_next(request)

# Backwards-compatible name for any older imports.
AdminAuthMiddleware = StudioAuthMiddleware
