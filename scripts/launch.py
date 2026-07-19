#!/usr/bin/env python3
"""Start FramersHaven, choose a usable local port, and open the browser."""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Callable
from pathlib import Path

import uvicorn


DEFAULT_PORT = 8000
PORT_SEARCH_COUNT = 10
ROOT_DIR = Path(__file__).resolve().parent.parent


def parse_port(value: str) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("PORT must be a number from 1 to 65535") from exc
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be a number from 1 to 65535")
    return port


def port_available(host: str, port: int) -> bool:
    bind_host = "127.0.0.1" if host == "localhost" else host
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((bind_host, port))
    except OSError:
        return False
    return True


def choose_port(
    host: str,
    preferred: int,
    *,
    explicit: bool,
    available: Callable[[str, int], bool] = port_available,
) -> int:
    if available(host, preferred):
        return preferred
    if explicit:
        raise RuntimeError(f"Port {preferred} is already in use. Choose another PORT and try again.")
    for candidate in range(preferred + 1, min(preferred + PORT_SEARCH_COUNT, 65535) + 1):
        if available(host, candidate):
            return candidate
    raise RuntimeError(
        f"Ports {preferred}-{min(preferred + PORT_SEARCH_COUNT, 65535)} are already in use. "
        "Close another local server or set PORT to a free port."
    )


def browser_url(host: str, port: int) -> str:
    browser_host = "127.0.0.1" if host in {"0.0.0.0", "::", "localhost"} else host
    return f"http://{browser_host}:{port}"


def prepare_app_import(root: Path = ROOT_DIR) -> None:
    root_text = os.fspath(root)
    os.chdir(root)
    if not sys.path or sys.path[0] != root_text:
        sys.path.insert(0, root_text)


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _open_browser_when_ready(url: str) -> None:
    health_url = f"{url}/api/health"
    for _ in range(80):
        try:
            with urllib.request.urlopen(health_url, timeout=0.5) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)
    print(f"The browser did not open automatically. Open {url} yourself.", file=sys.stderr)


def main() -> int:
    prepare_app_import()
    host = os.environ.get("HOST", "127.0.0.1").strip() or "127.0.0.1"
    raw_port = os.environ.get("PORT")
    preferred = parse_port(raw_port or str(DEFAULT_PORT))
    port = choose_port(host, preferred, explicit=bool(raw_port and raw_port.strip()))
    url = browser_url(host, port)

    if port != preferred:
        print(f"Port {preferred} is busy; using {port} instead.")
    print(f"Starting FramersHaven at {url}")
    print("Press Ctrl-C in this window to stop the app.")

    if not _truthy(os.environ.get("NO_BROWSER")):
        threading.Thread(target=_open_browser_when_ready, args=(url,), daemon=True).start()

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=_truthy(os.environ.get("RELOAD")),
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"FramersHaven could not start: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
