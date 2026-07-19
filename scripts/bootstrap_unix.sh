#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/venv"
VENV_PYTHON="${VENV_DIR}/bin/python"
TOOLS_DIR="${ROOT_DIR}/.tools"
INSTALL_STATE_DIR="${ROOT_DIR}/.install"
REQUIREMENTS_STAMP="${INSTALL_STATE_DIR}/requirements.txt"
NO_LAUNCH=0

usage() {
  echo "Usage: $0 [--no-launch]"
}

for argument in "$@"; do
  case "${argument}" in
    --no-launch) NO_LAUNCH=1 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: ${argument}" >&2; usage >&2; exit 2 ;;
  esac
done

python_is_compatible() {
  local candidate="$1"
  command -v "${candidate}" >/dev/null 2>&1 || [[ -x "${candidate}" ]] || return 1
  "${candidate}" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1
}

find_python() {
  local candidates=()
  if [[ -n "${PYTHON:-}" ]]; then
    candidates+=("${PYTHON}")
  fi
  candidates+=(python3.14 python3.13 python3.12 python3.11 python3 python)
  local candidate
  for candidate in "${candidates[@]}"; do
    if python_is_compatible "${candidate}"; then
      command -v "${candidate}" 2>/dev/null || printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

download_file() {
  local url="$1"
  local destination="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${url}" -o "${destination}"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "${url}" -O "${destination}"
  else
    echo "FramersHaven needs curl or wget for the private Python fallback." >&2
    return 1
  fi
}

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return 0
  fi
  if [[ -x "${TOOLS_DIR}/uv" ]]; then
    printf '%s\n' "${TOOLS_DIR}/uv"
    return 0
  fi

  echo "A compatible Python was not available. Installing a private Python helper for FramersHaven..." >&2
  mkdir -p "${TOOLS_DIR}"
  local installer
  installer="$(mktemp "${TMPDIR:-/tmp}/framershaven-uv.XXXXXX")"
  if ! download_file "https://astral.sh/uv/install.sh" "${installer}"; then
    rm -f "${installer}"
    return 1
  fi
  if ! env UV_UNMANAGED_INSTALL="${TOOLS_DIR}" sh "${installer}" >/dev/null; then
    rm -f "${installer}"
    return 1
  fi
  rm -f "${installer}"
  [[ -x "${TOOLS_DIR}/uv" ]] || {
    echo "The private Python helper did not install correctly." >&2
    return 1
  }
  printf '%s\n' "${TOOLS_DIR}/uv"
}

create_venv() {
  local python_candidate=""
  python_candidate="$(find_python || true)"
  if [[ -n "${python_candidate}" ]]; then
    echo "Creating the FramersHaven Python environment..."
    if "${python_candidate}" -m venv "${VENV_DIR}"; then
      return 0
    fi
    echo "The system Python could not create a virtual environment; using a private Python runtime instead."
    rm -rf "${VENV_DIR}"
  fi

  local uv_bin
  uv_bin="$(ensure_uv)"
  echo "Installing a private Python 3.12 runtime for FramersHaven..."
  env UV_PYTHON_INSTALL_DIR="${TOOLS_DIR}/python" \
    "${uv_bin}" venv --seed --python 3.12 "${VENV_DIR}"
}

if ! python_is_compatible "${VENV_PYTHON}"; then
  if [[ -e "${VENV_DIR}" ]]; then
    backup_venv="${VENV_DIR}.incompatible.$(date +%Y%m%d%H%M%S)"
    echo "Moving the incompatible Python environment to ${backup_venv}"
    mv "${VENV_DIR}" "${backup_venv}"
  fi
  create_venv
fi

echo "Installing FramersHaven dependencies..."
"${VENV_PYTHON}" -m pip install --upgrade pip
"${VENV_PYTHON}" -m pip install -r "${ROOT_DIR}/requirements.txt"
mkdir -p "${INSTALL_STATE_DIR}"
cp "${ROOT_DIR}/requirements.txt" "${REQUIREMENTS_STAMP}"

if [[ ! -f "${ROOT_DIR}/studio.db" ]]; then
  echo "Creating the starter workspace..."
  "${VENV_PYTHON}" "${ROOT_DIR}/scripts/seed_demo.py"
fi

if [[ "${NO_LAUNCH}" == "0" ]]; then
  exec "${ROOT_DIR}/scripts/run.sh"
fi

echo "FramersHaven is ready at ${ROOT_DIR}"
