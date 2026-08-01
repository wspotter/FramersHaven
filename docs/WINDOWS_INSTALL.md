# Windows Install

FramersHaven runs locally on Windows 10 or Windows 11. It starts a private
local server and opens the workstation in the default browser.

## Installer

1. Download `FramersHaven-Setup.exe` from the latest GitHub release.
2. Open the downloaded installer.
3. Finish setup, then launch FramersHaven from the Start menu or desktop.

The installer is per-user. It does not require Python, Git, administrator
rights, or command-line work. Starting FramersHaven again while it is already
running reopens the existing local session instead of starting a second copy.

## Existing Data

The installer keeps working data separate from program files at:

```text
%LOCALAPPDATA%\FramersHaven\Data
```

Runtime data stays local:

- `studio.db`
- `uploads\`
- `exports\`
- `backups\`
- `catalog_previews\`
- `catalog_imports\`

Installing a newer version preserves this folder. Uninstalling FramersHaven
also preserves it so an accidental uninstall does not erase shop records.
Use the in-app backup function before moving data to another workstation.

Launcher diagnostics are written to
`%LOCALAPPDATA%\FramersHaven\Data\logs\launcher.log`.

## Source Setup

Developers who clone the repository can run `run_windows.bat`. The source path
requires Python 3.11 or newer and creates a project-local virtual environment.

## Trusted LAN Use

The packaged installer binds to the local machine only. To make the source
launcher available to another computer on the same trusted private LAN, run:

```cmd
set HOST=0.0.0.0
run_windows.bat
```

Then open `http://WORKSTATION-IP:8000` from the other computer.

Do not expose FramersHaven directly to the public internet. It does not include internet-facing authentication, TLS termination, or hosted-service hardening.
