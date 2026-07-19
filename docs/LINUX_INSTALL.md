# Linux Install

FramersHaven runs as a local desktop workstation and opens in the default
browser. The basic app does not require Ollama, a GPU, Docker, or a cloud
account.

## Install

Open a terminal, paste this command, and press Enter:

```bash
installer="$(mktemp)"; curl -fsSL https://raw.githubusercontent.com/wspotter/FramersHaven/main/install.sh -o "$installer" && bash "$installer"; rm -f "$installer"
```

The installer:

- installs FramersHaven under `~/.local/share/FramersHaven`
- uses an existing Python 3.11 or newer when available
- installs a private Python 3.12 runtime through `uv` when needed
- creates an isolated `venv` and installs the app dependencies
- creates the starter workspace only when `studio.db` is missing
- adds FramersHaven to the desktop application menu
- starts the app and opens it in the default browser

The private Python fallback belongs only to FramersHaven and does not modify the
distribution's system Python.

## Start It Again

Open FramersHaven from the desktop application menu, or run:

```bash
"$HOME/.local/bin/framershaven"
```

Keep the terminal window open while using the app. Press `Ctrl-C` there to stop
it.

## Optional Framewise AI

The app remains fully usable without AI. To install Ollama from its official
installer and download the recommended local vision model, run:

```bash
"$HOME/.local/share/FramersHaven/setup_ai.sh"
```

Ollama installation may request `sudo` to install its service. FramersHaven
itself stays in your user account. See [AI setup](AI_SETUP.md) before enabling
Framewise.

## Existing Data

The installer never overwrites an existing `studio.db`. Workstation data lives
inside `~/.local/share/FramersHaven`, including `studio.db`, `uploads/`,
`exports/`, `backups/`, `catalog_previews/`, and `catalog_imports/`. Back up
those paths before moving the installation.

## Troubleshooting

- If the browser does not open, leave the terminal running and open the local
  URL printed there.
- If port 8000 is busy, FramersHaven tries ports 8001-8010 automatically. To
  choose a port, run `PORT=8010 "$HOME/.local/bin/framershaven"`.
- If the installer says `curl` is missing, install `curl` with the distribution
  package manager or use `wget` to download the repository ZIP.
- If the desktop icon does not appear immediately, log out and back in, or run
  the `~/.local/bin/framershaven` command directly.
- If Python packages cannot download, check the system clock, internet
  connection, proxy, and certificate configuration, then retry.

## Trusted Private LAN Use

The default is localhost-only. To opt in to another computer on the same
trusted private LAN, run:

```bash
HOST=0.0.0.0 "$HOME/.local/bin/framershaven"
```

Allow the chosen port through the workstation firewall only for the trusted
private LAN. Do not expose FramersHaven directly to the public internet. It does
not provide internet-facing authentication, TLS termination, or hosted-service
hardening.
