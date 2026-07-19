#!/usr/bin/env bash
set -euo pipefail

ARCHIVE_URL="${FRAMERSHAVEN_ARCHIVE_URL:-https://github.com/wspotter/FramersHaven/archive/refs/heads/main.tar.gz}"
NO_LAUNCH=0
INSTALL_ROOT="${FRAMERSHAVEN_INSTALL_ROOT:-}"

usage() {
  echo "Usage: $0 [--no-launch] [--install-root PATH]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-launch) NO_LAUNCH=1; shift ;;
    --install-root)
      [[ $# -ge 2 ]] || { echo "--install-root requires a path" >&2; exit 2; }
      INSTALL_ROOT="$2"
      shift 2
      ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

platform="$(uname -s)"
case "${platform}" in
  Darwin)
    default_root="${HOME}/Applications/FramersHaven"
    ;;
  Linux)
    default_root="${HOME}/.local/share/FramersHaven"
    ;;
  *)
    echo "This installer supports macOS and Linux. Use install_windows.ps1 on Windows." >&2
    exit 1
    ;;
esac
INSTALL_ROOT="${INSTALL_ROOT:-${default_root}}"
launcher="${INSTALL_ROOT}/scripts/run.sh"

download_file() {
  local url="$1"
  local destination="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${url}" -o "${destination}"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "${url}" -O "${destination}"
  else
    echo "Install curl or wget, then run this installer again." >&2
    return 1
  fi
}

if [[ -e "${INSTALL_ROOT}" ]]; then
  if [[ ! -f "${launcher}" ]]; then
    echo "The destination exists but is not a FramersHaven installation: ${INSTALL_ROOT}" >&2
    echo "Rename that folder if you need to keep it, then run this installer again." >&2
    exit 1
  fi
  echo "Using the existing FramersHaven installation at ${INSTALL_ROOT}"
else
  parent_dir="$(dirname "${INSTALL_ROOT}")"
  mkdir -p "${parent_dir}"
  staging_dir="$(mktemp -d "${TMPDIR:-/tmp}/framershaven-install.XXXXXX")"
  archive="${staging_dir}/FramersHaven.tar.gz"
  trap 'rm -rf "${staging_dir}"' EXIT

  echo "Downloading FramersHaven..."
  download_file "${ARCHIVE_URL}" "${archive}"
  tar -xzf "${archive}" -C "${staging_dir}"
  source_dir="$(find "${staging_dir}" -mindepth 1 -maxdepth 1 -type d -name 'FramersHaven-*' | head -n 1)"
  if [[ -z "${source_dir}" || ! -f "${source_dir}/scripts/run.sh" ]]; then
    echo "The downloaded FramersHaven archive has an unexpected layout." >&2
    exit 1
  fi
  mv "${source_dir}" "${INSTALL_ROOT}"
  rm -rf "${staging_dir}"
  trap - EXIT
fi

for executable in \
  "${INSTALL_ROOT}/install.sh" \
  "${INSTALL_ROOT}/setup_ai.sh" \
  "${INSTALL_ROOT}/Start FramersHaven.command" \
  "${INSTALL_ROOT}/scripts/bootstrap_unix.sh" \
  "${INSTALL_ROOT}/scripts/run.sh"; do
  [[ -f "${executable}" ]] && chmod +x "${executable}"
done

if [[ "${platform}" == "Linux" ]]; then
  bin_dir="${HOME}/.local/bin"
  applications_dir="${HOME}/.local/share/applications"
  mkdir -p "${bin_dir}" "${applications_dir}"
  printf '#!/usr/bin/env bash\nexec %q "$@"\n' "${INSTALL_ROOT}/scripts/run.sh" > "${bin_dir}/framershaven"
  chmod +x "${bin_dir}/framershaven"
  printf '%s\n' \
    '[Desktop Entry]' \
    'Type=Application' \
    'Name=FramersHaven' \
    'Comment=Local-first custom framing workstation' \
    "Exec=\"${bin_dir}/framershaven\"" \
    "Icon=${INSTALL_ROOT}/app/static/logo.png" \
    'Terminal=true' \
    'Categories=Office;Graphics;' \
    > "${applications_dir}/framershaven.desktop"
fi

"${INSTALL_ROOT}/scripts/bootstrap_unix.sh" --no-launch

echo
echo "Basic installation is complete. Local AI is optional."
echo "To add Framewise later, run: ${INSTALL_ROOT}/setup_ai.sh"

if [[ "${NO_LAUNCH}" == "0" ]]; then
  exec "${launcher}"
fi
