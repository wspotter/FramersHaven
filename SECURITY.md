# Security Policy

## Supported Use

FramersHaven is designed for a trusted local workstation or private LAN and
opens directly into the studio workspace. It does not include internet-facing
authentication, TLS termination, or multi-tenant authorization. Anyone who can
reach the app can use its operator and admin tools. Do not expose the local
server directly to the public internet.

## Reporting

Please report suspected vulnerabilities privately to the repository owner. Do not include customer databases, uploaded artwork, credentials, or other sensitive files in a public issue.

## Local Data

The SQLite database, uploads, exports, backups, catalog previews, and vendor packages are excluded from version control. Operators are responsible for workstation access controls, encrypted backups where required, and applicable privacy obligations.
