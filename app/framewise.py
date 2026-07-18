from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .db import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/framewise", tags=["framewise"])

FRAMEWISE_DEFAULTS: dict[str, str] = {
    "enabled": "0",
    "assistant_name": "Framewise",
    "provider_type": "ollama",
    "base_url": "http://127.0.0.1:11434/v1",
    "model": "llama3.2:3b",
    "api_key": "",
    "context_tokens": "4096",
    "temperature": "0.35",
}

FRAMEWISE_SETTING_KEYS = {f"framewise_{key}": key for key in FRAMEWISE_DEFAULTS}
ALLOWED_PROVIDER_TYPES = {"ollama", "llama.cpp", "lm-studio", "openai-compatible"}

SYSTEM_PROMPT = """\
You are Framewise, a concise framing-studio assistant built into FramersHaven.
Help shop staff choose framing directions, explain quote details, and work with
the local catalog data they provide. Do not invent item numbers, prices,
vendor availability, customer data, or completed actions. If exact catalog
data is missing, say what to search for or verify next.
"""


class FramewiseChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None
    workspace: str = "design"
    quote_context: dict[str, Any] = Field(default_factory=dict)


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _setting_rows() -> dict[str, str]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        keys = tuple(FRAMEWISE_SETTING_KEYS)
        placeholders = ",".join("?" for _ in keys)
        cur.execute(f"SELECT key, value FROM settings WHERE key IN ({placeholders})", keys)
        return {row["key"]: row["value"] for row in cur.fetchall()}
    finally:
        conn.close()


def _stored_config(include_secret: bool = False) -> dict[str, Any]:
    stored = _setting_rows()
    config = {
        key: stored.get(f"framewise_{key}", default)
        for key, default in FRAMEWISE_DEFAULTS.items()
    }
    provider_type = str(config["provider_type"]).strip().lower()
    if provider_type not in ALLOWED_PROVIDER_TYPES:
        provider_type = FRAMEWISE_DEFAULTS["provider_type"]
    api_key = str(config.get("api_key") or "")
    public_config: dict[str, Any] = {
        "enabled": _truthy(config["enabled"]),
        "assistant_name": str(config["assistant_name"] or "Framewise").strip()[:40] or "Framewise",
        "provider_type": provider_type,
        "base_url": str(config["base_url"] or FRAMEWISE_DEFAULTS["base_url"]).strip().rstrip("/"),
        "model": str(config["model"] or FRAMEWISE_DEFAULTS["model"]).strip(),
        "api_key_present": bool(api_key),
        "context_tokens": max(1024, min(65536, int(float(config["context_tokens"] or 4096)))),
        "temperature": max(0.0, min(2.0, float(config["temperature"] or 0.35))),
    }
    if include_secret:
        public_config["api_key"] = api_key
    return public_config


def _save_config(values: dict[str, Any]) -> dict[str, Any]:
    current = _stored_config(include_secret=True)
    cleaned = {
        "enabled": "1" if _truthy(values.get("enabled")) else "0",
        "assistant_name": str(values.get("assistant_name") or current["assistant_name"] or "Framewise").strip()[:40],
        "provider_type": str(values.get("provider_type") or current["provider_type"]).strip().lower(),
        "base_url": str(values.get("base_url") or current["base_url"]).strip().rstrip("/"),
        "model": str(values.get("model") or current["model"]).strip(),
        "api_key": str(values.get("api_key") if values.get("api_key") is not None else current.get("api_key", "")).strip(),
        "context_tokens": str(max(1024, min(65536, int(float(values.get("context_tokens") or current["context_tokens"]))))),
        "temperature": str(max(0.0, min(2.0, float(values.get("temperature") or current["temperature"])))),
    }
    if cleaned["provider_type"] not in ALLOWED_PROVIDER_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported Framewise provider type")
    if not cleaned["base_url"].startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Framewise base URL must start with http:// or https://")
    if not cleaned["model"]:
        raise HTTPException(status_code=400, detail="Framewise model is required")

    conn = get_connection()
    try:
        cur = conn.cursor()
        for key, value in cleaned.items():
            cur.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """,
                (f"framewise_{key}", value),
            )
        conn.commit()
    finally:
        conn.close()
    return _stored_config()


def _chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/chat/completions"


@router.get("/config")
def get_framewise_config() -> dict[str, Any]:
    return {"config": _stored_config()}


@router.post("/config")
async def update_framewise_config(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        values = await request.json()
    else:
        form = await request.form()
        values = dict(form)
    return {"config": _save_config(values)}


@router.get("/status")
async def framewise_status() -> dict[str, Any]:
    config = _stored_config(include_secret=True)
    if not config["enabled"]:
        return {
            "enabled": False,
            "available": False,
            "assistant_name": config["assistant_name"],
            "message": "Framewise is off. Enable a local provider in Admin when you want assistant help.",
        }
    headers = {"Authorization": f"Bearer {config['api_key']}"} if config.get("api_key") else {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{config['base_url'].rstrip('/')}/models", headers=headers)
            available = response.status_code < 500
    except Exception:
        available = False
    return {
        "enabled": True,
        "available": available,
        "assistant_name": config["assistant_name"],
        "message": "Framewise provider is reachable." if available else "Framewise provider is not reachable.",
    }


@router.post("/chat")
async def framewise_chat(req: FramewiseChatRequest) -> dict[str, Any]:
    config = _stored_config(include_secret=True)
    conversation_id = req.conversation_id or str(uuid.uuid4())
    if not config["enabled"]:
        return {
            "answer": "Framewise is off. Enable a local provider in Admin first.",
            "conversation_id": conversation_id,
            "mode": "disabled",
        }

    context = json.dumps(req.quote_context or {}, indent=2)
    user_text = f"{req.message}\n\nWorkspace: {req.workspace}\nLocal context:\n```json\n{context}\n```"
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": 512,
        "temperature": config["temperature"],
    }
    headers = {
        "Content-Type": "application/json",
        **({"Authorization": f"Bearer {config['api_key']}"} if config.get("api_key") else {}),
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(_chat_url(config["base_url"]), json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("Framewise provider error: %s", exc)
        answer = "Framewise could not reach the configured local model. The rest of FramersHaven is still working."
    return {"answer": answer, "conversation_id": conversation_id, "mode": "advisory"}
