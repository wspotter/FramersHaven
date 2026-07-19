from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
LAUNCHER = ROOT / "scripts" / "launch.py"


def load_launcher():
    assert LAUNCHER.is_file(), "scripts/launch.py is required"
    spec = importlib.util.spec_from_file_location("framershaven_launcher", LAUNCHER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_port_accepts_a_valid_tcp_port() -> None:
    parse_port = load_launcher().parse_port
    assert parse_port("8000") == 8000
    assert parse_port("65535") == 65535


@pytest.mark.parametrize("value", ["", "zero", "0", "65536"])
def test_parse_port_rejects_invalid_values(value: str) -> None:
    parse_port = load_launcher().parse_port
    with pytest.raises(ValueError, match="PORT must be a number from 1 to 65535"):
        parse_port(value)


def test_choose_port_uses_the_preferred_port_when_available() -> None:
    choose_port = load_launcher().choose_port
    assert choose_port("127.0.0.1", 8000, explicit=False, available=lambda _host, _port: True) == 8000


def test_choose_port_falls_forward_for_the_default_port() -> None:
    choose_port = load_launcher().choose_port
    occupied = {8000, 8001}
    selected = choose_port(
        "127.0.0.1",
        8000,
        explicit=False,
        available=lambda _host, port: port not in occupied,
    )
    assert selected == 8002


def test_choose_port_does_not_override_an_explicit_busy_port() -> None:
    choose_port = load_launcher().choose_port
    with pytest.raises(RuntimeError, match="Port 9000 is already in use"):
        choose_port("127.0.0.1", 9000, explicit=True, available=lambda _host, _port: False)


def test_browser_url_is_always_local_even_for_lan_binding() -> None:
    browser_url = load_launcher().browser_url
    assert browser_url("0.0.0.0", 8000) == "http://127.0.0.1:8000"
    assert browser_url("127.0.0.1", 8001) == "http://127.0.0.1:8001"


def test_prepare_app_import_adds_root_and_changes_working_directory(tmp_path, monkeypatch) -> None:
    prepare_app_import = load_launcher().prepare_app_import
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", ["fixture-path"])

    prepare_app_import(ROOT)

    assert Path.cwd() == ROOT
    assert sys.path[0] == os.fspath(ROOT)
