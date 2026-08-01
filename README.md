# FramersHaven

FramersHaven is a local-first workstation for custom framing shops. It combines artwork intake, visual design, material selection, quoting, production tracking, customer records, document previews, and backups in one browser-based application.

The included demo uses the fictional **FramersHaven** identity and generated sample data. No customer records, vendor catalogs, or operational credentials are distributed with the repository.

## Features

- Live framing mockup with stacked mats and moulding previews
- Gallery intake with non-destructive crop metadata
- Searchable mats, mouldings, and glazing catalog
- Configurable pricing, services, tax, and studio branding
- Quote, work-order, and invoice workflow
- PDF/JPG preview before save or customer handoff
- Customer history and local backup archives
- Multi-page operator help served by the app

## Quick Start

### Windows

Download `FramersHaven-Setup.exe` from the latest GitHub release and open it.
The installer does not require Python, Git, administrator rights, or a terminal.
It adds a Start menu shortcut and can add a desktop shortcut.

FramersHaven opens in the default browser and keeps its database, artwork,
exports, and backups under `%LOCALAPPDATA%\FramersHaven\Data`. Installing an
update or uninstalling the program does not delete that data.

Source developers can still run:

```powershell
.\run_windows.bat
```

That source launcher requires Python 3.11 or newer and installs dependencies
into a local virtual environment.

See [Windows install](docs/WINDOWS_INSTALL.md) for details.

### macOS / Linux

Requires Python 3.11 or newer.

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python scripts/seed_demo.py
./scripts/run.sh
```

Open `http://127.0.0.1:8000`. The launcher listens on `0.0.0.0:8000` by default for trusted LAN use. Set `HOST=127.0.0.1` to limit it to the local machine.

```bash
HOST=127.0.0.1 ./scripts/run.sh
```

The initial admin login is `admin` / `admin` unless you set
`FRAMERSHAVEN_BOOTSTRAP_EMAIL` and `FRAMERSHAVEN_BOOTSTRAP_PASSWORD` before the
first database is created. The packaged Windows app creates and reuses its own
local session secret. Source installs can set `FRAMERSHAVEN_SESSION_SECRET` for
the same behavior. `FRAMERSHAVEN_ALLOW_OPEN_ADMIN=1` is available only for
intentional trusted local/demo installs.

## Development

```bash
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m playwright install chromium
node -c app/static/app.js
node --test app/src/*.test.js
./venv/bin/python -m compileall app tests scripts
./venv/bin/python -m pytest -q tests
```

With the app running against demo data:

```bash
./venv/bin/python scripts/browser_smoke.py
./venv/bin/python scripts/generate_screenshots.py
```

## Data Safety

Runtime data is deliberately ignored by Git:

- `studio.db`
- `uploads/`
- `exports/`
- `backups/`
- `catalog_previews/`
- `catalog_imports/`

The app is intended for a trusted workstation or private LAN. Admin routes
require login by default, but the app does not provide TLS termination,
internet-facing rate limiting, payment processing, or automated message
delivery. Do not expose it directly to the public internet.

## Documentation

- [Windows install](docs/WINDOWS_INSTALL.md)
- [Operator manual](docs/USER_MANUAL.md)
- [Feature ledger](docs/FEATURES.md)
- [API reference](docs/API.md)
- [Architecture](ARCHITECTURE.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## License

The current public snapshot is source-available under the terms in [LICENSE](LICENSE). No open-source license has been granted yet.
