# Windows Install

FramersHaven runs as a local app on a trusted Windows workstation. It starts a small local web server and opens the app in your browser.

## Requirements

- Windows 10 or Windows 11
- Python 3.11 or newer
- Git, if cloning the repository instead of downloading a ZIP

When installing Python, enable **Add python.exe to PATH**.

## One-Click Local Start

1. Download or clone FramersHaven.
2. Open the FramersHaven folder.
3. Double-click `run_windows.bat`.

The launcher will:

- create `venv/` if needed
- install Python dependencies
- create the fictional demo workspace if `studio.db` does not exist
- open `http://127.0.0.1:8000`
- keep the app running until you press `Ctrl-C`

## PowerShell Install

```powershell
git clone https://github.com/wspotter/FramersHaven.git
cd FramersHaven
.\run_windows.bat
```

## Existing Data

`run_windows.bat` does not overwrite an existing `studio.db`. If you already have data, the launcher starts the existing workspace.

Runtime data stays local:

- `studio.db`
- `uploads\`
- `exports\`
- `backups\`
- `catalog_previews\`
- `catalog_imports\`

Back up these files before moving the app to another workstation.

## Trusted LAN Use

By default, the Windows launcher binds to the local machine only.

To let another computer on the same trusted private LAN connect, run:

```cmd
set HOST=0.0.0.0
run_windows.bat
```

Then open `http://WORKSTATION-IP:8000` from the other computer.

Do not expose FramersHaven directly to the public internet. It does not include internet-facing authentication, TLS termination, or hosted-service hardening.
