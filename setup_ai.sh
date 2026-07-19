#!/usr/bin/env bash
set -euo pipefail

MODEL="hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M"

download_file() {
  local url="$1"
  local destination="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${url}" -o "${destination}"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "${url}" -O "${destination}"
  else
    echo "AI setup needs curl or wget to install Ollama." >&2
    return 1
  fi
}

find_ollama() {
  if command -v ollama >/dev/null 2>&1; then
    command -v ollama
    return 0
  fi
  local candidate
  for candidate in \
    /usr/local/bin/ollama \
    /opt/homebrew/bin/ollama \
    /Applications/Ollama.app/Contents/Resources/ollama; do
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

ollama_bin="$(find_ollama || true)"
if [[ -z "${ollama_bin}" ]]; then
  echo "Ollama is not installed. Running Ollama's official installer..."
  installer="$(mktemp "${TMPDIR:-/tmp}/framershaven-ollama.XXXXXX")"
  trap 'rm -f "${installer}"' EXIT
  download_file "https://ollama.com/install.sh" "${installer}"
  sh "${installer}"
  rm -f "${installer}"
  trap - EXIT
  ollama_bin="$(find_ollama || true)"
fi

if [[ -z "${ollama_bin}" ]]; then
  echo "Ollama installed but its command is not available yet." >&2
  echo "Restart the terminal, then run setup_ai.sh again." >&2
  exit 1
fi

if ! "${ollama_bin}" list >/dev/null 2>&1; then
  echo "Starting Ollama..."
  if [[ "$(uname -s)" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
    open -a Ollama >/dev/null 2>&1 || true
    for _ in {1..10}; do
      "${ollama_bin}" list >/dev/null 2>&1 && break
      sleep 1
    done
  fi
  if ! "${ollama_bin}" list >/dev/null 2>&1; then
    nohup "${ollama_bin}" serve > "${TMPDIR:-/tmp}/framershaven-ollama.log" 2>&1 &
  fi
  for _ in {1..30}; do
    "${ollama_bin}" list >/dev/null 2>&1 && break
    sleep 1
  done
fi

if ! "${ollama_bin}" list >/dev/null 2>&1; then
  echo "Ollama did not start. Start the Ollama app and run setup_ai.sh again." >&2
  exit 1
fi

echo "Downloading the optional Framewise vision model. This can take several minutes..."
"${ollama_bin}" pull "${MODEL}"
"${ollama_bin}" show "${MODEL}" >/dev/null

echo
echo "Framewise local AI is ready."
echo "Open FramersHaven, go to Admin > Framewise, enable it, then Save and Test."
echo "Provider: Ollama"
echo "URL: http://127.0.0.1:11434/v1"
echo "Model: ${MODEL}"
