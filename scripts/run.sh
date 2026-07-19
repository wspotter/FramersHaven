#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/venv/bin/python"
REQUIREMENTS_STAMP="${ROOT_DIR}/.install/requirements.txt"

needs_bootstrap=0
if [[ ! -x "${PYTHON_BIN}" ]]; then
  needs_bootstrap=1
elif ! "${PYTHON_BIN}" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1; then
  needs_bootstrap=1
elif [[ ! -f "${REQUIREMENTS_STAMP}" ]] || ! cmp -s "${ROOT_DIR}/requirements.txt" "${REQUIREMENTS_STAMP}"; then
  needs_bootstrap=1
fi

if [[ "${needs_bootstrap}" == "1" ]]; then
  "${ROOT_DIR}/scripts/bootstrap_unix.sh" --no-launch
fi

cd "${ROOT_DIR}"
exec "${PYTHON_BIN}" "${ROOT_DIR}/scripts/launch.py"
