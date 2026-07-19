#!/usr/bin/env python3
"""Run a repeatable Framewise framing-suggestion evaluation.

The eval uses fictional generated artwork and a disposable local database. It
does not touch the operator's real `studio.db`, uploads, exports, or catalog.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import db
from app import main as main_module
from app.main import app

DEFAULT_MODEL = "hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M"
DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


SCENARIOS: list[dict[str, Any]] = [
    {"name": "safari_sunset", "subject": "African safari travel photograph, warm grasses, blue sky, customer wants polished but not flashy.", "size": (11, 14), "palette": ["#d7a84f", "#8c5b2f", "#6ea5c9", "#f1ddac"], "temperature": "warm"},
    {"name": "snowy_mountain", "subject": "Cool snowy mountain landscape with pale sky and dark pine trees.", "size": (16, 20), "palette": ["#dce7ef", "#8aa2b2", "#23313a", "#ffffff"], "temperature": "cool"},
    {"name": "black_white_portrait", "subject": "Black and white family portrait, high contrast, sentimental gift.", "size": (8, 10), "palette": ["#111111", "#f4f4f4", "#777777", "#d7d7d7"], "temperature": "neutral"},
    {"name": "bright_kids_art", "subject": "Bright children's painting with red, yellow, teal, and playful shapes.", "size": (12, 12), "palette": ["#f24b4b", "#f6d743", "#1fb7a6", "#ffffff"], "temperature": "warm"},
    {"name": "botanical_watercolor", "subject": "Soft botanical watercolor, sage greens, blush flowers, airy paper.", "size": (10, 14), "palette": ["#b9c7a6", "#e6a7ad", "#f5efe3", "#6f8f6b"], "temperature": "mixed"},
    {"name": "navy_certificate", "subject": "Formal navy and cream certificate with small gold seal.", "size": (11, 14), "palette": ["#172a4a", "#f3ead5", "#b88a32", "#222222"], "temperature": "cool"},
    {"name": "desert_panorama", "subject": "Wide desert panorama with terracotta cliffs and washed blue shadows.", "size": (24, 10), "palette": ["#c46f3c", "#dfb184", "#879fb6", "#f4e2c5"], "temperature": "warm"},
    {"name": "coastal_photo", "subject": "Beach photograph, soft sand, aqua water, light airy room.", "size": (14, 11), "palette": ["#d8c9a3", "#73b7c5", "#f8f6ed", "#527d8d"], "temperature": "cool"},
    {"name": "red_sports_jersey", "subject": "Signed red sports jersey shadowbox concept, bold and masculine.", "size": (18, 24), "palette": ["#b61f2a", "#111111", "#ffffff", "#747474"], "temperature": "warm"},
    {"name": "vintage_map", "subject": "Vintage map print, tan paper, sepia lines, old-world study decor.", "size": (18, 24), "palette": ["#d6bd8d", "#8b6d42", "#ede0bf", "#3c3325"], "temperature": "warm"},
    {"name": "abstract_neon", "subject": "Modern abstract print with magenta, teal, black, and white.", "size": (16, 16), "palette": ["#e83e8c", "#20b8a6", "#111111", "#ffffff"], "temperature": "mixed"},
    {"name": "wedding_photo", "subject": "Warm wedding photograph, cream dress, greenery, sentimental heirloom.", "size": (11, 14), "palette": ["#f1e4d0", "#8d9f72", "#c59b6d", "#ffffff"], "temperature": "warm"},
    {"name": "blue_diploma", "subject": "University diploma with blue crest and clean white paper.", "size": (11, 14), "palette": ["#ffffff", "#1f4e79", "#d6ba68", "#222222"], "temperature": "cool"},
    {"name": "charcoal_sketch", "subject": "Loose charcoal figure sketch on warm cream paper.", "size": (9, 12), "palette": ["#2b2b2b", "#e8dcc5", "#6b6255", "#f7f0e2"], "temperature": "neutral"},
    {"name": "autumn_forest", "subject": "Autumn forest photograph, orange leaves, deep shadows, cozy room.", "size": (16, 20), "palette": ["#c76b2d", "#7f3f1d", "#2f3a26", "#e0b06b"], "temperature": "warm"},
    {"name": "minimal_line_art", "subject": "Minimal black line art on white paper, modern apartment.", "size": (12, 16), "palette": ["#ffffff", "#111111", "#e8e8e8", "#cfcfcf"], "temperature": "neutral"},
    {"name": "purple_flower_photo", "subject": "Close-up purple flower photograph with deep green background.", "size": (12, 12), "palette": ["#68458f", "#2f4f34", "#c8a6d9", "#111b12"], "temperature": "cool"},
    {"name": "old_family_photo", "subject": "Small sepia family photograph, archival and nostalgic.", "size": (5, 7), "palette": ["#a98258", "#f0ddbf", "#4b3623", "#d5b88b"], "temperature": "warm"},
    {"name": "city_night", "subject": "City night photograph, blue-black sky, yellow lights, high contrast.", "size": (14, 18), "palette": ["#10192a", "#f2bd4b", "#283b5c", "#05070d"], "temperature": "cool"},
    {"name": "pastel_nursery", "subject": "Pastel nursery illustration, soft pink, pale mint, gentle mood.", "size": (10, 10), "palette": ["#f2b8c6", "#bddccc", "#fff5ec", "#d9c1d8"], "temperature": "warm"},
    {"name": "green_landscape_oil", "subject": "Traditional green landscape oil painting, dark trees, golden field.", "size": (20, 16), "palette": ["#2f4a2e", "#7d8a42", "#d5a047", "#4a351f"], "temperature": "warm"},
    {"name": "comic_art", "subject": "Comic-style art print with bold black outlines and saturated primaries.", "size": (11, 17), "palette": ["#f13232", "#2459d9", "#f5d833", "#111111"], "temperature": "mixed"},
    {"name": "ocean_storm", "subject": "Stormy ocean photograph, gray blue water, dramatic clouds.", "size": (20, 14), "palette": ["#526778", "#9aa7ad", "#26313b", "#d1d8dc"], "temperature": "cool"},
    {"name": "cream_gold_invitation", "subject": "Cream and gold event invitation, formal typography, elegant.", "size": (8, 10), "palette": ["#f7ecd5", "#c29b43", "#ffffff", "#4a3a22"], "temperature": "warm"},
]

CATALOG_ROWS = [
    ["FW-BLK-101", "Graphite Flat", "moulding", "3.25", "1.50", "Framewise Demo"],
    ["FW-MAP-102", "Natural Maple", "moulding", "4.10", "1.25", "Framewise Demo"],
    ["FW-WAL-103", "Wide Walnut Panel", "moulding", "7.95", "3.00", "Framewise Demo"],
    ["FW-SIL-104", "Soft Silver Scoop", "moulding", "5.50", "2.00", "Framewise Demo"],
    ["FW-GLD-105", "Antique Gold Bevel", "moulding", "5.75", "1.75", "Framewise Demo"],
    ["FW-WHT-201", "Warm White", "mat", "14.00", "32.0", "Framewise Demo"],
    ["FW-BLU-202", "Deep Blue", "mat", "14.00", "32.0", "Framewise Demo"],
    ["FW-BLS-203", "Soft Blush", "mat", "14.00", "32.0", "Framewise Demo"],
    ["FW-CRM-204", "Gallery Cream", "mat", "14.00", "32.0", "Framewise Demo"],
    ["FW-CHR-205", "Charcoal", "mat", "14.00", "32.0", "Framewise Demo"],
    ["FW-SGE-206", "Sage", "mat", "14.00", "32.0", "Framewise Demo"],
    ["FW-TAN-207", "Desert Tan", "mat", "14.00", "32.0", "Framewise Demo"],
]


def build_artwork(scenario: dict[str, Any]) -> bytes:
    width, height = 960, 720
    image = Image.new("RGB", (width, height), scenario["palette"][0])
    draw = ImageDraw.Draw(image)
    band = width // len(scenario["palette"])
    for index, color in enumerate(scenario["palette"]):
        draw.rectangle((index * band, 0, (index + 1) * band + 2, height), fill=color)
    draw.rectangle((80, 80, width - 80, height - 80), outline="#ffffff", width=10)
    draw.ellipse((220, 150, 740, 570), fill=scenario["palette"][-1], outline="#222222", width=6)
    draw.rectangle((320, 240, 640, 480), fill=scenario["palette"][1], outline="#ffffff", width=6)
    draw.text((90, height - 70), scenario["name"].replace("_", " ").title(), fill="#ffffff")
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def safe_photo_label(path: Path) -> str:
    folder_digest = hashlib.sha1(str(path.parent).encode("utf-8")).hexdigest()[:8]
    photo_digest = hashlib.sha1(path.name.encode("utf-8")).hexdigest()[:8]
    return f"folder-{folder_digest}/photo-{photo_digest}"


def load_photo_bytes(path: Path, max_side: int = 1600) -> tuple[bytes, tuple[int, int]]:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        original_size = image.size
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=90, optimize=True)
        return output.getvalue(), original_size


def build_photo_scenario(path: Path) -> dict[str, Any] | None:
    try:
        with Image.open(path) as image:
            width, height = image.size
    except (OSError, UnidentifiedImageError):
        return None
    if width < 400 or height < 300:
        return None
    label = safe_photo_label(path)
    ratio_width = 14
    ratio_height = max(8, round(ratio_width * height / width))
    return {
        "name": label,
        "subject": (
            "Customer photo or artwork from the real sample set. Inspect the image for dominant colors, "
            "warm/cool temperature, contrast, and mood, then suggest three sellable custom framing looks."
        ),
        "size": (ratio_width, ratio_height),
        "temperature": "unknown",
        "image_path": path,
        "source_label": label,
        "dimensions": (width, height),
    }


def discover_photo_scenarios(args: argparse.Namespace) -> list[dict[str, Any]]:
    if not args.image_dir:
        return SCENARIOS[: args.count]
    image_dir = args.image_dir.expanduser()
    rng = random.Random(args.seed)
    folders: dict[Path, list[Path]] = {}
    scanned = 0
    for path in image_dir.rglob("*"):
        if args.max_scan and scanned >= args.max_scan:
            break
        if not path.is_file() or path.suffix.lower() not in PHOTO_EXTENSIONS:
            continue
        scanned += 1
        folders.setdefault(path.parent, []).append(path)
    for folder_paths in folders.values():
        rng.shuffle(folder_paths)
    folder_order = list(folders)
    rng.shuffle(folder_order)
    candidates: list[Path] = []
    while folder_order:
        next_order: list[Path] = []
        for folder in folder_order:
            folder_paths = folders[folder]
            if folder_paths:
                candidates.append(folder_paths.pop())
            if folder_paths:
                next_order.append(folder)
        folder_order = next_order
    scenarios: list[dict[str, Any]] = []
    for path in candidates:
        scenario = build_photo_scenario(path)
        if scenario:
            scenarios.append(scenario)
        if len(scenarios) >= args.count:
            break
    if len(scenarios) < args.count:
        raise RuntimeError(f"Only found {len(scenarios)} usable photos in {image_dir}; requested {args.count}.")
    return scenarios


def catalog_csv() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["sku", "name", "category", "cost", "width_in", "vendor"])
    writer.writerows(CATALOG_ROWS)
    return output.getvalue()


def configure_provider(client: TestClient, args: argparse.Namespace) -> None:
    if not args.provider:
        return
    response = client.post(
        "/api/framewise/config",
        data={
            "enabled": "on",
            "assistant_name": "Framewise",
            "provider_type": args.provider_type,
            "base_url": args.base_url,
            "model": args.model,
            "api_key": args.api_key,
            "context_tokens": str(args.context_tokens),
            "temperature": str(args.temperature),
        },
    )
    response.raise_for_status()


def upload_scenario_image(client: TestClient, scenario: dict[str, Any]) -> int:
    width_in, height_in = scenario["size"]
    if scenario.get("image_path"):
        image_bytes, _ = load_photo_bytes(scenario["image_path"])
        filename = f"{scenario['source_label'].replace('/', '_')}.jpg"
        media_type = "image/jpeg"
    else:
        image_bytes = build_artwork(scenario)
        filename = f"{scenario['name']}.png"
        media_type = "image/png"
    response = client.post(
        "/api/images/upload",
        data={
            "width_in": str(width_in),
            "height_in": str(height_in),
            "ratio_label": f"{width_in}:{height_in}",
            "crop_json": "{}",
        },
        files={
            "file": (
                filename,
                image_bytes,
                media_type,
            )
        },
    )
    response.raise_for_status()
    return int(response.json()["id"])


def score_case(payload: dict[str, Any], provider_expected: bool) -> tuple[bool, list[str]]:
    issues: list[str] = []
    suggestions = payload.get("suggestions") or []
    if len(suggestions) != 3:
        issues.append(f"expected 3 suggestions, got {len(suggestions)}")
    for index, suggestion in enumerate(suggestions, start=1):
        selections = suggestion.get("selections") or {}
        if not (selections.get("moulding") or {}).get("sku"):
            issues.append(f"look {index} missing moulding sku")
        if not (selections.get("top_mat") or {}).get("sku"):
            issues.append(f"look {index} missing top mat sku")
        if not suggestion.get("conversation_tip"):
            issues.append(f"look {index} missing conversation tip")
    text = json.dumps(payload)
    for private_name in ["Ollie", "Printery", "Katherine", "Stacy"]:
        if private_name in text:
            issues.append(f"private name leaked: {private_name}")
    if provider_expected and payload.get("source") != "vision-guided":
        issues.append(f"expected vision-guided source, got {payload.get('source')}")
    return not issues, issues


def run_eval(args: argparse.Namespace) -> dict[str, Any]:
    temp_root = Path(tempfile.mkdtemp(prefix="framewise-eval-"))
    original = {
        "db_path": db.DB_PATH,
        "backup_dir": main_module.BACKUP_DIR,
        "preview_dir": main_module.PREVIEW_DIR,
        "catalog_import_dir": main_module.CATALOG_IMPORT_DIR,
        "upload_dir": main_module.UPLOAD_DIR,
    }
    db.DB_PATH = temp_root / "studio.db"
    main_module.BACKUP_DIR = temp_root / "backups"
    main_module.PREVIEW_DIR = temp_root / "catalog_previews"
    main_module.CATALOG_IMPORT_DIR = temp_root / "catalog_imports"
    main_module.UPLOAD_DIR = temp_root / "uploads"
    for path in [main_module.BACKUP_DIR, main_module.PREVIEW_DIR, main_module.CATALOG_IMPORT_DIR, main_module.UPLOAD_DIR]:
        path.mkdir(parents=True, exist_ok=True)

    try:
        with TestClient(app) as client:
            client.post(
                "/api/catalog/import",
                files={"file": ("framewise_eval_catalog.csv", catalog_csv(), "text/csv")},
            ).raise_for_status()
            configure_provider(client, args)
            status = client.get("/api/framewise/status").json() if args.provider else {"enabled": False, "available": False}
            cases = []
            scenarios = discover_photo_scenarios(args)
            for scenario in scenarios:
                image_id = upload_scenario_image(client, scenario)
                response = client.post(
                    "/api/framewise/design-ideas",
                    json={
                        "subject": scenario["subject"],
                        "goal": "Suggest three customer-friendly framing looks from the local catalog.",
                        "image_id": image_id,
                        "quote_context": {
                            "width_in": scenario["size"][0],
                            "height_in": scenario["size"][1],
                            "expected_temperature": scenario["temperature"],
                        },
                    },
                )
                response.raise_for_status()
                payload = response.json()
                ok, issues = score_case(payload, args.provider)
                cases.append(
                    {
                        "name": scenario["name"],
                        "source_label": scenario.get("source_label"),
                        "dimensions": scenario.get("dimensions"),
                        "ok": ok,
                        "issues": issues,
                        "source": payload.get("source"),
                        "image_available": (payload.get("image") or {}).get("available"),
                        "visual_analysis": payload.get("visual_analysis"),
                        "suggestions": [
                            {
                                "title": item.get("title"),
                                "moulding": ((item.get("selections") or {}).get("moulding") or {}).get("sku"),
                                "top_mat": ((item.get("selections") or {}).get("top_mat") or {}).get("sku"),
                                "second_mat": ((item.get("selections") or {}).get("second_mat") or {}).get("sku"),
                            }
                            for item in (payload.get("suggestions") or [])
                        ],
                    }
                )
    finally:
        db.DB_PATH = original["db_path"]
        main_module.BACKUP_DIR = original["backup_dir"]
        main_module.PREVIEW_DIR = original["preview_dir"]
        main_module.CATALOG_IMPORT_DIR = original["catalog_import_dir"]
        main_module.UPLOAD_DIR = original["upload_dir"]
        main_module._catalog_preview_basename_index.cache_clear()
        if not args.keep_temp:
            shutil.rmtree(temp_root, ignore_errors=True)

    passed = sum(1 for case in cases if case["ok"])
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "provider" if args.provider else "fallback",
        "dataset": "photos" if args.image_dir else "synthetic",
        "image_dir_label": args.image_dir.name if args.image_dir else None,
        "sample_strategy": "folder-balanced" if args.image_dir else "fixed-scenarios",
        "provider": {
            "base_url": args.base_url,
            "model": args.model,
            "status": status,
        },
        "summary": {
            "total": len(cases),
            "passed": passed,
            "failed": len(cases) - passed,
        },
        "cases": cases,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Framewise evaluation scenarios.")
    parser.add_argument("--count", type=int, default=24)
    parser.add_argument("--image-dir", type=Path, default=None, help="Sample real photos from this directory instead of generated artwork.")
    parser.add_argument("--seed", type=int, default=20260718, help="Deterministic random seed for real-photo sampling.")
    parser.add_argument("--max-scan", type=int, default=0, help="Maximum candidate image files to scan; 0 means no limit.")
    parser.add_argument("--provider", action="store_true", help="Enable the configured provider and expect vision-guided results.")
    parser.add_argument("--provider-type", default="ollama", choices=["ollama", "llama.cpp", "lm-studio", "openai-compatible"])
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--context-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--keep-temp", action="store_true", help="Keep the disposable temp workspace for debugging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_eval(args)
    output = args.output
    if output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = ROOT / "tmp" / f"framewise-eval-{report['mode']}-{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = report["summary"]
    print(f"Framewise eval {report['mode']}: {summary['passed']}/{summary['total']} passed")
    print(f"Report: {output}")
    failures = [case for case in report["cases"] if not case["ok"]]
    for case in failures[:8]:
        print(f"- {case['name']}: {'; '.join(case['issues'])}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
