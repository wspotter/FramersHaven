# Windows Install

FramersHaven runs locally on Windows 10 or Windows 11. It starts a private
local server and opens the workstation in the default browser.

## Install

1. Download [FramersHaven-Setup.exe](https://github.com/wspotter/FramersHaven/releases/latest/download/FramersHaven-Setup.exe).
2. Open the downloaded file.
3. Finish setup, then launch FramersHaven from the Start menu or desktop.

The installer includes everything FramersHaven needs. It does not require
Python, Git, administrator rights, or command-line work.

## Windows SmartScreen

Windows may show **Windows protected your PC** while FramersHaven is new and
building a download reputation. Confirm the download came from the official
`wspotter/FramersHaven` release, then:

1. Select **More info**.
2. Select **Run anyway**.

Do not bypass a warning for a copy obtained from an unofficial link.

## Existing Data

Program files are installed at:

```text
%LOCALAPPDATA%\Programs\FramersHaven
```

Customer data is stored separately at:

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

Installing a newer version preserves this data folder. Uninstalling and
reinstalling FramersHaven also preserves it. On first launch, the new installer
moves customer data from the earlier `%LOCALAPPDATA%\FramersHaven` layout into
the `Data` folder without deleting the earlier program files.

Use the in-app backup function before moving data to another workstation.
Launcher diagnostics are written to
`%LOCALAPPDATA%\FramersHaven\Data\logs\launcher.log`.

## Optional Framewise AI

FramersHaven works without Ollama or a model. To add the recommended local
vision model after the basic install, open PowerShell and run:

```powershell
& "$env:LOCALAPPDATA\Programs\FramersHaven\setup_ai_windows.ps1"
```

This explicit AI setup installs Ollama from its official installer when it is
missing and downloads the selected SmolVLM2 model. It does not upload shop data
or change the basic FramersHaven installation. See [AI setup](AI_SETUP.md) for
the final Framewise enable-and-test step.

## If Installation Stops

- Rerun the installer. An interrupted setup does not remove customer data.
- If Windows reports a security policy block without a **Run anyway** option,
  do not disable antivirus protection; that workstation requires its
  administrator to approve the application.
- If FramersHaven does not open, review
  `%LOCALAPPDATA%\FramersHaven\Data\logs\launcher.log` and include that file in
  a support request.
- If port 8000 is busy, FramersHaven automatically tries the next available
  local port.

## Network Boundary

The packaged Windows application binds to the local machine only. Source
developers can configure access from a trusted private LAN separately.

Do not expose FramersHaven directly to the public internet. It does not include
internet-facing authentication hardening, TLS termination, or hosted-service
hardening.
