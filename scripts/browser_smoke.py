#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys


def assert_moulding_orientation(page) -> None:
    result = page.evaluate(
        """() => {
            if (typeof createMouldingTexture !== 'function') {
                return { ok: false, reason: 'createMouldingTexture is not available' };
            }

            const preview = document.createElement('canvas');
            preview.width = 80;
            preview.height = 20;
            const source = preview.getContext('2d');
            source.fillStyle = '#050505';
            source.fillRect(0, 0, 80, 10);
            source.fillStyle = '#d02020';
            source.fillRect(0, 10, 80, 10);

            const item = {
                sku: 'orientation-check',
                name: 'orientation-check',
                preview_url: `orientation-check-${Date.now()}-strip.jpg`,
            };
            const profile = { facePx: 20, depthPx: 12, lipPx: 3 };
            const sample = (canvas, x, y) => {
                const data = canvas.getContext('2d').getImageData(x, y, 1, 1).data;
                return [data[0], data[1], data[2]];
            };
            const isDark = (pixel) => pixel[0] < 40 && pixel[1] < 40 && pixel[2] < 40;
            const isRed = (pixel) => pixel[0] > 120 && pixel[1] < 70 && pixel[2] < 70;

            const makeRail = (position) => {
                const horizontal = position === 'top' || position === 'bottom';
                const canvas = document.createElement('canvas');
                canvas.width = horizontal ? 80 : 20;
                canvas.height = horizontal ? 20 : 80;
                const ctx = canvas.getContext('2d');
                paintMouldingStripRail(ctx, position, 0, 0, canvas.width, canvas.height, preview);
                return canvas;
            };

            const top = makeRail('top');
            const bottom = makeRail('bottom');
            const left = makeRail('left');
            const right = makeRail('right');

            const samples = {
                topOuter: sample(top, 10, 2),
                topInner: sample(top, 10, 17),
                bottomInner: sample(bottom, 10, 2),
                bottomOuter: sample(bottom, 10, 17),
                leftOuter: sample(left, 2, 10),
                leftInner: sample(left, 17, 10),
                rightInner: sample(right, 2, 10),
                rightOuter: sample(right, 17, 10),
            };
            return {
                ok: isDark(samples.topOuter)
                    && isRed(samples.topInner)
                    && isRed(samples.bottomInner)
                    && isDark(samples.bottomOuter)
                    && isDark(samples.leftOuter)
                    && isRed(samples.leftInner)
                    && isRed(samples.rightInner)
                    && isDark(samples.rightOuter),
                samples,
            };
        }"""
    )
    if not result.get("ok"):
        raise AssertionError(f"Moulding texture orientation check failed: {result}")


