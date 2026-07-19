from __future__ import annotations

import base64
import io
import json
import logging
import uuid
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from .db import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/framewise", tags=["framewise"])

RECOMMENDED_FRAMEWISE_MODEL = "hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M"

FRAMEWISE_DEFAULTS: dict[str, str] = {
    "enabled": "0",
    "assistant_name": "Framewise",
    "provider_type": "ollama",
    "base_url": "http://127.0.0.1:11434/v1",
    "model": RECOMMENDED_FRAMEWISE_MODEL,
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


class FramewiseDesignRequest(BaseModel):
    subject: str = Field("", max_length=1200)
    goal: str = Field("", max_length=1200)
    image_id: int | None = None
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


def _catalog_rows(category_keyword: str, limit: int = 12) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, sku, name, category, cost, vendor, width_in, height_in, rabbet_in, metadata_json
            FROM catalog_items
            WHERE active = 1 AND lower(category) LIKE '%' || ? || '%'
            ORDER BY
              CASE WHEN cost > 0 THEN 0 ELSE 1 END,
              CASE WHEN vendor IS NULL OR vendor = '' THEN 1 ELSE 0 END,
              sku COLLATE NOCASE
            LIMIT ?
            """,
            (category_keyword.lower(), limit),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def _catalog_label(item: dict[str, Any] | None) -> str:
    if not item:
        return "No catalog item selected"
    vendor = f" · {item['vendor']}" if item.get("vendor") else ""
    return f"{item['sku']} · {item['name']}{vendor}"


def _compact_item(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    return {
        "id": item["id"],
        "sku": item["sku"],
        "name": item["name"],
        "category": item["category"],
        "vendor": item.get("vendor") or "",
        "width_in": item.get("width_in"),
        "height_in": item.get("height_in"),
        "rabbet_in": item.get("rabbet_in"),
        "cost": item.get("cost"),
    }


def _image_id_from_request(req: FramewiseDesignRequest) -> int | None:
    if req.image_id:
        return req.image_id
    selected = (req.quote_context or {}).get("selected_image") or {}
    try:
        return int(selected.get("id") or 0) or None
    except (TypeError, ValueError):
        return None


def _framewise_image_payload(image_id: int | None) -> dict[str, Any]:
    if not image_id:
        return {"available": False, "reason": "No gallery image is selected."}
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, filename, path, width_in, height_in, ratio_label, crop_json FROM images WHERE id = ?",
            (image_id,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return {"available": False, "reason": f"Gallery image {image_id} was not found."}

    image_path = Path(str(row["path"]))
    if not image_path.exists() or not image_path.is_file():
        return {"available": False, "reason": "The selected gallery image file is missing."}

    try:
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            image.thumbnail((768, 768))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=82, optimize=True)
    except (UnidentifiedImageError, OSError) as exc:
        logger.warning("Framewise image load failed for %s: %s", image_path, exc)
        return {"available": False, "reason": "The selected gallery image could not be prepared for vision analysis."}

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "available": True,
        "image_id": row["id"],
        "filename": row["filename"],
        "width_in": row["width_in"],
        "height_in": row["height_in"],
        "ratio_label": row["ratio_label"],
        "crop_json": row["crop_json"],
        "data_url": f"data:image/jpeg;base64,{encoded}",
    }


def _default_visual_analysis(image_payload: dict[str, Any]) -> dict[str, Any]:
    if image_payload.get("available"):
        return {
            "source": "image-not-analyzed",
            "summary": "A selected artwork image is available, but no vision model analysis was returned.",
            "dominant_colors": [],
            "temperature": "unknown",
            "contrast": "unknown",
            "style": "unknown",
            "framing_notes": [],
        }
    return {
        "source": "no-image",
        "summary": image_payload.get("reason") or "No selected artwork image was available.",
        "dominant_colors": [],
        "temperature": "unknown",
        "contrast": "unknown",
        "style": "unknown",
        "framing_notes": [],
    }


def _clean_visual_analysis(value: Any, image_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return _default_visual_analysis(image_payload)
    colors = value.get("dominant_colors") or []
    notes = value.get("framing_notes") or []
    return {
        "source": "vision-model" if image_payload.get("available") else "text-only-model",
        "summary": str(value.get("summary") or "")[:500],
        "dominant_colors": [str(color)[:40] for color in colors[:6] if str(color).strip()],
        "temperature": str(value.get("temperature") or "unknown")[:40],
        "contrast": str(value.get("contrast") or "unknown")[:40],
        "style": str(value.get("style") or "unknown")[:80],
        "framing_notes": [str(note)[:180] for note in notes[:5] if str(note).strip()],
    }


def _parse_provider_json(text: str) -> dict[str, Any]:
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.strip("`")
        clean = clean.removeprefix("json").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        start = clean.find("{")
        end = clean.rfind("}")
        if start >= 0 and end > start:
            return json.loads(clean[start : end + 1])
        raise


def _starter_suggestions(
    subject: str,
    goal: str,
    mouldings: list[dict[str, Any]],
    mats: list[dict[str, Any]],
    visual_analysis: dict[str, Any] | None = None,
    provider_directions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    visual = visual_analysis or {}
    visual_summary = str(visual.get("summary") or "").strip()
    color_summary = ", ".join(str(color) for color in (visual.get("dominant_colors") or [])[:4])
    templates = [
        {
            "title": "Quiet Gallery Contrast",
            "summary": "A clean presentation that lets the art do most of the talking.",
            "why": "Use a restrained frame and a light top mat so the customer's eye lands on the image first.",
            "conversation_tip": "This is the safest counter option when the customer wants it polished but not loud.",
            "mat_border_in": 2.5,
        },
        {
            "title": "Warm Natural Depth",
            "summary": "A warmer frame direction for travel, family, landscape, and memory pieces.",
            "why": "Wood tones and a soft mat usually make photographs feel more personal without getting busy.",
            "conversation_tip": "Good when the customer says the piece is sentimental or wants it to feel inviting.",
            "mat_border_in": 3.0,
        },
        {
            "title": "Crisp Modern Edge",
            "summary": "A sharper contemporary treatment with stronger contrast.",
            "why": "A darker frame and neutral mat can make color photographs and graphic pieces feel intentional.",
            "conversation_tip": "Offer this when the customer likes clean rooms, black fixtures, or modern decor.",
            "mat_border_in": 2.25,
        },
    ]
    if provider_directions:
        for index, direction in enumerate(provider_directions[:3]):
            templates[index].update(
                {
                    "title": str(direction.get("title") or templates[index]["title"])[:80],
                    "summary": str(direction.get("summary") or templates[index]["summary"])[:260],
                    "why": str(direction.get("why") or templates[index]["why"])[:420],
                    "conversation_tip": str(direction.get("conversation_tip") or templates[index]["conversation_tip"])[:260],
                }
            )

    suggestions: list[dict[str, Any]] = []
    for index, template in enumerate(templates):
        moulding = mouldings[index % len(mouldings)] if mouldings else None
        top_mat = mats[index % len(mats)] if mats else None
        second_mat = mats[(index + 1) % len(mats)] if len(mats) > 1 and index != 0 else None
        subject_note = f" Subject: {subject.strip()}" if subject.strip() else ""
        goal_note = f" Goal: {goal.strip()}" if goal.strip() else ""
        vision_note = f" Visual read: {visual_summary}" if visual_summary else ""
        color_note = f" Dominant colors: {color_summary}." if color_summary else ""
        suggestions.append(
            {
                "id": f"look-{index + 1}",
                "title": template["title"],
                "summary": template["summary"],
                "why": f"{template['why']}{subject_note}{goal_note}{vision_note}{color_note}",
                "conversation_tip": template["conversation_tip"],
                "selections": {
                    "moulding": _compact_item(moulding),
                    "top_mat": _compact_item(top_mat),
                    "second_mat": _compact_item(second_mat),
                    "mat_border_in": template["mat_border_in"],
                    "second_mat_reveal_in": 0.25 if second_mat else 0,
                },
                "catalog_summary": {
                    "moulding": _catalog_label(moulding),
                    "top_mat": _catalog_label(top_mat),
                    "second_mat": _catalog_label(second_mat) if second_mat else "",
                },
            }
        )
    return suggestions


async def _provider_design_directions(
    config: dict[str, Any],
    req: FramewiseDesignRequest,
    mouldings: list[dict[str, Any]],
    mats: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not config["enabled"]:
        return [], _default_visual_analysis({})
    image_payload = _framewise_image_payload(_image_id_from_request(req))
    catalog_sample = {
        "mouldings": [_compact_item(item) for item in mouldings[:8]],
        "mats": [_compact_item(item) for item in mats[:8]],
    }
    prompt = {
        "task": "Suggest three framing directions for a retail frame counter.",
        "rules": [
            "Return JSON only.",
            "Do not invent catalog item numbers.",
            "Analyze the artwork image when one is attached.",
            "Use plain shop-floor language a customer can understand.",
        ],
        "subject": req.subject,
        "goal": req.goal,
        "current_quote_context": req.quote_context,
        "selected_image": {
            key: image_payload.get(key)
            for key in ["available", "image_id", "filename", "width_in", "height_in", "ratio_label", "reason"]
        },
        "available_catalog_sample": catalog_sample,
        "schema": {
            "visual_analysis": {
                "summary": "one sentence about the artwork",
                "dominant_colors": ["color names visible in the artwork"],
                "temperature": "warm, cool, or mixed",
                "contrast": "low, medium, or high",
                "style": "photograph, painting, document, graphic, etc.",
                "framing_notes": ["specific visual cues that should guide framing"],
            },
            "suggestions": [
                {
                    "title": "short display title",
                    "summary": "one sentence",
                    "why": "why this works",
                    "conversation_tip": "what the employee can say",
                }
            ]
        },
    }
    user_content: str | list[dict[str, Any]]
    prompt_text = json.dumps(prompt, indent=2)
    if image_payload.get("available"):
        user_content = [
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": image_payload["data_url"]}},
        ]
    else:
        user_content = prompt_text
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 700,
        "temperature": config["temperature"],
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Content-Type": "application/json",
        **({"Authorization": f"Bearer {config['api_key']}"} if config.get("api_key") else {}),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(_chat_url(config["base_url"]), json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    content = data["choices"][0]["message"]["content"]
    parsed = _parse_provider_json(content)
    suggestions = parsed.get("suggestions") or []
    visual_analysis = _clean_visual_analysis(parsed.get("visual_analysis"), image_payload)
    return [item for item in suggestions if isinstance(item, dict)], visual_analysis


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


@router.post("/design-ideas")
async def framewise_design_ideas(req: FramewiseDesignRequest) -> dict[str, Any]:
    config = _stored_config(include_secret=True)
    mouldings = _catalog_rows("mould", 18)
    mats = _catalog_rows("mat", 18)
    provider_directions: list[dict[str, Any]] = []
    image_payload = _framewise_image_payload(_image_id_from_request(req))
    visual_analysis = _default_visual_analysis(image_payload)
    source = "local-starter"
    provider_error = ""
    if config["enabled"]:
        try:
            provider_directions, visual_analysis = await _provider_design_directions(config, req, mouldings, mats)
            if provider_directions:
                source = "vision-guided" if visual_analysis.get("source") == "vision-model" else "provider-guided"
        except Exception as exc:
            logger.warning("Framewise design provider error: %s", exc)
            provider_error = "Framewise could not reach the configured model, so local starter looks were used."
    suggestions = _starter_suggestions(req.subject, req.goal, mouldings, mats, visual_analysis, provider_directions)
    return {
        "assistant_name": config["assistant_name"],
        "enabled": config["enabled"],
        "source": source,
        "provider_error": provider_error,
        "image": {key: image_payload.get(key) for key in ["available", "image_id", "filename", "width_in", "height_in", "ratio_label", "reason"]},
        "visual_analysis": visual_analysis,
        "catalog_counts": {"mouldings": len(mouldings), "mats": len(mats)},
        "suggestions": suggestions,
    }
