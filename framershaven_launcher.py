from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Callable, Mapping, MutableMapping


APP_NAME = "FramersHaven"
DEFAULT_PORT = 8000
PORT_ATTEMPTS = 20
HEALTH_TIMEOUT_SECONDS = 30.0
LEGACY_DATA_NAMES = (
    "uploads",
    "exports",
    "backups",
    "catalog_previews",
    "catalog_imports",
    "studio.db",
)


def default_data_dir(env: Mapping[str, str] | None = None) -> Path:
    source = os.environ if env is None else env
    explicit = str(source.get("FRAMERSHAVEN_DATA_DIR") or "").strip()
    if explicit:
        return Path(explicit).expanduser()
    local_app_data = str(source.get("LOCALAPPDATA") or "").strip()
    if local_app_data:
        return Path(local_app_data) / APP_NAME / "Data"
    return Path.home() / ".framershaven"


def migrate_legacy_data(local_app_data: Path, data_dir: Path) -> list[str]:
    legacy_root = local_app_data / APP_NAME
    if data_dir.resolve() != (legacy_root / "Data").resolve():
        return []
    if (data_dir / "studio.db").exists() or not (legacy_root / "studio.db").exists():
        return []

    data_dir.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    for name in LEGACY_DATA_NAMES:
        source = legacy_root / name
        target = data_dir / name
        if not source.exists() or target.exists():
            continue
        shutil.move(str(source), str(target))
        moved.append(name)
    return moved


def configure_runtime_environment(data_dir: Path, env: MutableMapping[str, str] | None = None) -> None:
    target = os.environ if env is None else env
    resolved = data_dir.expanduser().resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    target["FRAMERSHAVEN_DATA_DIR"] = str(resolved)


def ensure_initial_workspace(data_dir: Path) -> None:
    database = data_dir / "studio.db"
    if database.exists():
        return
    from scripts.seed_demo import create_demo_data

    create_demo_data(database, data_dir / "uploads")


def select_available_port(start_port: int = DEFAULT_PORT, attempts: int = PORT_ATTEMPTS) -> int:
    for port in range(start_port, min(start_port + attempts, 65536)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            candidate.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                candidate.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No available local port between {start_port} and {start_port + attempts - 1}.")


def _open_without_proxy(request: urllib.request.Request, timeout: float):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(request, timeout=timeout)


def probe_server(port: int, timeout: float = 1.0) -> bool:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/health",
        headers={"Accept": "application/json"},
    )
    try:
        with _open_without_proxy(request, timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return False
    return payload.get("status") == "ok" and payload.get("app") == APP_NAME


def write_server_state(data_dir: Path, *, port: int, pid: int) -> None:
    state_path = data_dir / "server.json"
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"app": APP_NAME, "port": port, "pid": pid}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(state_path)


def find_running_port(data_dir: Path, probe: Callable[[int], bool] = probe_server) -> int | None:
    state_path = data_dir / "server.json"
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        port = int(payload["port"])
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        state_path.unlink(missing_ok=True)
        return None
    if payload.get("app") == APP_NAME and 1 <= port <= 65535 and probe(port):
        return port
    state_path.unlink(missing_ok=True)
    return None


def clear_server_state(data_dir: Path, pid: int) -> None:
    state_path = data_dir / "server.json"
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return
    if payload.get("pid") == pid:
        state_path.unlink(missing_ok=True)


def wait_for_server(port: int, timeout: float = HEALTH_TIMEOUT_SECONDS) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if probe_server(port):
            return True
        time.sleep(0.2)
    return False


def setup_logging(data_dir: Path) -> Path:
    log_dir = data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "launcher.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )
    return log_path


def show_fatal_error(message: str, log_path: Path) -> None:
    detail = f"{message}\n\nDetails were written to:\n{log_path}"
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, detail, f"{APP_NAME} could not start", 0x10)
            return
        except Exception:
            pass
    print(detail, file=sys.stderr)


def _open_browser_when_ready(port: int) -> None:
    if wait_for_server(port):
        webbrowser.open(f"http://127.0.0.1:{port}")
    else:
        logging.error("The local server did not become healthy within %.1f seconds", HEALTH_TIMEOUT_SECONDS)


def prepare_workspace(data_dir: Path) -> None:
    configure_runtime_environment(data_dir)
    ensure_initial_workspace(data_dir)


def run_smoke_test(data_dir: Path, requested_port: int = DEFAULT_PORT) -> int:
    prepare_workspace(data_dir)
    setup_logging(data_dir)
    port = select_available_port(requested_port)

    import uvicorn
    from app.main import app

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    )
    thread = threading.Thread(target=server.run, name="framershaven-smoke-server", daemon=True)
    thread.start()
    try:
        if not wait_for_server(port):
            logging.error("Packaged server health check failed")
            return 1
        request = urllib.request.Request(f"http://127.0.0.1:{port}/")
        with _open_without_proxy(request, 5.0) as response:
            body = response.read().decode("utf-8")
        if response.status != 200 or "FramersHaven" not in body:
            logging.error("Packaged home page check failed")
            return 1
        logging.info("Packaged smoke test passed on port %s", port)
        return 0
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def run_application(data_dir: Path, requested_port: int, open_browser: bool = True) -> int:
    configure_runtime_environment(data_dir)
    log_path = setup_logging(data_dir)
    running_port = find_running_port(data_dir)
    if running_port is not None:
        if open_browser:
            webbrowser.open(f"http://127.0.0.1:{running_port}")
        return 0

    try:
        ensure_initial_workspace(data_dir)
        port = select_available_port(requested_port)
        write_server_state(data_dir, port=port, pid=os.getpid())
        if open_browser:
            threading.Thread(
                target=_open_browser_when_ready,
                args=(port,),
                name="framershaven-browser-opener",
                daemon=True,
            ).start()

        import uvicorn
        from app.main import app

        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info", access_log=False)
        return 0
    except Exception as exc:
        logging.exception("FramersHaven startup failed")
        show_fatal_error(str(exc), log_path)
        return 1
    finally:
        clear_server_state(data_dir, os.getpid())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the local FramersHaven workstation.")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    data_dir = args.data_dir or default_data_dir()
    try:
        if args.data_dir is None and os.environ.get("LOCALAPPDATA"):
            migrate_legacy_data(Path(os.environ["LOCALAPPDATA"]), data_dir)
        if args.smoke_test:
            return run_smoke_test(data_dir, args.port)
        return run_application(data_dir, args.port, open_browser=not args.no_browser)
    except Exception as exc:
        configure_runtime_environment(data_dir)
        log_path = setup_logging(data_dir)
        logging.exception("FramersHaven startup failed")
        if args.smoke_test:
            print(f"FramersHaven smoke test failed: {exc}", file=sys.stderr)
        else:
            show_fatal_error(str(exc), log_path)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
