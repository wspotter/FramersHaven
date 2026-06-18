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

## Editions

FramersHaven operates in two editions:

- **Community Edition** is the default local-first workstation. It includes:
  - 1 studio profile
  - Up to 50 active catalog items
  - Up to 25 saved quotes/orders
  - Up to 1 successful local catalog package import
  - Manual quote, work order, and invoice workflow

- **Workstation Edition** removes the currently enforced catalog, saved order/quote, and local package-import limits. Additional Workstation conveniences, including accounting CSV export and expanded document branding, remain planned.

To use Workstation Edition, set the environment variable `FRAMERSHAVEN_EDITION=workstation` before starting the app.

No vendor catalogs, customer records, accounting credentials, or online billing flow are included in the repository. This is a local-first app. It does not provide payment processing, email/SMS sending, accounting CSV export, or accounting API sync. Do not expose it directly to the public internet.

## Quick Start

Requires Python 3.11 or newer.

### Windows

Double-click `run_windows.bat`, or run:

```powershell
.\run_windows.bat
```

The Windows launcher creates `venv/`, installs dependencies, creates demo data if needed, starts the local app, and opens `http://127.0.0.1:8000`.

See [Windows install](docs/WINDOWS_INSTALL.md) for details.

### macOS / Linux

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

The app is intended for a trusted workstation or private LAN. It does not provide internet-facing authentication, TLS termination, payment processing, or automated message delivery. Do not expose it directly to the public internet.

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
