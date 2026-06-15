# FramersHaven Contributor Notes

## Product Direction

- Keep the Design workspace compact and operator-friendly.
- Keep the live mockup visually dominant.
- Browse materials in drawers rather than expanding the worksheet.
- Keep catalog materials separate from shop-priced services.
- Preserve exports, customer history, backups, migrations, and tests.

## Main Files

- `app/main.py`
- `app/db.py`
- `app/pricing.py`
- `app/templates/index.html`
- `app/static/app.js`
- `tests/test_api.py`
- `tests/test_pricing.py`

## Data Safety

Never commit `studio.db`, uploads, exports, backups, catalog previews, vendor packages, credentials, or real customer data. Database changes must include migration support in `app/db.py` so existing workstations continue to start.

## Verification

```bash
node -c app/static/app.js
node --test app/src/*.test.js
./venv/bin/python -m compileall app tests scripts
./venv/bin/python -m pytest -q tests
```

For UI changes, run the demo seed, start the app, and execute `scripts/browser_smoke.py` against the live application.
