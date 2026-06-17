# Edition API Response Examples (Draft)

This file contains draft JSON examples for a future `GET /api/edition` endpoint. It does not implement the endpoint.

## Community Edition

```json
{
  "edition": "community",
  "label": "Community Edition",
  "description": "Free source-available snapshot for trying FramersHaven locally.",
  "limits": {
    "studio_profiles": 1,
    "active_catalog_items": 50,
    "saved_orders_quotes": 25,
    "local_catalog_package_imports": 1
  },
  "features": {
    "accounting_csv_export": false,
    "windows_paid_package": false
  },
  "unlimited": []
}
```

## Workstation Edition

```json
{
  "edition": "workstation",
  "label": "Workstation Edition",
  "description": "Planned paid Windows-ready ZIP/folder workflow for daily local use.",
  "limits": {
    "studio_profiles": "unlimited",
    "active_catalog_items": "unlimited",
    "saved_orders_quotes": "unlimited",
    "local_catalog_package_imports": "unlimited"
  },
  "features": {
    "accounting_csv_export": true,
    "windows_paid_package": true
  },
  "unlimited": [
    "studio_profiles",
    "active_catalog_items",
    "saved_orders_quotes",
    "local_catalog_package_imports",
    "accounting_csv_export",
    "windows_paid_package"
  ]
}
```

## Unknown Edition Fallback

If the configured edition value is not recognized, the endpoint should fall back to the Community response above.

## Contract Notes

- The response must not expose secrets, machine-specific identifiers, or filesystem paths.
- `limits` should reflect the active edition only.
- `unlimited` is a convenience list of fields where the active edition has no numeric cap.
- Unknown edition values fall back to `community`.
