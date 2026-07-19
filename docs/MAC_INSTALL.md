# macOS Install

FramersHaven runs locally on the Mac and opens in the default browser. The
basic app does not require Ollama, a GPU, or an AI model.

## Install

Open Terminal, paste this command, and press Return:

```bash
installer="$(mktemp)"; curl -fsSL https://raw.githubusercontent.com/wspotter/FramersHaven/main/install.sh -o "$installer" && bash "$installer"; rm -f "$installer"
```

The installer:

- installs FramersHaven under `~/Applications/FramersHaven`
- uses an existing Python 3.11 or newer when available
- installs a private Python 3.12 runtime through `uv` when needed
- creates an isolated `venv` and installs the app dependencies
- creates the starter workspace only when `studio.db` is missing
- starts FramersHaven and opens it in the default browser

The private Python fallback belongs only to FramersHaven. It does not replace
or modify Apple's system Python.

## Start It Again

In Finder, open your home folder, then `Applications`, then `FramersHaven`.
Double-click `Start FramersHaven.command`. Keep its Terminal window open while
using the app. Press `Ctrl-C` there to stop it.

You can also start it from Terminal:

```bash
"$HOME/Applications/FramersHaven/scripts/run.sh"
```

## Optional Framewise AI

The app remains fully usable without AI. To install Ollama and the recommended
local vision model, run:

```bash
"$HOME/Applications/FramersHaven/setup_ai.sh"
```

Apple Silicon is the preferred Mac hardware for the model. Ollama also supports
Intel Macs on current macOS, but inference is CPU-only and will be slower. See
[AI setup](AI_SETUP.md) before enabling Framewise.

## Existing Data

The installer never overwrites an existing `studio.db`. Workstation data lives
inside `~/Applications/FramersHaven`, including `studio.db`, `uploads/`,
`exports/`, `backups/`, `catalog_previews/`, and `catalog_imports/`. Back up
those paths before moving the installation.

## Troubleshooting

- If macOS blocks `Start FramersHaven.command`, Control-click it in Finder,
  choose **Open**, and confirm it came from your FramersHaven installation.
- If the browser does not open, leave Terminal running and open the local URL
  printed there.
- If port 8000 is busy, FramersHaven tries ports 8001-8010 automatically. To
  choose a port, run `PORT=8010 "$HOME/Applications/FramersHaven/scripts/run.sh"`.
- If installation reports a download or certificate error, verify the Mac's
  date and internet connection, then retry. A repository ZIP is the manual
  fallback.
- If a security product blocks Python or the launcher, allow only the files
  under `~/Applications/FramersHaven`; do not disable system security.

## Trusted Private LAN Use

The default is localhost-only. To opt in to another computer on the same
trusted private LAN, run:

```bash
HOST=0.0.0.0 "$HOME/Applications/FramersHaven/scripts/run.sh"
```

Do not expose FramersHaven directly to the public internet. It does not provide
internet-facing authentication, TLS termination, or hosted-service hardening.
