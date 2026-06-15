#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON:-python3}"
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
ARGS=(-m uvicorn app.main:app --host "${HOST}" --port "${PORT}")
if [[ "${RELOAD:-0}" == "1" ]]; then
  ARGS+=(--reload)
fi

cd "${ROOT_DIR}"
exec "${PYTHON_BIN}" "${ARGS[@]}"