def assert_orders_workspace(page) -> None:
    print("Orders smoke: open workspace", flush=True)
    page.locator("[data-tab='orders']").first.click()
    page.wait_for_selector("#ordersList .job-row", timeout=10_000)

    all_count = int(page.locator("#summaryAllCount").inner_text())
    if all_count < 1:
        raise AssertionError("Orders workspace did not load any jobs")

    created_header = page.locator("[data-order-sort='created_at']")
    initial_sort = created_header.get_attribute("aria-sort")
    created_header.click()
    toggled_sort = created_header.get_attribute("aria-sort")
    if initial_sort == toggled_sort or toggled_sort not in {"ascending", "descending"}:
        raise AssertionError(f"Created sort did not toggle: {initial_sort!r} -> {toggled_sort!r}")

    work_count = int(page.locator("#summaryWorkOrderCount").inner_text())
    if work_count:
        page.locator("[data-order-stage='work_order']").click()
        visible_statuses = page.locator("#ordersList .job-status-pill").all_inner_texts()
        if not visible_statuses or any("Work Order" not in status for status in visible_statuses):
            raise AssertionError(f"Work Order quick filter returned unexpected rows: {visible_statuses}")
        page.locator("[data-order-stage='']").click()

    row = page.locator("#ordersList .job-row").first
    row.click()
    page.wait_for_selector("#orderInspector.open", timeout=10_000)
    print("Orders smoke: preview quote PDF", flush=True)
    page.locator("[data-inspector-tab='files']").click()
    page.get_by_role("button", name="Quote PDF", exact=True).click()
    pdf_src = page.locator("#documentPdfPreview").get_attribute("src") or ""
    save_href = page.locator("#documentDownloadLink").get_attribute("href") or ""
    if "disposition=inline" not in pdf_src or "document=quote" not in pdf_src:
        raise AssertionError(f"Quote preview did not use the inline PDF URL: {pdf_src}")
    if "disposition=attachment" not in save_href:
        raise AssertionError(f"Save File did not use an attachment URL: {save_href}")

    print("Orders smoke: preview mockup JPG", flush=True)
    page.get_by_role("button", name="Mockup JPG", exact=True).click()
    page.wait_for_function("() => document.querySelector('#documentImagePreview')?.naturalWidth > 0")
    print("Orders smoke: prepare handoff", flush=True)
    page.get_by_role("button", name="Send", exact=True).click()
    attachment_note = page.locator("#handoffAttachmentNote").inner_text()
    if "Mockup JPG" not in attachment_note:
        raise AssertionError(f"Handoff did not retain the selected document: {attachment_note!r}")
    page.wait_for_function("() => document.querySelector('#handoffEmailBody')?.value.length > 20")
    if not page.locator("#handoffPhone").input_value():
        raise AssertionError("Handoff preview did not populate the customer phone")

    page.locator("#handoffEmail").fill("browser-smoke@example.com")
    if page.locator("#emailDraftButton").is_disabled():
        raise AssertionError("Email draft action stayed disabled after entering a valid email")
    page.locator("#handoffSubject").fill("Edited handoff subject")
    page.locator("button", has_text="Reset Draft").click()
    if page.locator("#handoffSubject").input_value() == "Edited handoff subject":
        raise AssertionError("Reset Draft did not restore the generated handoff subject")

    print("Orders smoke: close inspector", flush=True)
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.querySelector('#orderInspector')?.getAttribute('aria-hidden') === 'true'")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the critical framing quote flow in a real browser.")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Running app URL")
    parser.add_argument("--headed", action="store_true", help="Run with a visible browser window")
    parser.add_argument("--save", action="store_true", help="Also save a test quote into the local database")
    parser.add_argument(
        "--expected-edition",
        choices=("community",),
        help="Fail unless the running app uses this edition",
    )
    args = parser.parse_args()

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Run: ./venv/bin/pip install -r requirements-dev.txt", file=sys.stderr)
        return 2

    console_errors: list[str] = []
    step = "launch browser"
    with sync_playwright() as p:
        launch_options = {"headless": not args.headed}
        executable_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        if executable_path:
            launch_options["executable_path"] = executable_path
        browser = p.chromium.launch(**launch_options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        try:
            step = "load Design workspace"
            page.goto(args.url, wait_until="networkidle")
            if page.locator("input[name='username']").count():
                page.locator("input[name='username']").fill(os.environ.get("FRAMERSHAVEN_SMOKE_USERNAME", "admin"))
                page.locator("input[name='password']").fill(os.environ.get("FRAMERSHAVEN_SMOKE_PASSWORD", "admin"))
                page.get_by_role("button", name="Sign In").click()
                page.wait_for_url("**/", timeout=5000)
            page.wait_for_selector("#mockupCanvas", timeout=10_000)
            assert_moulding_orientation(page)
            step = "verify Admin edition status"
            page.locator("[data-tab='admin']").first.click()
            page.wait_for_selector("#adminEditionStatus", timeout=5000)
            page.wait_for_function(
                """() => {
                    const text = document.querySelector('#editionName')?.textContent || '';
                    return text.includes('Community Edition');
                }""",
                timeout=5000,
            )
            edition_text = page.locator("#editionName").inner_text()
            if "Community Edition" in edition_text:
                active_edition = "community"
            else:
                raise AssertionError(f"Edition status did not load properly: {edition_text}")
            if args.expected_edition and active_edition != args.expected_edition:
                raise AssertionError(
                    f"Expected {args.expected_edition} edition, but the app reported {active_edition}"
                )
            catalog_usage = page.locator("#editionCatalogUsage").inner_text()
            orders_usage = page.locator("#editionOrdersUsage").inner_text()
            imports_usage = page.locator("#editionImportsUsage").inner_text()
            for label, usage in (
                ("Catalog", catalog_usage),
                ("Orders/quotes", orders_usage),
                ("Package imports", imports_usage),
            ):
                if "/" not in usage:
                    raise AssertionError(f"{label} usage not displayed: {usage}")
            page.locator("[data-admin-view='accounting']").click()
            accounting_message = page.locator("#accountingExportMessage")
            accounting_button = page.locator("#accountingExportButton")
            if accounting_button.is_hidden():
                raise AssertionError("Community accounting export button is hidden")
            if "local ZIP" not in accounting_message.inner_text():
                raise AssertionError("Community accounting export message is missing")
            with page.expect_download(timeout=10_000) as download_info:
                accounting_button.click()
            if download_info.value.suggested_filename != "accounting_csv_export.zip":
                raise AssertionError(
                    f"Unexpected accounting download name: {download_info.value.suggested_filename}"
                )
            page.locator("[data-tab='design']").first.click()
            page.wait_for_selector("#tab-design.active", timeout=5000)
            if page.locator("#customerSelect").count():
                raise AssertionError("Legacy customer dropdown is still present in Design")
            first_customer = page.evaluate(
                "fetch('/api/customers').then(response => response.json()).then(data => data.customers[0] || null)"
            )
            if first_customer:
                page.locator("#designCustomerSearch").fill(first_customer["name"])
                page.wait_for_function(
                    "() => document.querySelectorAll('#designCustomerResults .customer-picker-result').length > 0"
                )
                page.locator("#designCustomerResults .customer-picker-result").first.click()
                if page.locator("#customerName").input_value() != first_customer["name"]:
                    raise AssertionError("Customer search did not populate the quote identity fields")
            page.locator("button", has_text="New customer").click()
            if page.locator("#inlineCustomerCreate").is_hidden():
                raise AssertionError("Inline customer creation did not open")
            page.locator("#inlineCustomerCreate button", has_text="Cancel").click()
            if page.locator("#inlineCustomerCreate").is_visible():
                raise AssertionError("Inline customer creation did not close")
            if "option-row" not in (page.locator("#glazingType").locator("..").get_attribute("class") or ""):
                raise AssertionError("Glazing is not rendered with the quote service rows")
            page.locator("#useSecondMat").check()
            page.locator("#useThirdMat").check()
            page.wait_for_function(
                "() => !document.querySelector('#secondMatCard')?.classList.contains('hidden')"
                " && !document.querySelector('#thirdMatCard')?.classList.contains('hidden')"
            )
            mat_layout = page.locator(".material-slot-grid").evaluate(
                """grid => ({
                    cards: [...grid.querySelectorAll('.material-slot:not(.hidden)')].map(card => card.getBoundingClientRect().width),
                    fields: [...grid.querySelectorAll('input')].map(field => field.getBoundingClientRect().width),
                })"""
            )
            if min(mat_layout["cards"], default=0) < 170:
                raise AssertionError(f"Mat cards are too narrow to read: {mat_layout['cards']}")
            if min(mat_layout["fields"], default=0) < 100:
                raise AssertionError(f"Mat fields are too narrow to read: {mat_layout['fields']}")
            page.locator("#useThirdMat").uncheck()
            page.locator("#useSecondMat").uncheck()
            before_canvas = page.locator("#mockupCanvas").evaluate("node => node.toDataURL()")

            step = "select a mat"
            page.locator("button", has_text="Browse Mats").first.click()
            page.wait_for_selector("#catalogDrawer.visible .catalog-result", timeout=10_000)
            page.locator("#catalogDrawer .catalog-result").first.click()
            top_mat = page.locator("#selectionTopMat").input_value()
            if top_mat == "None":
                raise AssertionError("Top mat was not selected")

            step = "select a moulding"
            page.locator("button", has_text="Browse Frame").first.click()
            page.wait_for_selector("#catalogDrawer.visible .catalog-result", timeout=10_000)
            priced_mouldings = page.locator("#catalogDrawer .catalog-result:not(.sample)")
            if priced_mouldings.count():
                priced_mouldings.first.click()
            else:
                page.locator("#catalogDrawer .catalog-result").first.click()
            moulding = page.locator("#selectionMoulding").input_value()
            if moulding == "None":
                raise AssertionError("Moulding was not selected")

            after_canvas = page.locator("#mockupCanvas").evaluate("node => node.toDataURL()")
            if before_canvas == after_canvas:
                raise AssertionError("Mockup canvas did not change after material selection")

            step = "calculate quote"
            page.locator("button", has_text="Calculate Quote").click()
            page.wait_for_function(
                "() => document.querySelector('#quoteTotal')?.textContent !== '$0.00'",
                timeout=10_000,
            )
            total = page.locator("#quoteTotal").inner_text()

            step = "verify Orders workspace"
            assert_orders_workspace(page)
            page.locator("[data-tab='design']").first.click()

            saved = ""
            if args.save:
                page.locator("#customerName").fill("Browser Smoke Test")
                page.locator("#customerContact").fill("555-010-0199")
                page.locator("button", has_text="Save Quote").click()
                page.wait_for_function(
                    "() => document.querySelector('#notice')?.textContent.includes('Quote Q')",
                    timeout=10_000,
                )
                notice_text = page.locator("#notice").inner_text()
                # notice text is like "Quote Q00001 saved successfully."
                quote_num = notice_text.split("Quote ")[1].split()[0]
                
                # Switch to orders tab and verify
                page.locator("[data-tab='orders']").first.click()
                page.wait_for_selector(f"#ordersList:has-text('{quote_num}')", timeout=10_000)
                page.locator("#orderPrimaryAction").wait_for(timeout=10_000)
                primary_label = page.locator("#orderPrimaryAction").inner_text()
                if "Approve" not in primary_label:
                    raise AssertionError(f"Expected Approve primary action, saw {primary_label!r}")
                page.locator("#orderPrimaryAction").click()
                page.wait_for_function(
                    "() => document.querySelector('#orderStatusLabel')?.textContent.includes('Work Order')",
                    timeout=10_000,
                )
                
                saved = f" and saved quote {quote_num} (verified and approved in Jobs split view)"

            if console_errors:
                raise AssertionError("Console errors during smoke test: " + " | ".join(console_errors))

            print(f"Browser smoke passed: top mat {top_mat}, moulding {moulding}, total {total}{saved}")
            return 0
        except PlaywrightTimeoutError as exc:
            print(f"Browser smoke timed out during {step}: {exc}", file=sys.stderr)
            return 1
        except AssertionError as exc:
            print(f"Browser smoke failed: {exc}", file=sys.stderr)
            return 1
        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
