# Windows Install

FramersHaven runs as a local app on a trusted Windows workstation. It starts a small local web server and opens the app in your browser.

## Install on a Fresh Windows Machine

On Windows 10 or Windows 11, open PowerShell and run:

```powershell
$installer="$env:TEMP\FramersHaven-install.ps1"; Invoke-WebRequest https://raw.githubusercontent.com/wspotter/FramersHaven/main/install_windows.ps1 -OutFile $installer; & ([scriptblock]::Create((Get-Content -Raw $installer)))
```

The installer:

- installs the app under `%LOCALAPPDATA%\FramersHaven`
- uses Python 3.11 or newer when it is already installed
- installs Python 3.12 through `winget` only when Python 3.11 or newer is missing
- creates the app's virtual environment and installs its dependencies
- creates fictional demo data only when `studio.db` does not exist
- starts the app and opens `http://127.0.0.1:8000`

If the installer cannot be downloaded, use the manual fallback below.

## Manual ZIP Fallback

1. Download the repository ZIP from GitHub.
2. Unzip it into a folder on the workstation.
3. Open that folder and double-click `run_windows.bat`.

The launcher creates `venv\` if needed, installs dependencies, creates the
fictional demo workspace only if `studio.db` is missing, opens
`http://127.0.0.1:8000`, and keeps the app running until you press `Ctrl-C`.

For this fallback, install Python 3.11 or newer first. If you install Python
manually, enable **Add python.exe to PATH**.

## Existing Data

The installer reuses an existing FramersHaven installation at
`%LOCALAPPDATA%\FramersHaven`; it does not delete or replace that installation.
Neither install path overwrites an existing `studio.db`. If you already have
data, the launcher starts the existing workspace.

Runtime data stays local:

- `studio.db`
- `uploads\`
- `exports\`
- `backups\`
- `catalog_previews\`
- `catalog_imports\`

Back up these files before moving the app to another workstation.

## If Installation Stops

- If Python was just installed but cannot be detected, close PowerShell, open a
  new PowerShell window, and run the install command again.
- If `winget` is unavailable or Python installation fails, install Python 3.12
  from [python.org](https://www.python.org/downloads/windows/), then rerun the
  command.
- If `%LOCALAPPDATA%\FramersHaven` already exists but is not a FramersHaven
  installation, rename that folder and rerun the command. Do not delete it if
  it may contain data you need.
- If the launcher reports that an existing `venv` uses Python older than 3.11,
  rename or remove only the `venv` folder, then run the launcher again. This
  does not remove `studio.db` or the runtime-data folders listed above.
- If the raw installer cannot be downloaded, use the manual ZIP fallback.

## Trusted LAN Use

By default, the Windows launcher binds to the local machine only.

To let another computer on the same trusted private LAN connect, run:

```cmd
set HOST=0.0.0.0
run_windows.bat
```

Then open `http://WORKSTATION-IP:8000` from the other computer.

Do not expose FramersHaven directly to the public internet. It does not include
internet-facing authentication hardening, TLS termination, or hosted-service
hardening.
