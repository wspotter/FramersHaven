#!/usr/bin/env python3
"""Capture repeatable help screenshots from a running demo workspace."""
from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "app" / "static" / "help" / "images"


def capture(page, output_dir: Path, filename: str) -> None:
    page.wait_for_timeout(350)
    page.screenshot(path=output_dir / filename, full_page=False)
    print(f"Captured {filename}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})

        page.goto(f"{args.url}/help/", wait_until="networkidle")
        capture(page, output_dir, "help-home-overview.png")

        page.goto(args.url, wait_until="networkidle")
        page.wait_for_selector("#mockupCanvas")
        capture(page, output_dir, "design-workspace-overview.png")

        page.get_by_role("button", name="Browse Mats").first.click()
        page.wait_for_selector("#catalogDrawer.visible .catalog-result")
        capture(page, output_dir, "design-material-drawer.png")
        page.keyboard.press("Escape")

        page.locator("[data-tab='gallery']").first.click()
        capture(page, output_dir, "gallery-intake-overview.png")
        capture(page, output_dir, "gallery-crop-controls.png")

        page.locator("[data-tab='orders']").first.click()
        page.wait_for_selector("#ordersList .job-row")
        capture(page, output_dir, "orders-quotes-table.png")
        page.locator("#ordersList .job-row").first.click()
        page.wait_for_selector("#orderInspector.open")
        page.locator("[data-inspector-tab='files']").click()
        capture(page, output_dir, "orders-files-handoff.png")
        page.keyboard.press("Escape")

        page.locator("[data-tab='customers']").first.click()
        capture(page, output_dir, "customer-management-overview.png")

        page.locator("[data-tab='admin']").first.click()
        page.locator("[data-admin-view='import']").click()
        capture(page, output_dir, "admin-catalog-import.png")
        page.locator("[data-admin-view='pricing']").click()
        capture(page, output_dir, "admin-pricing-services.png")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
