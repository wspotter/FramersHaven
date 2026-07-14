import base64
import io
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from html import unescape
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app import db
from app import main as main_module
from app.main import app


def run_frontend_behavior(body: str) -> dict:
    script_path = Path(__file__).parents[1] / "app" / "static" / "app.js"
    harness = r"""
const fs = require('fs');
const nodes = {};
function input(value = '') {
  return { value: String(value), type: 'text', focus() { this.focused = true; }, addEventListener() {} };
}
function select(value = '') {
  const node = input(value);
  node.options = [];
  node.appendChild = (option) => node.options.push(option);
  Object.defineProperty(node, 'innerHTML', { set() { node.options = []; } });
  return node;
}
global.window = { addEventListener() {}, setTimeout, clearTimeout, localStorage: { getItem() { return null; } } };
global.document = {
  getElementById(id) { return nodes[id] || null; },
  createElement(tag) { return tag === 'option' ? new Option('', '') : {}; },
  querySelectorAll() { return []; },
  querySelector() { return null; },
};
global.Option = class { constructor(text, value) { this.textContent = text; this.value = value; } };
class TestFormData {
  constructor() { this.entries = []; }
  append(key, value) { this.entries.push([key, String(value)]); }
  get(key) { return this.entries.find(([name]) => name === key)?.[1]; }
  has(key) { return this.entries.some(([name]) => name === key); }
}
eval(fs.readFileSync(process.argv[1], 'utf8') + '\n' + process.argv[2]);
"""
    result = subprocess.run(
        ["node", "-e", harness, str(script_path), body],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


class ApiTests(unittest.TestCase):
    def test_admin_services_panel_has_printing_option_editor(self):
        home = self.client.get("/")
        self.assertIn('id="printingOptionsAdmin"', home.text)
        self.assertIn("Add Print Size", home.text)
        self.assertNotIn('id="servicePrintingLabel"', home.text)

    def test_frontend_contains_printing_option_admin_actions(self):
        script = self.client.get("/static/app.js").text
        self.assertIn("function renderPrintingOptionAdmin()", script)
        self.assertIn("async function addPrintingOption()", script)
        self.assertIn("async function savePrintingOption(id)", script)

    def test_frontend_printing_admin_renders_escaped_numeric_rows_and_filters_inactive_quotes(self):
        result = run_frontend_behavior(r"""
nodes.printingOptionsAdmin = { innerHTML: '' };
nodes.optionPrinting = select('');
printingOptionsCache = [
  { id: 7, label: '<img src=x onerror="bad">', unit_price: 12.5, active: 1, sort_order: 10 },
  { id: 8, label: 'Inactive', unit_price: 9, active: 0, sort_order: 20 },
  { id: '9);bad()', label: 'Invalid id', unit_price: 1, active: 1, sort_order: 30 },
];
renderPrintingOptionAdmin();
populatePrintingSelect();
console.log(JSON.stringify({
  html: nodes.printingOptionsAdmin.innerHTML,
  quoteValues: nodes.optionPrinting.options.map((option) => option.value),
  quoteTexts: nodes.optionPrinting.options.map((option) => option.textContent),
}));
""")
        self.assertIn('&lt;img src=x onerror=&quot;bad&quot;&gt;', result["html"])
        self.assertIn('savePrintingOption(7)', result["html"])
        self.assertNotIn('bad()', result["html"])
        self.assertEqual(result["quoteValues"], ["7", "custom"])
        self.assertEqual(result["quoteTexts"][0], '<img src=x onerror="bad"> · $12.50')

    def test_frontend_printing_mutations_are_serialized_and_restore_failed_row(self):
        result = run_frontend_behavior(r"""
global.FormData = TestFormData;
nodes.notice = { textContent: '', className: '' };
nodes.printingOptionsAdmin = { innerHTML: '' };
nodes.optionPrinting = select('');
const saveButton = { disabled: false };
const fields = {
  label: { value: 'First edit' },
  'unit-price': { value: '12.75' },
  active: { checked: false },
  'sort-order': { value: '35' },
};
const row = {
  querySelector(selector) {
    if (selector === 'button') return saveButton;
    return fields[selector.match(/data-field="([^"]+)/)?.[1]] || null;
  },
};
document.querySelector = (selector) => selector === '[data-printing-option-id="7"]' ? row : null;
const calls = [];
let resolveFirst;
fetchJson = (url, options) => {
  calls.push({ url, body: Object.fromEntries(options.body.entries) });
  if (calls.length === 1) return new Promise((resolve) => { resolveFirst = resolve; });
  return Promise.reject(new Error('newer save rejected'));
};
printingOptionsCache = [{ id: 7, label: 'Original', unit_price: 1, active: 1, sort_order: 1 }];
const first = savePrintingOption(7);
const pendingAfterFirst = saveButton.disabled;
fields.label.value = 'Second edit';
fields['unit-price'].value = '22.50';
fields.active.checked = true;
fields['sort-order'].value = '45';
const second = savePrintingOption(7);
Promise.resolve().then(() => {
  const callsBeforeFirstSettles = calls.length;
  resolveFirst({ printing_options: [{ id: 7, label: 'First edit', unit_price: 12.75, active: 0, sort_order: 35 }] });
  return Promise.all([first, second]).then(() => console.log(JSON.stringify({
  pendingAfterFirst,
  callsBeforeFirstSettles,
  calls,
  cacheLabel: printingOptionsCache[0].label,
  rowLabel: fields.label.value,
  disabledAfter: saveButton.disabled,
  notice: nodes.notice.textContent,
  tone: nodes.notice.className,
  })));
});
""")
        self.assertTrue(result["pendingAfterFirst"])
        self.assertEqual(result["callsBeforeFirstSettles"], 1)
        self.assertEqual(result["calls"][0]["body"], {
            "label": "First edit", "unit_price": "12.75", "active": "0", "sort_order": "35",
        })
        self.assertEqual(result["calls"][1]["body"], {
            "label": "Second edit", "unit_price": "22.50", "active": "1", "sort_order": "45",
        })
        self.assertEqual(result["cacheLabel"], "First edit")
        self.assertEqual(result["rowLabel"], "Second edit")
        self.assertFalse(result["disabledAfter"])
        self.assertEqual(result["notice"], "newer save rejected")
        self.assertIn("error", result["tone"])

    def test_frontend_add_printing_option_refreshes_admin_cache_and_quote_dropdown(self):
        result = run_frontend_behavior(r"""
global.FormData = TestFormData;
nodes.notice = { textContent: '', className: '' };
nodes.printingOptionsAdmin = { innerHTML: '' };
nodes.optionPrinting = select('');
nodes.addPrintingOptionButton = { disabled: false };
let request;
fetchJson = async (url, options) => {
  request = { url, body: Object.fromEntries(options.body.entries) };
  return { printing_options: [
    { id: 11, label: 'Existing', unit_price: 5, active: 0, sort_order: 20 },
    { id: 12, label: 'New Print Size', unit_price: 0, active: 1, sort_order: 30 },
  ] };
};
printingOptionsCache = [{ id: 11, label: 'Existing', unit_price: 5, active: 0, sort_order: 20 }];
const mutation = addPrintingOption();
const pending = nodes.addPrintingOptionButton.disabled;
mutation.then(() => console.log(JSON.stringify({
  request,
  pending,
  disabledAfter: nodes.addPrintingOptionButton.disabled,
  cacheIds: printingOptionsCache.map((row) => row.id),
  adminHtml: nodes.printingOptionsAdmin.innerHTML,
  quoteValues: nodes.optionPrinting.options.map((option) => option.value),
})));
""")
        self.assertEqual(result["request"], {
            "url": "/api/printing-options",
            "body": {"label": "New Print Size", "unit_price": "0", "active": "1", "sort_order": "30"},
        })
        self.assertTrue(result["pending"])
        self.assertFalse(result["disabledAfter"])
        self.assertEqual(result["cacheIds"], [11, 12])
        self.assertIn("New Print Size", result["adminHtml"])
        self.assertEqual(result["quoteValues"], ["12", "custom"])

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db.DB_PATH = Path(self.tempdir.name) / "test_studio.db"
        main_module.BACKUP_DIR = Path(self.tempdir.name) / "backups"
        main_module.BACKUP_DIR.mkdir(exist_ok=True)
        main_module.PREVIEW_DIR = Path(self.tempdir.name) / "catalog_previews"
        main_module.PREVIEW_DIR.mkdir(exist_ok=True)
        main_module.PFD_DIR = Path(self.tempdir.name) / "pfd"
        main_module.PFD_DIR.mkdir(exist_ok=True)
        self.original_upload_dir = main_module.UPLOAD_DIR
        main_module.UPLOAD_DIR = Path(self.tempdir.name) / "uploads"
        main_module.UPLOAD_DIR.mkdir(exist_ok=True)
        main_module._catalog_preview_basename_index.cache_clear()
        db.init_db()
        self.client = TestClient(app)
        main_module.init_admin_tables()
        login = self.client.post(
            "/admin/login",
            data={"email": "admin", "password": "admin"},
            follow_redirects=False,
        )
        self.assertEqual(login.status_code, 303)

    def tearDown(self):
        self.client.close()
        main_module.UPLOAD_DIR = self.original_upload_dir
        main_module._catalog_preview_basename_index.cache_clear()
        self.tempdir.cleanup()

    def test_quote_markup_exposes_discount_column_and_printing_option_ids(self):
        home = self.client.get("/")
        self.assertIn("Discount %", home.text)
        for field_id in (
            "discountMoulding", "discountTopMat", "discountSecondMat", "discountThirdMat",
            "discountGlazing", "discountLabor", "discountBacking", "discountMounting",
            "discountFrameMounting", "discountPrinting", "discountVarious",
            "discountAssembly", "discountRoyalties", "discountCustom1", "discountCustom2",
        ):
            self.assertIn(f'id="{field_id}"', home.text)
        self.assertIn('id="optionPrinting"', home.text)

    def test_frontend_global_discount_populates_line_fields_without_stacking(self):
        script = self.client.get("/static/app.js").text
        self.assertIn("function populateLineDiscounts(value)", script)
        self.assertIn("fd.append('printing_option_id'", script)
        self.assertIn("fd.append(`${key}_discount_pct`", script)
        self.assertNotIn("fd.append(`${key}_discount_pct`, '0')", script)

    def test_frontend_discount_fanout_keeps_individual_overrides_independent(self):
        result = run_frontend_behavior(r"""
nodes.globalDiscount = input('25');
Object.values(LINE_DISCOUNT_FIELDS).forEach((id) => { nodes[id] = input('0'); });
populateLineDiscounts(nodes.globalDiscount.value);
nodes.discountLabor.value = '10';
console.log(JSON.stringify({
  global: nodes.globalDiscount.value,
  labor: nodes.discountLabor.value,
  moulding: nodes.discountMoulding.value,
  other: nodes.otherLineDiscount.value,
  otherHistoryEntries: DESIGN_HISTORY_FIELD_IDS.filter((id) => id === 'otherLineDiscount').length,
}));
""")
        self.assertEqual(result, {
            "global": "25", "labor": "10", "moulding": "25", "other": "25",
            "otherHistoryEntries": 1,
        })

    def test_frontend_quote_form_maps_discounts_and_printing_selection_behavior(self):
        result = run_frontend_behavior(r"""
Object.entries(LINE_DISCOUNT_FIELDS).forEach(([key, id]) => { nodes[id] = input(key === 'mat' ? '11' : '20'); });
OPTION_SELECTS.forEach(({ selectId, countId }) => { nodes[selectId] = select(''); nodes[countId] = input('1'); });
nodes.optionPrinting = select('41');
nodes.countPrinting = input('3');
nodes.otherLineLabel = input(''); nodes.otherLineAmount = input('0');
nodes.otherLine2Label = input(''); nodes.otherLine2Amount = input('0');
let fd = new TestFormData();
appendQuoteOptionFields(fd);
const numeric = { top: fd.get('top_mat_discount_pct'), wrong: fd.has('mat_discount_pct'),
  printingId: fd.get('printing_option_id'), printingCount: fd.get('printing_count'),
  printingDiscount: fd.get('printing_discount_pct') };
nodes.optionPrinting.value = 'custom';
handlePrintingSelectionChange('custom');
fd = new TestFormData();
appendQuoteOptionFields(fd);
console.log(JSON.stringify({ numeric, custom: { hasId: fd.has('printing_option_id'),
  label: nodes.otherLineLabel.value, focused: Boolean(nodes.otherLineLabel.focused) } }));
""")
        self.assertEqual(result["numeric"], {
            "top": "11", "wrong": False, "printingId": "41",
            "printingCount": "3", "printingDiscount": "20",
        })
        self.assertEqual(result["custom"], {"hasId": False, "label": "Printing ", "focused": True})

    def test_frontend_unavailable_and_legacy_printing_restore_as_safe_other_lines(self):
        result = run_frontend_behavior(r"""
nodes.optionPrinting = select(''); nodes.countPrinting = input('1'); nodes.discountPrinting = input('0');
nodes.otherLineLabel = input(''); nodes.otherLineAmount = input('0'); nodes.otherLineDiscount = input('0');
nodes.otherLine2Label = input(''); nodes.otherLine2Amount = input('0'); nodes.otherLine2Discount = input('0');
printingOptionsCache = [];
populatePrintingSelect();
restorePrintingSelection({ id: 9, label: 'Retired Print', unit_price: 12.5, count: 3, discount_pct: 20 });
const managedVisible = { value: nodes.optionPrinting.value, text: nodes.optionPrinting.options.at(-1).textContent,
  count: nodes.countPrinting.value, discount: nodes.discountPrinting.value };
let fd = new TestFormData();
appendQuoteOptionFields(fd);
const managedFallback = { value: nodes.optionPrinting.value, hasId: fd.has('printing_option_id'), label: fd.get('other_label'),
  amount: fd.get('other_amount'), discount: fd.get('other_discount_pct') };

nodes.otherLineLabel.value = ''; nodes.otherLineAmount.value = '0'; nodes.otherLineDiscount.value = '0';
restorePrintingSelection({ service: { label: 'Legacy Printing', cost: 8, markup: 1.5 }, count: 2,
  variable: 2, discount_pct: 25 });
fd = new TestFormData();
appendQuoteOptionFields(fd);
console.log(JSON.stringify({ managedVisible, managedFallback, legacyFallback: {
  value: nodes.optionPrinting.value, hasId: fd.has('printing_option_id'), label: fd.get('other_label'),
  amount: fd.get('other_amount'), discount: fd.get('other_discount_pct') } }));
""")
        self.assertEqual(result["managedVisible"], {
            "value": "snapshot:9", "text": "Retired Print (unavailable) · $12.50",
            "count": "3", "discount": "20",
        })
        self.assertEqual(result["managedFallback"], {
            "value": "custom", "hasId": False, "label": "Retired Print", "amount": "37.5", "discount": "20",
        })
        self.assertEqual(result["legacyFallback"], {
            "value": "custom", "hasId": False, "label": "Legacy Printing",
            "amount": "24", "discount": "25",
        })

    def test_frontend_printing_snapshot_materializes_only_once_across_recalculation(self):
        result = run_frontend_behavior(r"""
Object.values(LINE_DISCOUNT_FIELDS).forEach((id) => { nodes[id] = input('0'); });
OPTION_SELECTS.forEach(({ selectId, countId }) => { nodes[selectId] = select(''); nodes[countId] = input('1'); });
nodes.optionPrinting = select(''); nodes.countPrinting = input('2');
nodes.otherLineLabel = input(''); nodes.otherLineAmount = input('0'); nodes.otherLineDiscount = input('0');
nodes.otherLine2Label = input(''); nodes.otherLine2Amount = input('0'); nodes.otherLine2Discount = input('0');
printingOptionsCache = [];
restorePrintingSelection({ id: 19, label: 'Archived Print', unit_price: 15, count: 2, discount_pct: 10 });
const first = new TestFormData();
const firstOk = appendQuoteOptionFields(first);
const second = new TestFormData();
const secondOk = appendQuoteOptionFields(second);
console.log(JSON.stringify({ firstOk, secondOk, selection: nodes.optionPrinting.value,
  firstLabels: first.entries.filter(([key]) => key === 'other_label' || key === 'other2_label').map(([, value]) => value),
  secondLabels: second.entries.filter(([key]) => key === 'other_label' || key === 'other2_label').map(([, value]) => value),
  other1: [nodes.otherLineLabel.value, nodes.otherLineAmount.value, nodes.otherLineDiscount.value],
  other2: [nodes.otherLine2Label.value, nodes.otherLine2Amount.value, nodes.otherLine2Discount.value] }));
""")
        self.assertEqual(result, {
            "firstOk": True, "secondOk": True, "selection": "custom",
            "firstLabels": ["Archived Print", ""], "secondLabels": ["Archived Print", ""],
            "other1": ["Archived Print", "30", "10"], "other2": ["", "0", "0"],
        })

    def test_frontend_blocked_printing_snapshot_shows_error_without_mutating_other_rows(self):
        result = run_frontend_behavior(r"""
Object.values(LINE_DISCOUNT_FIELDS).forEach((id) => { nodes[id] = input('0'); });
OPTION_SELECTS.forEach(({ selectId, countId }) => { nodes[selectId] = select(''); nodes[countId] = input('1'); });
nodes.optionPrinting = select(''); nodes.countPrinting = input('1');
nodes.otherLineLabel = input('Existing A'); nodes.otherLineAmount = input('8'); nodes.otherLineDiscount = input('5');
nodes.otherLine2Label = input('Existing B'); nodes.otherLine2Amount = input('9'); nodes.otherLine2Discount = input('6');
nodes.notice = { textContent: '', className: '' };
printingOptionsCache = [];
restorePrintingSelection({ id: 20, label: 'Blocked Print', unit_price: 12, count: 1, discount_pct: 15 });
const before = [nodes.otherLineLabel.value, nodes.otherLineAmount.value, nodes.otherLineDiscount.value,
  nodes.otherLine2Label.value, nodes.otherLine2Amount.value, nodes.otherLine2Discount.value];
const fd = new TestFormData();
const ok = appendQuoteOptionFields(fd);
const after = [nodes.otherLineLabel.value, nodes.otherLineAmount.value, nodes.otherLineDiscount.value,
  nodes.otherLine2Label.value, nodes.otherLine2Amount.value, nodes.otherLine2Discount.value];
console.log(JSON.stringify({ ok, before, after, notice: nodes.notice.textContent, tone: nodes.notice.className,
  selection: nodes.optionPrinting.value, submittedId: fd.has('printing_option_id') }));
""")
        self.assertEqual(result, {
            "ok": False,
            "before": ["Existing A", "8", "5", "Existing B", "9", "6"],
            "after": ["Existing A", "8", "5", "Existing B", "9", "6"],
            "notice": "Both Other rows are in use. Clear one before recalculating this unavailable printing snapshot.",
            "tone": "notice visible error", "selection": "snapshot:20", "submittedId": False,
        })

    def test_printing_options_migrate_once_from_existing_service(self):
        conn = db.get_connection()
        conn.execute(
            "UPDATE service_options SET label = ?, price = ?, pricing_method = 'cost_markup' WHERE key = 'printing'",
            ("Print 5x7", 8.50),
        )
        conn.execute("DELETE FROM printing_options")
        conn.commit()
        conn.close()

        main_module._seed_printing_options_from_legacy_service()
        main_module._seed_printing_options_from_legacy_service()

        rows = self.client.get("/api/printing-options").json()["printing_options"]
        self.assertEqual([(row["label"], row["unit_price"]) for row in rows], [("Print 5x7", 8.50)])

    def test_admin_can_create_update_and_deactivate_printing_options(self):
        created = self.client.post(
            "/api/printing-options",
            data={"label": "  Print 8x10  ", "unit_price": "14.00", "active": "1", "sort_order": "20"},
        )
        self.assertEqual(created.status_code, 200)
        created_body = created.json()
        option_id = created_body["printing_option"]["id"]
        self.assertEqual(created_body["printing_option"]["label"], "Print 8x10")
        self.assertEqual(created_body["printing_option"]["sort_order"], 20)
        self.assertEqual([row["id"] for row in created_body["printing_options"]], [option_id])

        updated = self.client.post(
            f"/api/printing-options/{option_id}",
            data={"label": "Print 8 x 10", "unit_price": "15.00", "active": "0", "sort_order": "10"},
        )
        self.assertEqual(updated.status_code, 200)
        updated_body = updated.json()
        self.assertEqual(updated_body["printing_option"]["unit_price"], 15.0)
        self.assertEqual(updated_body["printing_option"]["active"], 0)
        self.assertEqual(updated_body["printing_option"]["sort_order"], 10)
        self.assertEqual(updated_body["printing_options"][0]["id"], option_id)

        missing = self.client.post(
            "/api/printing-options/999999",
            data={"label": "Missing", "unit_price": "10", "active": "1", "sort_order": "10"},
        )
        self.assertEqual(missing.status_code, 400)
        self.assertIn("not found", missing.json()["detail"])

    def test_printing_option_validation_rejects_blank_label_and_large_price(self):
        blank = self.client.post(
            "/api/printing-options",
            data={"label": "", "unit_price": "10", "active": "1", "sort_order": "10"},
        )
        self.assertEqual(blank.status_code, 400)
        self.assertIn("label is required", blank.json()["detail"])

        expensive = self.client.post(
            "/api/printing-options",
            data={"label": "Huge Print", "unit_price": "1000", "active": "1", "sort_order": "10"},
        )
        self.assertEqual(expensive.status_code, 400)
        self.assertIn("999.99 or less", expensive.json()["detail"])

    def test_printing_option_validation_rejects_non_finite_prices_on_create_and_update(self):
        for raw_price in ("nan", "inf", "-inf"):
            with self.subTest(operation="create", unit_price=raw_price):
                response = self.client.post(
                    "/api/printing-options",
                    data={"label": "Invalid Print", "unit_price": raw_price, "active": "1", "sort_order": "10"},
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("finite number", response.json()["detail"])

        created = self.client.post(
            "/api/printing-options",
            data={"label": "Valid Print", "unit_price": "10", "active": "1", "sort_order": "10"},
        )
        self.assertEqual(created.status_code, 200)
        option_id = created.json()["printing_option"]["id"]

        for raw_price in ("nan", "inf", "-inf"):
            with self.subTest(operation="update", unit_price=raw_price):
                response = self.client.post(
                    f"/api/printing-options/{option_id}",
                    data={"label": "Still Valid", "unit_price": raw_price, "active": "1", "sort_order": "10"},
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("finite number", response.json()["detail"])

    def test_help_site_routes_pages_and_shared_assets(self):
        redirect = self.client.get("/help", follow_redirects=False)
        self.assertEqual(redirect.status_code, 307)
        self.assertEqual(redirect.headers["location"], "http://testserver/help/")

        pages = {
            "/help/": "Printery Framing Studio Operator Guide",
            "/help/design-workspace.html": "Design Workspace",
            "/help/gallery-intake.html": "Gallery & Intake",
            "/help/orders-quotes.html": "Orders & Quotes",
            "/help/customer-management.html": "Customer Management",
            "/help/admin-pricing.html": "Admin & Pricing",
        }
        for path, heading in pages.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(heading, unescape(response.text))
                self.assertIn('href="/"', response.text)
                self.assertIn('href="/help/design-workspace.html"', response.text)

        design = self.client.get("/help/design-workspace.html")
        self.assertIn('src="images/design-workspace-overview.png"', design.text)
        self.assertIn('alt="Design workspace with the live framing mockup and compact quote worksheet"', design.text)

        stylesheet = self.client.get("/help/css/help-style.css")
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("text/css", stylesheet.headers["content-type"])
        self.assertIn("--printery-pink", stylesheet.text)

    def test_studio_profile_updates_branding_used_by_the_app_and_handoffs(self):
        saved = self.client.post(
            "/api/studio-profile",
            data={
                "business_name": "Mountain Frame House",
                "contact_name": "Ada Frame",
                "phone": "606-555-0142",
                "email": "ada@example.com",
                "street": "10 Main Street",
                "city": "Prestonsburg",
                "state": "KY",
                "postal_code": "41653",
            },
        )
        self.assertEqual(saved.status_code, 200)
        profile = saved.json()["profile"]
        self.assertEqual(profile["business_name"], "Mountain Frame House")
        self.assertEqual(profile["address"], "10 Main Street, Prestonsburg, KY 41653")

        fetched = self.client.get("/api/studio-profile")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["profile"]["email"], "ada@example.com")

        home = self.client.get("/")
        self.assertIn("Mountain Frame House", home.text)
        self.assertIn("Ada Frame", home.text)

        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Profile Handoff",
                "customer_contact": "606-555-0180",
                "payload_json": json.dumps({"subtotal": 10, "tax": 0.6, "total": 10.6}),
                "subtotal": "10",
                "tax": "0.6",
                "total": "10.6",
            },
        )
        handoff = self.client.get(f"/api/orders/{created.json()['order_id']}/handoff")
        self.assertIn("Mountain Frame House quote", handoff.json()["email_subject"])
        self.assertIn("Ada Frame\n606-555-0142\nada@example.com", handoff.json()["email_body"])

    def test_design_launcher_is_compact_and_collapsed_by_default(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn('id="designLauncherToggle"', home.text)
        self.assertIn('aria-expanded="false"', home.text)
        self.assertIn('>+ New Design</button>', home.text)
        self.assertIn('id="designHomePanel" class="design-launcher-panel" hidden', home.text)
        self.assertNotIn('id="themeStatus"', home.text)

    def test_frontend_assets_are_not_stale_cached_during_local_updates(self):
        script = self.client.get("/static/app.js")
        self.assertEqual(script.status_code, 200)
        self.assertEqual(script.headers.get("cache-control"), "no-store")

        home = self.client.get("/")
        self.assertIn('/static/app.js?v=', home.text)

    def test_studio_opens_locally_without_login(self):
        self.client.get("/admin/logout", follow_redirects=False)

        home = self.client.get("/", follow_redirects=False)
        self.assertEqual(home.status_code, 200)

        api = self.client.get("/api/config")
        self.assertEqual(api.status_code, 200)

        me = self.client.get("/admin/me")
        self.assertEqual(me.status_code, 200)
        self.assertIn(me.json()["role"], ["admin", "owner"])

        login_page = self.client.get("/admin/login", follow_redirects=False)
        self.assertEqual(login_page.status_code, 303)
        self.assertEqual(login_page.headers["location"], "/")

        login = self.client.post(
            "/admin/login",
            data={"email": "admin", "password": "admin", "next": "/"},
            follow_redirects=False,
        )
        self.assertEqual(login.status_code, 303)
        self.assertEqual(login.headers["location"], "/")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_studio_logo_upload_validates_format_size_and_dimensions(self):
        valid = io.BytesIO()
        Image.new("RGBA", (600, 200), (20, 80, 90, 0)).save(valid, format="PNG")
        uploaded = self.client.post(
            "/api/studio-profile/logo",
            files={"file": ("studio-logo.png", valid.getvalue(), "image/png")},
        )
        self.assertEqual(uploaded.status_code, 200)
        logo_url = uploaded.json()["profile"]["logo_url"]
        self.assertTrue(logo_url.startswith("/api/studio-profile/logo/file"))
        self.assertEqual(self.client.get(logo_url).status_code, 200)

        wrong_format = io.BytesIO()
        Image.new("RGB", (600, 200), "white").save(wrong_format, format="JPEG")
        rejected_type = self.client.post(
            "/api/studio-profile/logo",
            files={"file": ("studio-logo.jpg", wrong_format.getvalue(), "image/jpeg")},
        )
        self.assertEqual(rejected_type.status_code, 400)
        self.assertIn("PNG or WebP", rejected_type.json()["detail"])

        too_small = io.BytesIO()
        Image.new("RGBA", (200, 80), (0, 0, 0, 0)).save(too_small, format="PNG")
        rejected_size = self.client.post(
            "/api/studio-profile/logo",
            files={"file": ("small.png", too_small.getvalue(), "image/png")},
        )
        self.assertEqual(rejected_size.status_code, 400)
        self.assertIn("300-1600 px wide", rejected_size.json()["detail"])

        bad_ratio = io.BytesIO()
        Image.new("RGBA", (600, 600), (0, 0, 0, 0)).save(bad_ratio, format="PNG")
        rejected_ratio = self.client.post(
            "/api/studio-profile/logo",
            files={"file": ("square.png", bad_ratio.getvalue(), "image/png")},
        )
        self.assertEqual(rejected_ratio.status_code, 400)
        self.assertIn("2:1 and 5:1", rejected_ratio.json()["detail"])

        removed = self.client.delete("/api/studio-profile/logo")
        self.assertEqual(removed.status_code, 200)
        self.assertIsNone(removed.json()["profile"]["logo_url"])

    def test_catalog_import_upsert_and_skip(self):
        csv1 = "sku,name,category,cost,width_in\nA1,Frame Alpha,moulding,10,1.5\nA2,Mat White,mat,3,0\nA1,Glass Clear,glazing,6,0\n"
        r1 = self.client.post(
            "/api/catalog/import",
            files={"file": ("catalog.csv", csv1, "text/csv")},
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["inserted"], 3)

        csv2 = "sku,name,category,cost,width_in\nA1,Frame Alpha Updated,moulding,12,1.5\nBAD,,mat,-1,0\n"
        r2 = self.client.post(
            "/api/catalog/import",
            files={"file": ("catalog.csv", csv2, "text/csv")},
        )
        self.assertEqual(r2.status_code, 200)
        payload = r2.json()
        self.assertEqual(payload["updated"], 1)
        self.assertEqual(payload["skipped"], 1)

        search = self.client.get("/api/catalog/search", params={"q": "Updated"})
        self.assertEqual(search.status_code, 200)
        items = search.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["sku"], "A1")
        self.assertEqual(items[0]["cost"], 12.0)

    def test_catalog_rejects_service_categories(self):
        created = self.client.post(
            "/api/catalog/items",
            data={
                "sku": "SVC1",
                "name": "Backing As Catalog",
                "category": "backing",
                "cost": "10",
                "width_in": "0",
            },
        )
        self.assertEqual(created.status_code, 400)
        self.assertIn("Catalog category must be one of", created.json()["detail"])

        imported = self.client.post(
            "/api/catalog/import",
            files={
                "file": (
                    "catalog.csv",
                    "sku,name,category,cost,width_in\nSVC1,Backing Row,backing,10,0\nM1,Frame One,moulding,12,1.5\n",
                    "text/csv",
                )
            },
        )
        self.assertEqual(imported.status_code, 200)
        self.assertEqual(imported.json()["inserted"], 1)
        self.assertEqual(imported.json()["skipped"], 1)

        search = self.client.get("/api/catalog/search", params={"limit": 0})
        categories = {item["category"] for item in search.json()["items"]}
        self.assertEqual(categories, {"moulding"})

    def test_catalog_search_limit_zero_returns_full_dataset(self):
        rows = ["sku,name,category,cost,width_in"]
        for index in range(1, 306):
            rows.append(f"F{index:03d},Frame {index:03d},moulding,{10 + index / 100:.2f},1.5")
        imported = self.client.post(
            "/api/catalog/import",
            files={"file": ("catalog.csv", "\n".join(rows) + "\n", "text/csv")},
        )
        self.assertEqual(imported.status_code, 200)

        default_search = self.client.get("/api/catalog/search", params={"category": "moulding"})
        self.assertEqual(default_search.status_code, 200)
        self.assertEqual(len(default_search.json()["items"]), 300)

        full_search = self.client.get("/api/catalog/search", params={"category": "moulding", "limit": 0})
        self.assertEqual(full_search.status_code, 200)
        payload = full_search.json()
        self.assertEqual(len(payload["items"]), 305)
        self.assertEqual(payload["items"][0]["sku"], "F305")
        self.assertEqual(payload["items"][-1]["sku"], "F001")

    def test_pfd_import_normalizes_rows_and_preview_urls(self):
        (main_module.PFD_DIR / "Mats.csv").write_text(
            "Code,Vendor,Category,Description,Price Code,Price,Core,Width,Height,Thickness,Available to,System\n"
            "A109,Peterboro,CONSERVATION,TV. BLACK,2,10.95,wh1,32,40,1,3,1\n",
            encoding="utf-8",
        )
        with zipfile.ZipFile(main_module.PFD_DIR / "Mats.zip", "w") as zf:
            zf.writestr("A109.jpg", b"fake-jpg")

        imported = self.client.post("/api/catalog/import/pfd", data={"source": "mats"})
        self.assertEqual(imported.status_code, 200)
        self.assertEqual(imported.json()["inserted"], 1)

        search = self.client.get("/api/catalog/search", params={"q": "A109"})
        self.assertEqual(search.status_code, 200)
        item = search.json()["items"][0]
        self.assertEqual(item["sku"], "A109")
        self.assertEqual(item["category"], "mat")
        self.assertEqual(item["vendor"], "Peterboro")
        self.assertEqual(item["height_in"], 40.0)
        self.assertTrue(item["preview_url"].startswith("/catalog-previews/mats/A109.jpg?v="))
        metadata = json.loads(item["metadata_json"])
        self.assertEqual(item["preview_filename"], "mats/A109.jpg")
        self.assertEqual(metadata["source"], "pfd_mats")
        self.assertEqual(metadata["core"], "wh1")
        self.assertEqual(metadata["vendor_category"], "CONSERVATION")

    def test_catalog_search_hides_missing_preview_urls(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO catalog_items (sku, name, category, cost, preview_filename)
            VALUES ('MISS1', 'Missing Preview', 'moulding', 10, 'mouldings/missing.jpg')
            """
        )
        conn.commit()
        conn.close()

        search = self.client.get("/api/catalog/search", params={"q": "MISS1"})
        self.assertEqual(search.status_code, 200)
        item = search.json()["items"][0]
        self.assertIsNone(item["preview_url"])
        self.assertEqual(item["preview_filename"], "mouldings/missing.jpg")

    def test_catalog_search_resolves_international_preview_prefix_variants(self):
        target = main_module.PREVIEW_DIR / "mouldings"
        target.mkdir(parents=True, exist_ok=True)
        (target / "I0354-3086.jpg").write_bytes(b"fake-jpg")

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO catalog_items (sku, name, category, cost, preview_filename)
            VALUES ('0354-3086', 'Walnut Reverse Stairs', 'moulding', 2.54, 'mouldings/0354-3086.jpg')
            """
        )
        conn.commit()
        conn.close()

        search = self.client.get("/api/catalog/search", params={"q": "0354-3086"})
        self.assertEqual(search.status_code, 200)
        item = search.json()["items"][0]
        self.assertTrue(item["preview_url"].startswith("/catalog-previews/mouldings/I0354-3086.jpg?v="))
        self.assertEqual(item["preview_filename"], "mouldings/0354-3086.jpg")

    def test_backfills_missing_catalog_preview_links_from_nested_assets(self):
        target = main_module.PREVIEW_DIR / "mats" / "Crescent Select"
        target.mkdir(parents=True, exist_ok=True)
        (target / "C9805.jpg").write_bytes(b"fake-jpg")

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO catalog_items (sku, name, category, cost, preview_filename)
            VALUES ('C9805', 'Crescent Coconut Milk 32x40', 'mat', 14, '')
            """
        )
        conn.commit()
        conn.close()

        self.assertEqual(main_module._backfill_catalog_preview_links(), 1)

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT preview_filename FROM catalog_items WHERE sku = 'C9805'")
        self.assertEqual(cur.fetchone()["preview_filename"], "mats/Crescent Select/C9805.jpg")
        conn.close()

        search = self.client.get("/api/catalog/search", params={"q": "C9805"})
        self.assertEqual(search.status_code, 200)
        item = search.json()["items"][0]
        self.assertEqual(item["preview_filename"], "mats/Crescent Select/C9805.jpg")
        self.assertTrue(item["preview_url"].startswith("/catalog-previews/mats/Crescent Select/C9805.jpg?v="))

    def test_service_options_remain_independent_from_catalog_materials(self):
        services = self.client.post(
            "/api/services",
            data={
                "backing_label": "Foam Backing",
                "backing_price": "12",
                "backing_active": "1",
                "mounting_label": "Subject Mounting",
                "mounting_price": "18",
                "mounting_active": "1",
                "frame_mounting_label": "Frame Mounting",
                "frame_mounting_price": "22",
                "frame_mounting_active": "1",
                "printing_label": "Printing",
                "printing_price": "30",
                "printing_active": "1",
                "various_label": "Various",
                "various_price": "8",
                "various_active": "1",
                "assembly_label": "Assembly",
                "assembly_price": "10",
                "assembly_active": "1",
                "royalties_label": "Royalties",
                "royalties_price": "6",
                "royalties_active": "1",
                "custom_1_label": "Canvas Stretch",
                "custom_1_price": "45.50",
                "custom_1_active": "1",
                "custom_2_label": "Blank Service",
                "custom_2_price": "0",
                "custom_2_active": "0",
            },
        )
        self.assertEqual(services.status_code, 200)
        service_rows = {row["key"]: row for row in services.json()["services"]}
        self.assertEqual(service_rows["custom_1"]["price"], 45.5)
        self.assertEqual(service_rows["custom_1"]["active"], 1)

        imported = self.client.post(
            "/api/catalog/import",
            files={
                "file": (
                    "catalog.csv",
                    "sku,name,category,cost,width_in\nM1,Frame One,moulding,10,1.5\nMAT1,Top White,mat,3,0\n",
                    "text/csv",
                )
            },
        )
        self.assertEqual(imported.status_code, 200)

        search = self.client.get("/api/catalog/search", params={"limit": 0})
        items = search.json()["items"]
        by_sku = {item["sku"]: item["id"] for item in items}

        quote = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "8",
                "height_in": "10",
                "labor_flat": "20",
                "moulding_id": str(by_sku["M1"]),
                "top_mat_id": str(by_sku["MAT1"]),
                "backing_key": "backing",
                "backing_discount_pct": "10",
                "printing_key": "printing",
                "custom_1_key": "custom_1",
                "global_discount_pct": "5",
                "other_label": "Rush",
                "other_amount": "15",
                "other_discount_pct": "20",
            },
        )
        self.assertEqual(quote.status_code, 200)
        payload = quote.json()
        self.assertIn("backing", payload["line_items"])
        self.assertIn("printing", payload["line_items"])
        self.assertIn("custom_1", payload["line_items"])
        self.assertIn("Rush", payload["line_items"])
        self.assertEqual(payload["selected"]["addons"]["backing"]["service"]["label"], "Foam Backing")
        self.assertEqual(payload["selected"]["addons"]["custom_1"]["service"]["label"], "Canvas Stretch")
        self.assertEqual(payload["selected"]["global_discount_pct"], 5.0)
        self.assertEqual(payload["selected"]["moulding"]["sku"], "M1")
        self.assertEqual(payload["selected"]["mat"]["sku"], "MAT1")

    def test_service_prices_are_capped_to_dollars_and_cents(self):
        services = self.client.post(
            "/api/services",
            data={
                "backing_label": "Foam Backing",
                "backing_price": "1000",
                "backing_active": "1",
                "mounting_label": "Subject Mounting",
                "mounting_price": "18",
                "mounting_active": "1",
                "frame_mounting_label": "Frame Mounting",
                "frame_mounting_price": "22",
                "frame_mounting_active": "1",
                "printing_label": "Printing",
                "printing_price": "30",
                "printing_active": "1",
                "various_label": "Various",
                "various_price": "8",
                "various_active": "1",
                "assembly_label": "Assembly",
                "assembly_price": "10",
                "assembly_active": "1",
                "royalties_label": "Royalties",
                "royalties_price": "6",
                "royalties_active": "1",
            },
        )
        self.assertEqual(services.status_code, 400)
        self.assertIn("999.99 or less", services.json()["detail"])

    def test_manual_glazing_prices_by_area(self):
        services = self.client.post(
            "/api/services",
            data={
                "glazing_reg_glass_label": "Reg glass",
                "glazing_reg_glass_cost": "0.02",
                "glazing_reg_glass_markup": "2",
                "glazing_reg_glass_basis": "square_inches",
                "glazing_reg_glass_active": "1",
            },
        )
        self.assertEqual(services.status_code, 200)

        quote = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "8",
                "height_in": "10",
                "mat_border_in": "2",
                "labor_flat": "0",
                "glazing_key": "glazing_reg_glass",
            },
        )
        self.assertEqual(quote.status_code, 200)
        payload = quote.json()
        self.assertEqual(payload["selected"]["glazing"]["name"], "Reg glass")
        self.assertEqual(payload["selected"]["glazing"]["basis"], "square_inches")
        self.assertAlmostEqual(payload["line_items"]["glazing"], 6.72)

    def test_price_table_service_applies_admin_markup_multiplier(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO price_table_entries (price_code, half_perimeter, price) VALUES (?, ?, ?)",
            ("mounting:Dry Mounting", 36, 27.20),
        )
        cur.execute(
            """
            UPDATE service_options
            SET label = 'Dry Mounting', pricing_method = 'price_table',
                price_code = 'mounting:Dry Mounting', basis = 'square_inches'
            WHERE key = 'mounting'
            """
        )
        conn.commit()
        conn.close()

        saved = self.client.post(
            "/api/services",
            data={
                "mounting_label": "Dry Mounting",
                "mounting_cost": "0",
                "mounting_markup": "0.33",
                "mounting_basis": "square_inches",
                "mounting_active": "1",
            },
        )
        self.assertEqual(saved.status_code, 200)
        mounting = next(row for row in saved.json()["services"] if row["key"] == "mounting")
        self.assertEqual(mounting["markup"], 0.33)

        quote = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "8",
                "height_in": "10",
                "mat_border_in": "2",
                "labor_flat": "0",
                "mounting_key": "mounting",
            },
        )
        self.assertEqual(quote.status_code, 200)
        self.assertEqual(quote.json()["line_items"]["mounting"], 8.98)

    def test_order_lifecycle_transition_rules(self):
        quote_payload = {"subtotal": 50, "tax": 3, "total": 53}
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Test Customer",
                "customer_contact": "606-555-0101",
                "payload_json": json.dumps(quote_payload),
                "subtotal": "50",
                "tax": "3",
                "total": "53",
            },
        )
        self.assertEqual(created.status_code, 200)
        order_id = created.json()["order_id"]

        unapproved = self.client.post(
            f"/api/orders/{order_id}/status",
            data={"status": "work_order", "note": "operator clicked too early"},
        )
        self.assertEqual(unapproved.status_code, 400)
        self.assertIn("Customer approval is required", unapproved.json()["detail"])

        bad_jump = self.client.post(
            f"/api/orders/{order_id}/status",
            data={"status": "invoice", "note": "skip attempt"},
        )
        self.assertEqual(bad_jump.status_code, 400)

        to_work_order = self.client.post(
            f"/api/orders/{order_id}/status",
            data={"status": "work_order", "note": "approved", "customer_approved": "1"},
        )
        self.assertEqual(to_work_order.status_code, 200)
        self.assertIsNotNone(to_work_order.json()["approved_at"])

        undone = self.client.post(
            f"/api/orders/{order_id}/status",
            data={"status": "invoice", "note": "operator clicked too early"},
        )
        self.assertEqual(undone.status_code, 400)
        self.assertIn("Work order must be marked done", undone.json()["detail"])

        to_invoice = self.client.post(
            f"/api/orders/{order_id}/status",
            data={"status": "invoice", "note": "completed", "work_completed": "1"},
        )
        self.assertEqual(to_invoice.status_code, 200)
        self.assertIsNotNone(to_invoice.json()["completed_at"])

        back_to_work_order = self.client.post(
            f"/api/orders/{order_id}/status",
            data={"status": "work_order", "note": "customer requested changes"},
        )
        self.assertEqual(back_to_work_order.status_code, 200)

        detail = self.client.get(f"/api/orders/{order_id}")
        self.assertEqual(detail.status_code, 200)
        history = detail.json()["history"]
        self.assertEqual([h["status"] for h in history], ["quote", "work_order", "invoice", "work_order"])
        self.assertIsNotNone(detail.json()["order"]["approved_at"])
        self.assertIsNone(detail.json()["order"]["completed_at"])

    def test_quote_requires_customer_name_and_phone(self):
        quote_payload = {"subtotal": 50, "tax": 3, "total": 53}
        missing_phone = self.client.post(
            "/api/orders",
            data={
                "customer_name": "No Phone",
                "customer_contact": "",
                "payload_json": json.dumps(quote_payload),
                "subtotal": "50",
                "tax": "3",
                "total": "53",
            },
        )
        self.assertEqual(missing_phone.status_code, 400)
        self.assertIn("Customer phone number is required", missing_phone.json()["detail"])

        email_only = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Email Only",
                "customer_contact": "email-only@example.com",
                "payload_json": json.dumps(quote_payload),
                "subtotal": "50",
                "tax": "3",
                "total": "53",
            },
        )
        self.assertEqual(email_only.status_code, 400)
        self.assertIn("Customer phone number is required", email_only.json()["detail"])

    def test_legacy_walk_in_quote_cannot_be_advanced(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orders (customer_name, customer_contact, status, payload_json, subtotal, tax, total)
            VALUES ('Walk-in Customer', 'manual', 'quote', ?, 50, 3, 53)
            """,
            (json.dumps({"subtotal": 50, "tax": 3, "total": 53}),),
        )
        order_id = cur.lastrowid
        conn.commit()
        conn.close()

        advanced = self.client.post(
            f"/api/orders/{order_id}/status",
            data={"status": "work_order", "note": "approved", "customer_approved": "1"},
        )
        self.assertEqual(advanced.status_code, 400)
        self.assertIn("Customer phone number is required", advanced.json()["detail"])

    def test_order_export_rejects_malformed_historic_payload(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orders (customer_name, customer_contact, status, payload_json, subtotal, tax, total)
            VALUES ('Bad Payload', '', 'quote', 'not-json', 10, 0.6, 10.6)
            """
        )
        order_id = cur.lastrowid
        conn.commit()
        conn.close()

        exported = self.client.get(f"/api/orders/{order_id}/export", params={"format": "pdf"})
        self.assertEqual(exported.status_code, 400)
        self.assertIn("Stored order payload is invalid JSON", exported.json()["detail"])

    def test_legacy_admin_orders_export_route_returns_csv(self):
        login = self.client.post(
            "/admin/login",
            data={"email": "admin", "password": "admin"},
            follow_redirects=False,
        )
        self.assertEqual(login.status_code, 303)

        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Admin Export",
                "customer_contact": "606-555-0102",
                "payload_json": json.dumps({"subtotal": 50, "tax": 3, "total": 53}),
                "subtotal": "50",
                "tax": "3",
                "total": "53",
            },
        )
        self.assertEqual(created.status_code, 200)

        exported = self.client.get("/admin/orders/export")
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.headers["content-type"].split(";")[0], "text/csv")
        self.assertIn("quote_number,id,customer_name", exported.text)
        self.assertIn("Admin Export", exported.text)

    def test_customers_can_be_created_and_linked_to_orders(self):
        created_customer = self.client.post(
            "/api/customers",
            data={
                "name": "Ada Frame",
                "contact": "606-555-0103",
                "customer_email": "ada@example.com",
                "notes": "Prefers warm woods",
            },
        )
        self.assertEqual(created_customer.status_code, 200)
        customer_id = created_customer.json()["customer_id"]

        listed = self.client.get("/api/customers", params={"q": "Ada"})
        self.assertEqual(listed.status_code, 200)
        customers = listed.json()["customers"]
        self.assertEqual(len(customers), 1)
        self.assertEqual(customers[0]["id"], customer_id)
        self.assertEqual(customers[0]["customer_email"], "ada@example.com")

        quote_payload = {"subtotal": 80, "tax": 4.8, "total": 84.8}
        created_order = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Ada Frame",
                "customer_contact": "606-555-0103",
                "customer_email": "new-ada@example.com",
                "payload_json": json.dumps(quote_payload),
                "subtotal": "80",
                "tax": "4.8",
                "total": "84.8",
            },
        )
        self.assertEqual(created_order.status_code, 200)

        detail = self.client.get(f"/api/customers/{customer_id}")
        self.assertEqual(detail.status_code, 200)
        payload = detail.json()
        self.assertEqual(payload["customer"]["name"], "Ada Frame")
        self.assertEqual(payload["customer"]["contact"], "606-555-0103")
        self.assertEqual(payload["customer"]["customer_email"], "new-ada@example.com")
        self.assertEqual(len(payload["orders"]), 1)
        self.assertEqual(payload["orders"][0]["status"], "quote")

        email_search = self.client.get("/api/customers", params={"q": "new-ada@example.com"})
        self.assertEqual(email_search.status_code, 200)
        self.assertEqual(email_search.json()["customers"][0]["id"], customer_id)

    def test_init_db_migrates_customer_email_columns_without_losing_rows(self):
        db.DB_PATH.unlink()
        conn = db.get_connection()
        conn.executescript(
            """
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                customer_contact TEXT,
                status TEXT NOT NULL DEFAULT 'quote',
                payload_json TEXT NOT NULL,
                subtotal REAL NOT NULL,
                tax REAL NOT NULL,
                total REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO customers (name, contact, notes) VALUES ('Legacy Customer', '606-555-0199', 'keep');
            INSERT INTO orders (customer_name, customer_contact, payload_json, subtotal, tax, total)
            VALUES ('Legacy Customer', '606-555-0199', '{}', 10, 0.6, 10.6);
            """
        )
        conn.commit()
        conn.close()

        db.init_db()

        conn = db.get_connection()
        customer = conn.execute("SELECT name, contact, customer_email FROM customers").fetchone()
        order = conn.execute("SELECT customer_name, customer_contact, customer_email FROM orders").fetchone()
        conn.close()
        self.assertEqual(dict(customer), {"name": "Legacy Customer", "contact": "606-555-0199", "customer_email": None})
        self.assertEqual(
            dict(order),
            {"customer_name": "Legacy Customer", "customer_contact": "606-555-0199", "customer_email": None},
        )

    def test_quote_calculation_rejects_invalid_inputs(self):
        invalid_dimension = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "0",
                "height_in": "10",
                "labor_flat": "20",
            },
        )
        self.assertEqual(invalid_dimension.status_code, 400)
        self.assertIn("width_in must be positive", invalid_dimension.json()["detail"])

        invalid_image = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "8",
                "height_in": "10",
                "labor_flat": "20",
                "image_id": "999",
            },
        )
        self.assertEqual(invalid_image.status_code, 400)
        self.assertIn("Image 999 not found", invalid_image.json()["detail"])

    def test_upload_image_rejects_invalid_rotation_and_crop_json(self):
        image_bytes = io.BytesIO()
        Image.new("RGB", (10, 10), "white").save(image_bytes, format="PNG")
        payload = image_bytes.getvalue()

        bad_rotation = self.client.post(
            "/api/images/upload",
            data={
                "width_in": "8",
                "height_in": "10",
                "ratio_label": "free",
                "crop_json": "{}",
                "rotation_deg": "45",
            },
            files={"file": ("art.png", payload, "image/png")},
        )
        self.assertEqual(bad_rotation.status_code, 400)
        self.assertIn("rotation_deg must be a multiple of 90", bad_rotation.json()["detail"])

        bad_crop = self.client.post(
            "/api/images/upload",
            data={
                "width_in": "8",
                "height_in": "10",
                "ratio_label": "free",
                "crop_json": "[]",
                "rotation_deg": "0",
            },
            files={"file": ("art.png", payload, "image/png")},
        )
        self.assertEqual(bad_crop.status_code, 400)
        self.assertIn("crop_json must be a JSON object", bad_crop.json()["detail"])

    def test_upload_image_applies_rotation_to_saved_file(self):
        image = Image.new("RGB", (80, 40), "white")
        px = image.load()
        for y in range(40):
            for x in range(80):
                if x < 40 and y < 20:
                    px[x, y] = (255, 0, 0)
                elif x >= 40 and y < 20:
                    px[x, y] = (0, 0, 255)
                elif x < 40 and y >= 20:
                    px[x, y] = (0, 255, 0)
                else:
                    px[x, y] = (255, 255, 0)
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")

        uploaded = self.client.post(
            "/api/images/upload",
            data={
                "width_in": "8",
                "height_in": "10",
                "ratio_label": "custom",
                "crop_json": json.dumps(
                    {
                        "version": 2,
                        "cropper": {"x": 0, "y": 0, "width": 40, "height": 80, "rotate": 0, "scaleX": 1, "scaleY": 1},
                        "ratio_w": 8,
                        "ratio_h": 10,
                    }
                ),
                "rotation_deg": "90",
            },
            files={"file": ("quadrants.png", image_bytes.getvalue(), "image/png")},
        )
        self.assertEqual(uploaded.status_code, 200)
        saved = Image.open(main_module.UPLOAD_DIR / uploaded.json()["filename"]).convert("RGB")
        self.assertEqual(saved.size, (40, 80))
        self.assertEqual(saved.getpixel((0, 0)), (0, 255, 0))
        self.assertEqual(saved.getpixel((saved.width - 1, 0)), (255, 0, 0))

    def test_create_order_rejects_invalid_payload_json(self):
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Broken Payload",
                "customer_contact": "606-555-0104",
                "payload_json": "[]",
                "subtotal": "50",
                "tax": "3",
                "total": "53",
            },
        )
        self.assertEqual(created.status_code, 400)
        self.assertIn("payload_json must be a JSON object", created.json()["detail"])

    def test_customer_edit_renames_linked_orders(self):
        customer = self.client.post(
            "/api/customers",
            data={
                "name": "Old Name",
                "contact": "606-555-0105",
                "customer_email": "old@example.com",
                "notes": "legacy",
            },
        )
        customer_id = customer.json()["customer_id"]

        order = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Old Name",
                "customer_contact": "606-555-0105",
                "customer_email": "old@example.com",
                "payload_json": json.dumps({"subtotal": 10, "tax": 0.6, "total": 10.6}),
                "subtotal": "10",
                "tax": "0.6",
                "total": "10.6",
            },
        )
        order_id = order.json()["order_id"]

        updated = self.client.post(
            f"/api/customers/{customer_id}",
            data={
                "name": "New Name",
                "contact": "606-555-0106",
                "customer_email": "new@example.com",
                "notes": "preferred",
            },
        )
        self.assertEqual(updated.status_code, 200)

        order_detail = self.client.get(f"/api/orders/{order_id}")
        self.assertEqual(order_detail.status_code, 200)
        self.assertEqual(order_detail.json()["order"]["customer_name"], "New Name")
        self.assertEqual(order_detail.json()["order"]["customer_contact"], "606-555-0106")
        self.assertEqual(order_detail.json()["order"]["customer_email"], "new@example.com")

    def test_order_edit_updates_customer_fields(self):
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Original Customer",
                "customer_contact": "606-555-0107",
                "customer_email": "original@example.com",
                "payload_json": json.dumps({"subtotal": 40, "tax": 2.4, "total": 42.4}),
                "subtotal": "40",
                "tax": "2.4",
                "total": "42.4",
            },
        )
        order_id = created.json()["order_id"]

        updated = self.client.post(
            f"/api/orders/{order_id}",
            data={
                "customer_name": "Updated Customer",
                "customer_contact": "606-555-0108",
                "customer_email": "updated@example.com",
                "note": "phone typo corrected",
            },
        )
        self.assertEqual(updated.status_code, 200)

        detail = self.client.get(f"/api/orders/{order_id}")
        self.assertEqual(detail.status_code, 200)
        payload = detail.json()
        self.assertEqual(payload["order"]["customer_name"], "Updated Customer")
        self.assertEqual(payload["order"]["customer_contact"], "606-555-0108")
        self.assertEqual(payload["order"]["customer_email"], "updated@example.com")
        self.assertEqual(payload["history"][-1]["note"], "phone typo corrected")

        customers = self.client.get("/api/customers", params={"q": "Updated Customer"})
        self.assertEqual(customers.status_code, 200)
        self.assertEqual(len(customers.json()["customers"]), 1)
        self.assertEqual(customers.json()["customers"][0]["customer_email"], "updated@example.com")

    def test_customer_and_order_edits_preserve_email_when_field_is_omitted(self):
        customer = self.client.post(
            "/api/customers",
            data={
                "name": "Preserved Email",
                "contact": "606-555-0120",
                "customer_email": "preserve@example.com",
            },
        )
        customer_id = customer.json()["customer_id"]
        order = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Preserved Email",
                "customer_contact": "606-555-0120",
                "customer_email": "preserve@example.com",
                "payload_json": json.dumps({"subtotal": 20, "tax": 1.2, "total": 21.2}),
                "subtotal": "20",
                "tax": "1.2",
                "total": "21.2",
            },
        )
        order_id = order.json()["order_id"]

        customer_update = self.client.post(
            f"/api/customers/{customer_id}",
            data={"name": "Preserved Email", "contact": "606-555-0121", "notes": "phone only"},
        )
        self.assertEqual(customer_update.status_code, 200)
        order_update = self.client.post(
            f"/api/orders/{order_id}",
            data={"customer_name": "Preserved Email", "customer_contact": "606-555-0122"},
        )
        self.assertEqual(order_update.status_code, 200)

        customer_detail = self.client.get(f"/api/customers/{customer_id}").json()["customer"]
        order_detail = self.client.get(f"/api/orders/{order_id}").json()["order"]
        self.assertEqual(customer_detail["customer_email"], "preserve@example.com")
        self.assertEqual(order_detail["customer_email"], "preserve@example.com")

    def test_order_edit_can_update_saved_quote_payload_and_totals(self):
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Editable Quote",
                "customer_contact": "606-555-0202",
                "payload_json": json.dumps({"subtotal": 40, "tax": 2.4, "total": 42.4, "line_items": {"labor": 40}}),
                "subtotal": "40",
                "tax": "2.4",
                "total": "42.4",
            },
        )
        self.assertEqual(created.status_code, 200)
        order_id = created.json()["order_id"]

        updated_payload = {
            "subtotal": 75,
            "tax": 4.5,
            "total": 79.5,
            "line_items": {"labor": 25, "mat": 50},
            "design_state": {"opening_layout": "single"},
        }
        updated = self.client.post(
            f"/api/orders/{order_id}",
            data={
                "customer_name": "Editable Quote",
                "customer_contact": "606-555-0202",
                "payload_json": json.dumps(updated_payload),
                "subtotal": "75",
                "tax": "4.5",
                "total": "79.5",
                "note": "Saved quote contents updated from Design",
            },
        )
        self.assertEqual(updated.status_code, 200)

        detail = self.client.get(f"/api/orders/{order_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["order"]["subtotal"], 75.0)
        self.assertEqual(detail.json()["order"]["tax"], 4.5)
        self.assertEqual(detail.json()["order"]["total"], 79.5)
        self.assertEqual(detail.json()["order"]["payload"]["line_items"]["mat"], 50)
        self.assertEqual(detail.json()["history"][-1]["note"], "Saved quote contents updated from Design")

    def test_settings_can_update_quote_pricing_rules(self):
        defaults = self.client.get("/api/settings")
        self.assertEqual(defaults.status_code, 200)
        self.assertEqual(defaults.json()["pricing"]["tax_rate"], 0.06)

        updated = self.client.post(
            "/api/settings",
            data={
                "tax_rate": "0.08",
                "markup_moulding": "3.0",
                "markup_mat": "2.5",
                "markup_glazing": "2.2",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["pricing"]["tax_rate"], 0.08)

        csv1 = "sku,name,category,cost,width_in\nA1,Frame Alpha,moulding,10,1.5\nA2,Mat White,mat,3,0\nA3,Glass Clear,glazing,4,0\n"
        imported = self.client.post(
            "/api/catalog/import",
            files={"file": ("catalog.csv", csv1, "text/csv")},
        )
        self.assertEqual(imported.status_code, 200)

        search = self.client.get("/api/catalog/search")
        items = search.json()["items"]
        by_sku = {item["sku"]: item["id"] for item in items}

        quote = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "8",
                "height_in": "10",
                "labor_flat": "20",
                "moulding_id": str(by_sku["A1"]),
                "mat_id": str(by_sku["A2"]),
                "glazing_id": str(by_sku["A3"]),
            },
        )
        self.assertEqual(quote.status_code, 200)
        payload = quote.json()
        self.assertEqual(payload["pricing_rules"]["tax_rate"], 0.08)
        self.assertEqual(payload["pricing_rules"]["markup_moulding"], 3.0)
        self.assertAlmostEqual(payload["tax"], round(payload["subtotal"] * 0.08, 2))

    def test_export_uses_stored_tax_rate_label(self):
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Export Customer",
                "customer_contact": "606-555-0109",
                "payload_json": json.dumps(
                    {
                        "subtotal": 50,
                        "tax": 4,
                        "total": 54,
                        "pricing_rules": {"tax_rate": 0.08},
                        "selected": {},
                        "line_items": {},
                    }
                ),
                "subtotal": "50",
                "tax": "4",
                "total": "54",
            },
        )
        order_id = created.json()["order_id"]
        exported = self.client.get(f"/api/orders/{order_id}/export", params={"format": "pdf"})
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.headers["content-type"], "application/pdf")
        self.assertGreater(len(exported.content), 100)

    def test_orders_can_be_filtered_by_status_and_query(self):
        for name, status in [("Alpha Quote", "quote"), ("Beta Work", "quote"), ("Gamma Invoice", "quote")]:
            created = self.client.post(
                "/api/orders",
                data={
                    "customer_name": name,
                    "customer_contact": "606-555-0188",
                    "payload_json": json.dumps({"subtotal": 20, "tax": 1.2, "total": 21.2}),
                    "subtotal": "20",
                    "tax": "1.2",
                    "total": "21.2",
                },
            )
            order_id = created.json()["order_id"]
            if status == "work_order":
                self.client.post(
                    f"/api/orders/{order_id}/status",
                    data={"status": "work_order", "note": "approved", "customer_approved": "1"},
                )

        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Beta Work",
                "customer_contact": "606-555-0110",
                "payload_json": json.dumps({"subtotal": 20, "tax": 1.2, "total": 21.2}),
                "subtotal": "20",
                "tax": "1.2",
                "total": "21.2",
            },
        )
        work_order_id = created.json()["order_id"]
        self.client.post(
            f"/api/orders/{work_order_id}/status",
            data={"status": "work_order", "note": "approved", "customer_approved": "1"},
        )

        filtered = self.client.get("/api/orders", params={"q": "Beta", "status": "work_order"})
        self.assertEqual(filtered.status_code, 200)
        orders = filtered.json()["orders"]
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["customer_name"], "Beta Work")

    def test_order_list_includes_phone_balance_and_lifecycle_markers(self):
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Split View Customer",
                "customer_contact": "606-555-0201",
                "customer_email": "split@example.com",
                "payload_json": json.dumps({"subtotal": 100, "tax": 6, "total": 106}),
                "subtotal": "100",
                "tax": "6",
                "total": "106",
            },
        )
        self.assertEqual(created.status_code, 200)
        order_id = created.json()["order_id"]

        listed = self.client.get("/api/orders", params={"q": "Split View"})
        self.assertEqual(listed.status_code, 200)
        row = listed.json()["orders"][0]
        self.assertEqual(row["id"], order_id)
        self.assertEqual(row["quote_number"], f"Q{order_id:05d}")
        self.assertEqual(row["customer_contact"], "606-555-0201")
        self.assertEqual(row["customer_email"], "split@example.com")
        self.assertEqual(row["balance"], 106.0)
        self.assertEqual(row["next_action"], "approve_quote")
        self.assertIsNone(row["approved_at"])
        self.assertIsNone(row["completed_at"])
        self.assertIsNone(row["invoiced_at"])

    def test_order_list_returns_all_local_jobs_for_table_counts_and_sorting(self):
        conn = db.get_connection()
        cur = conn.cursor()
        for index in range(151):
            cur.execute(
                """
                INSERT INTO orders (customer_name, customer_contact, status, payload_json, subtotal, tax, total)
                VALUES (?, '606-555-0100', 'quote', '{}', 10, 0.6, 10.6)
                """,
                (f"Bulk Customer {index:03d}",),
            )
        conn.commit()
        conn.close()

        listed = self.client.get("/api/orders")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["orders"]), 151)

    def test_catalog_items_can_be_created_and_updated_manually(self):
        created = self.client.post(
            "/api/catalog/items",
            data={
                "sku": "M100",
                "name": "Manual Moulding",
                "category": "moulding",
                "cost": "12.5",
                "width_in": "1.75",
            },
        )
        self.assertEqual(created.status_code, 200)
        item_id = created.json()["item_id"]

        updated = self.client.post(
            f"/api/catalog/items/{item_id}",
            data={
                "sku": "M100",
                "name": "Manual Moulding Updated",
                "category": "moulding",
                "cost": "13.0",
                "width_in": "2.0",
                "active": "1",
            },
        )
        self.assertEqual(updated.status_code, 200)

        search = self.client.get("/api/catalog/search", params={"q": "Updated"})
        self.assertEqual(search.status_code, 200)
        items = search.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["sku"], "M100")
        self.assertEqual(items[0]["width_in"], 2.0)

    def test_backups_can_be_created_and_listed(self):
        created = self.client.post("/api/backups")
        self.assertEqual(created.status_code, 200)
        filename = created.json()["filename"]

        listed = self.client.get("/api/backups")
        self.assertEqual(listed.status_code, 200)
        backups = listed.json()["backups"]
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0]["filename"], filename)

        downloaded = self.client.get(f"/api/backups/{filename}")
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.headers["content-type"], "application/zip")

    def test_order_handoff_returns_email_and_sms_text(self):
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Handoff Customer",
                "customer_contact": "606-555-0111",
                "customer_email": "handoff@example.com",
                "payload_json": json.dumps(
                    {
                        "subtotal": 30,
                        "tax": 1.8,
                        "total": 31.8,
                        "design_state": {"opening_layout": "diptych"},
                        "selected": {},
                        "line_items": {},
                    }
                ),
                "subtotal": "30",
                "tax": "1.8",
                "total": "31.8",
            },
        )
        order_id = created.json()["order_id"]
        handoff = self.client.get(f"/api/orders/{order_id}/handoff")
        self.assertEqual(handoff.status_code, 200)
        payload = handoff.json()
        self.assertIn("The Printery Framing Studio quote", payload["email_subject"])
        self.assertIn("2 openings", payload["email_body"])
        self.assertIn("attach the PDF quote and mockup JPG", payload["email_body"])
        self.assertNotIn("/api/", payload["email_body"])
        self.assertNotIn("/api/", payload["sms_body"])
        self.assertEqual(payload["customer_email"], "handoff@example.com")
        self.assertEqual(payload["customer_phone"], "606-555-0111")
        self.assertEqual(payload["quote_pdf_url"], f"/api/orders/{order_id}/export?format=pdf&document=quote")
        self.assertEqual(payload["preview_jpg_url"], f"/api/orders/{order_id}/export?format=jpg")

        email_search = self.client.get("/api/orders", params={"q": "handoff@example.com"})
        self.assertEqual(email_search.status_code, 200)
        self.assertEqual(email_search.json()["orders"][0]["id"], order_id)

    def test_order_pdf_export_handles_null_glazing_selection(self):
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Export Smoke",
                "customer_contact": "606-555-0109",
                "payload_json": json.dumps(
                    {
                        "subtotal": 30,
                        "tax": 1.8,
                        "total": 31.8,
                        "design_state": {"opening_layout": "single"},
                        "selected": {
                            "moulding": {"sku": "UP4825", "name": "Structura Charcoal"},
                            "mats": [{"slot": "top", "item": {"sku": "W793", "name": "LIGHT SILVER WHITE CORE"}}],
                            "glazing": None,
                            "mat_border_in": 2,
                        },
                        "line_items": {"moulding": 20, "mat": 10},
                    }
                ),
                "subtotal": "30",
                "tax": "1.8",
                "total": "31.8",
            },
        )
        order_id = created.json()["order_id"]

        exported = self.client.get(f"/api/orders/{order_id}/export", params={"format": "pdf"})
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.headers["content-type"], "application/pdf")

    def test_order_export_supports_inline_preview_and_attachment_download(self):
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Preview Customer",
                "customer_contact": "606-555-0181",
                "payload_json": json.dumps({"subtotal": 30, "tax": 1.8, "total": 31.8, "selected": {}}),
                "subtotal": "30",
                "tax": "1.8",
                "total": "31.8",
            },
        )
        order_id = created.json()["order_id"]

        inline = self.client.get(
            f"/api/orders/{order_id}/export",
            params={"format": "pdf", "document": "quote", "disposition": "inline"},
        )
        self.assertEqual(inline.status_code, 200)
        self.assertTrue(inline.headers["content-disposition"].startswith("inline;"))

        attachment = self.client.get(
            f"/api/orders/{order_id}/export",
            params={"format": "jpg", "disposition": "attachment"},
        )
        self.assertEqual(attachment.status_code, 200)
        self.assertTrue(attachment.headers["content-disposition"].startswith("attachment;"))

        invalid = self.client.get(
            f"/api/orders/{order_id}/export",
            params={"format": "pdf", "disposition": "popup"},
        )
        self.assertEqual(invalid.status_code, 400)

    def test_order_pdf_export_names_form_by_status(self):
        mockup = io.BytesIO()
        Image.new("RGB", (12, 8), "#ffccd8").save(mockup, format="JPEG")
        mockup_data_url = "data:image/jpeg;base64," + base64.b64encode(mockup.getvalue()).decode("ascii")
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Form Customer",
                "customer_contact": "606-555-0112",
                "payload_json": json.dumps(
                    {
                        "subtotal": 30,
                        "tax": 1.8,
                        "total": 31.8,
                        "pricing_rules": {"tax_rate": 0.06},
                        "design_state": {
                            "item_name": "Moulding & Single Mat",
                            "mockup_image_data_url": mockup_data_url,
                        },
                        "selected": {
                            "subject_width_in": 8,
                            "subject_height_in": 10,
                            "outside_width_in": 12,
                            "outside_height_in": 14,
                            "mat_border_in": 2,
                            "moulding": {"sku": "F1", "name": "Frame One"},
                            "mats": [{"slot": "top", "item": {"sku": "M1", "name": "White"}, "reveal_in": 0}],
                            "addons": {},
                        },
                        "line_items": {"moulding": 20, "mat": 10},
                    }
                ),
                "subtotal": "30",
                "tax": "1.8",
                "total": "31.8",
            },
        )
        order_id = created.json()["order_id"]
        quote_number = created.json()["quote_number"]

        quote_pdf = self.client.get(f"/api/orders/{order_id}/export", params={"format": "pdf", "document": "quote"})
        self.assertEqual(quote_pdf.status_code, 200)
        self.assertIn(f"Quote-{quote_number}.pdf", quote_pdf.headers["content-disposition"])
        self.assertIsNotNone(main_module._mockup_image_reader({"design_state": {"mockup_image_data_url": mockup_data_url}}))

        explicit_work_order_pdf = self.client.get(
            f"/api/orders/{order_id}/export",
            params={"format": "pdf", "document": "work_order"},
        )
        self.assertEqual(explicit_work_order_pdf.status_code, 200)
        self.assertIn(f"Work-Order-{quote_number}.pdf", explicit_work_order_pdf.headers["content-disposition"])

        bad_document = self.client.get(f"/api/orders/{order_id}/export", params={"format": "pdf", "document": "receipt"})
        self.assertEqual(bad_document.status_code, 400)

        self.client.post(
            f"/api/orders/{order_id}/status",
            data={"status": "work_order", "note": "approved", "customer_approved": "1"},
        )
        work_order_pdf = self.client.get(f"/api/orders/{order_id}/export", params={"format": "pdf"})
        self.assertEqual(work_order_pdf.status_code, 200)
        self.assertIn(f"Work-Order-{quote_number}.pdf", work_order_pdf.headers["content-disposition"])

        self.client.post(
            f"/api/orders/{order_id}/status",
            data={"status": "invoice", "note": "complete", "work_completed": "1"},
        )
        invoice_pdf = self.client.get(f"/api/orders/{order_id}/export", params={"format": "pdf"})
        self.assertEqual(invoice_pdf.status_code, 200)
        self.assertIn(f"Invoice-{quote_number}.pdf", invoice_pdf.headers["content-disposition"])

        if shutil.which("pdftotext"):
            pdf_path = Path(self.tempdir.name) / "quote.pdf"
            pdf_path.write_bytes(quote_pdf.content)
            text = subprocess.check_output(["pdftotext", "-layout", str(pdf_path), "-"], text=True)
            self.assertIn("Quantity", text)
            self.assertIn("Total", text)
            self.assertNotIn("Price", text)
            self.assertNotIn("Amount", text)

    def test_quote_supports_multi_mat_stack(self):
        imported = self.client.post(
            "/api/catalog/import",
            files={
                "file": (
                    "catalog.csv",
                    "sku,name,category,cost,width_in\n"
                    "F1,Frame One,moulding,10,1.5\n"
                    "M1,Top White,mat,3,0\n"
                    "M2,Black Core,mat,2,0\n"
                    "M3,Gold Accent,mat,2.5,0\n"
                    "G1,Clear Glass,glazing,4,0\n",
                    "text/csv",
                )
            },
        )
        self.assertEqual(imported.status_code, 200)

        search = self.client.get("/api/catalog/search")
        items = search.json()["items"]
        by_sku = {item["sku"]: item["id"] for item in items}

        quote = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "16",
                "height_in": "20",
                "mat_border_in": "3",
                "labor_flat": "20",
                "moulding_id": str(by_sku["F1"]),
                "top_mat_id": str(by_sku["M1"]),
                "second_mat_id": str(by_sku["M2"]),
                "third_mat_id": str(by_sku["M3"]),
                "second_mat_reveal_in": "0.25",
                "third_mat_reveal_in": "0.125",
                "glazing_id": str(by_sku["G1"]),
            },
        )
        self.assertEqual(quote.status_code, 200)
        payload = quote.json()
        self.assertEqual(len(payload["selected"]["mats"]), 3)
        self.assertEqual(payload["selected"]["mats"][1]["slot"], "second")
        self.assertEqual(payload["selected"]["mats"][1]["reveal_in"], 0.25)
        self.assertEqual(payload["selected"]["mats"][2]["slot"], "third")
        self.assertEqual(payload["selected"]["mats"][2]["reveal_in"], 0.125)
        self.assertGreater(payload["line_items"]["mat"], 0)
        self.assertGreater(payload["area_sqft"], (16 * 20) / 144)

    def test_explicit_line_discounts_override_global_without_stacking(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO printing_options (label, unit_price, active, sort_order) VALUES ('Print 5x7', 10, 1, 10)")
        printing_id = cur.lastrowid
        conn.commit()
        conn.close()

        quote = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "8", "height_in": "10", "labor_flat": "20",
                "printing_option_id": str(printing_id), "printing_count": "2",
                "global_discount_pct": "30", "printing_discount_pct": "30",
                "labor_discount_pct": "30",
            },
        )
        self.assertEqual(quote.status_code, 200)
        payload = quote.json()
        self.assertEqual(payload["line_items"]["printing"], 14.0)
        self.assertEqual(payload["line_items"]["labor"], 14.0)
        self.assertEqual(payload["selected"]["addons"]["printing"]["unit_price"], 10.0)
        self.assertEqual(payload["selected"]["addons"]["printing"]["count"], 2.0)
        self.assertEqual(payload["selected"]["addons"]["printing"]["discount_pct"], 30.0)

    def test_material_and_mat_layer_discounts_are_independent(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO catalog_items (sku, name, category, cost, width_in) VALUES ('M-D', 'Discount Frame', 'moulding', 10, 1.5)")
        moulding_id = cur.lastrowid
        cur.execute("INSERT INTO catalog_items (sku, name, category, cost, width_in) VALUES ('MAT-A', 'Top Mat', 'mat', 4, 0)")
        top_mat_id = cur.lastrowid
        cur.execute("INSERT INTO catalog_items (sku, name, category, cost, width_in) VALUES ('MAT-B', 'Second Mat', 'mat', 5, 0)")
        second_mat_id = cur.lastrowid
        conn.commit()
        conn.close()

        base = self.client.post(
            "/api/quotes/calculate",
            data={"width_in": "8", "height_in": "10", "labor_flat": "0", "moulding_id": moulding_id,
                  "top_mat_id": top_mat_id, "second_mat_id": second_mat_id},
        ).json()["line_items"]
        sale = self.client.post(
            "/api/quotes/calculate",
            data={"width_in": "8", "height_in": "10", "labor_flat": "0", "moulding_id": moulding_id,
                  "top_mat_id": top_mat_id, "second_mat_id": second_mat_id,
                  "moulding_discount_pct": "80", "top_mat_discount_pct": "30", "second_mat_discount_pct": "10"},
        ).json()["line_items"]
        self.assertEqual(sale["moulding"], round(base["moulding"] * 0.20, 2))
        self.assertEqual(sale["mat"], round(base["mat"] * 0.70, 2))
        self.assertEqual(sale["mat_second"], round(base["mat_second"] * 0.90, 2))

    def test_legacy_global_discount_is_used_when_line_discount_is_omitted(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO printing_options (label, unit_price, active, sort_order) VALUES ('Print 8x10', 20, 1, 10)")
        printing_id = cur.lastrowid
        conn.commit()
        conn.close()

        quote = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "8", "height_in": "10", "labor_flat": "20",
                "printing_option_id": str(printing_id), "printing_count": "1",
                "global_discount_pct": "25",
            },
        )
        self.assertEqual(quote.status_code, 200)
        self.assertEqual(quote.json()["line_items"]["printing"], 15.0)
        self.assertEqual(quote.json()["line_items"]["labor"], 15.0)

    def test_quote_rejects_line_discount_above_one_hundred(self):
        response = self.client.post(
            "/api/quotes/calculate",
            data={"width_in": "8", "height_in": "10", "labor_flat": "20", "labor_discount_pct": "101"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("labor_discount_pct must be 100 or less", response.json()["detail"])

    def test_quote_rejects_negative_global_and_line_discounts(self):
        for field_name in ("global_discount_pct", "labor_discount_pct"):
            with self.subTest(field_name=field_name):
                response = self.client.post(
                    "/api/quotes/calculate",
                    data={"width_in": "8", "height_in": "10", field_name: "-1"},
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(f"{field_name} must be non-negative", response.json()["detail"])

    def test_quote_rejects_non_finite_numeric_inputs(self):
        cases = {
            "width_in": "nan",
            "moulding_cost_ft": "inf",
            "other_amount": "-inf",
            "printing_count": "nan",
            "global_discount_pct": "inf",
            "labor_discount_pct": "nan",
        }
        for field_name, value in cases.items():
            with self.subTest(field_name=field_name):
                data = {"width_in": "8", "height_in": "10", field_name: value}
                response = self.client.post("/api/quotes/calculate", data=data)
                self.assertEqual(response.status_code, 400)
                self.assertIn(f"{field_name} must be a finite number", response.json()["detail"])

    def test_quote_accepts_zero_and_one_hundred_percent_discount_boundaries(self):
        zero = self.client.post(
            "/api/quotes/calculate",
            data={"width_in": "8", "height_in": "10", "labor_flat": "20",
                  "global_discount_pct": "100", "labor_discount_pct": "0"},
        )
        hundred = self.client.post(
            "/api/quotes/calculate",
            data={"width_in": "8", "height_in": "10", "labor_flat": "20",
                  "global_discount_pct": "0", "labor_discount_pct": "100"},
        )
        self.assertEqual(zero.status_code, 200)
        self.assertEqual(zero.json()["line_items"]["labor"], 20.0)
        self.assertEqual(hundred.status_code, 200)
        self.assertEqual(hundred.json()["line_items"].get("labor", 0.0), 0.0)

    def test_quote_rejects_negative_and_non_finite_counts(self):
        for value in ("-1", "inf"):
            with self.subTest(value=value):
                response = self.client.post(
                    "/api/quotes/calculate",
                    data={"width_in": "8", "height_in": "10", "printing_count": value},
                )
                self.assertEqual(response.status_code, 400)

    def test_legacy_printing_key_remains_available_without_printing_option_id(self):
        conn = db.get_connection()
        conn.execute(
            "UPDATE service_options SET label = 'Legacy Printing', cost = 12, markup = 1, basis = 'count', active = 1 WHERE key = 'printing'"
        )
        conn.commit()
        conn.close()
        response = self.client.post(
            "/api/quotes/calculate",
            data={"width_in": "8", "height_in": "10", "labor_flat": "0",
                  "printing_key": "printing", "printing_count": "2", "global_discount_pct": "25"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["line_items"]["printing"], 18.0)
        self.assertEqual(payload["selected"]["addons"]["printing"]["service"]["label"], "Legacy Printing")

    def test_quote_closes_owned_connection_when_lookup_fails(self):
        original_get_connection = main_module.get_connection
        tracked_connections = []

        class TrackedConnection:
            def __init__(self):
                self.connection = original_get_connection()
                self.closed = False

            def __getattr__(self, name):
                return getattr(self.connection, name)

            def close(self):
                self.closed = True
                self.connection.close()

        def tracked_get_connection():
            connection = TrackedConnection()
            tracked_connections.append(connection)
            return connection

        with patch.object(main_module, "get_connection", side_effect=tracked_get_connection):
            response = self.client.post(
                "/api/quotes/calculate",
                data={"width_in": "8", "height_in": "10", "printing_option_id": "999999"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertGreaterEqual(len(tracked_connections), 2)
        self.assertTrue(all(connection.closed for connection in tracked_connections))

    def test_inactive_printing_option_is_rejected(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO printing_options (label, unit_price, active, sort_order) VALUES ('Retired Print', 12, 0, 10)")
        option_id = cur.lastrowid
        conn.commit()
        conn.close()
        response = self.client.post(
            "/api/quotes/calculate",
            data={"width_in": "8", "height_in": "10", "labor_flat": "0", "printing_option_id": option_id},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("is inactive", response.json()["detail"])

    def test_saved_quote_retains_printing_price_snapshot_after_admin_edit(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO printing_options (label, unit_price, active, sort_order) VALUES ('Print 8x10', 20, 1, 10)")
        option_id = cur.lastrowid
        conn.commit()
        conn.close()
        quote = self.client.post(
            "/api/quotes/calculate",
            data={"width_in": "8", "height_in": "10", "labor_flat": "0", "printing_option_id": option_id},
        ).json()
        created = self.client.post(
            "/api/orders",
            data={"customer_name": "Print Buyer", "customer_contact": "606-555-0188",
                  "payload_json": json.dumps(quote), "subtotal": quote["subtotal"],
                  "tax": quote["tax"], "total": quote["total"]},
        ).json()
        self.client.post(
            f"/api/printing-options/{option_id}",
            data={"label": "Print 8x10", "unit_price": "30", "active": "1", "sort_order": "10"},
        )
        saved = self.client.get(f"/api/orders/{created['order_id']}").json()["order"]["payload"]
        snapshot = saved["selected"]["addons"]["printing"]
        self.assertEqual(snapshot["id"], option_id)
        self.assertEqual(snapshot["label"], "Print 8x10")
        self.assertEqual(snapshot["unit_price"], 20.0)
        self.assertEqual(snapshot["count"], 1.0)
        self.assertEqual(snapshot["discount_pct"], 0.0)

    def test_quote_uses_explicit_overall_mat_size(self):
        quote = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "8",
                "height_in": "10",
                "mat_border_in": "2",
                "outside_width_in": "10",
                "outside_height_in": "15",
                "moulding_cost_ft": "4",
                "mat_cost_sqft": "2",
            },
        )
        self.assertEqual(quote.status_code, 200)
        payload = quote.json()
        self.assertEqual(payload["selected"]["outside_width_in"], 10)
        self.assertEqual(payload["selected"]["outside_height_in"], 15)
        self.assertAlmostEqual(payload["area_sqft"], (10 * 15) / 144, places=4)
        self.assertAlmostEqual(payload["perimeter_ft"], (2 * (10 + 15)) / 12, places=2)

    def test_quote_rejects_partial_or_undersized_overall_mat_size(self):
        partial = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "8",
                "height_in": "10",
                "outside_width_in": "10",
            },
        )
        self.assertEqual(partial.status_code, 400)
        self.assertIn("outside_width_in and outside_height_in", partial.json()["detail"])

        undersized = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "8",
                "height_in": "10",
                "outside_width_in": "8",
                "outside_height_in": "15",
            },
        )
        self.assertEqual(undersized.status_code, 400)
        self.assertIn("larger than the opening", undersized.json()["detail"])

    def test_explicit_mat_size_export_uses_stored_board_dimensions(self):
        payload = {
            "selected": {
                "subject_width_in": 8,
                "subject_height_in": 10,
                "mat_border_in": 2,
                "outside_width_in": 10,
                "outside_height_in": 15,
                "mats": [
                    {
                        "slot": "top",
                        "item": {"sku": "M1", "name": "White"},
                        "reveal_in": 0,
                    }
                ],
            },
            "design_state": {
                "item_name": "Exact Mat Test",
                "opening_layout": "single",
                "opening_offset_x": 0,
                "opening_offset_y": 0,
            },
        }
        sizes = main_module._form_sizes(payload["selected"])
        self.assertEqual(sizes["board_w"], 10)
        self.assertEqual(sizes["board_h"], 15)
        lines = main_module._order_form_lines(payload, include_production=True)
        self.assertTrue(any("Top Mat: M1 (10 x 15)" in line for line in lines))
        self.assertTrue(any("Top 2.5" in line and "Left 1" in line for line in lines))


    def test_order_saves_design_state_layout(self):
        """Verify diptych layout design state roundtrips through order save/load."""
        imported = self.client.post(
            "/api/catalog/import",
            files={
                "file": (
                    "catalog.csv",
                    "sku,name,category,cost,width_in\nF1,Frame One,moulding,10,1.5\nM1,Top White,mat,3,0\n",
                    "text/csv",
                )
            },
        )
        search = self.client.get("/api/catalog/search")
        by_sku = {item["sku"]: item["id"] for item in search.json()["items"]}

        quote = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "20",
                "height_in": "16",
                "mat_border_in": "2.5",
                "labor_flat": "20",
                "moulding_id": str(by_sku["F1"]),
                "top_mat_id": str(by_sku["M1"]),
            },
        )
        quote_data = quote.json()

        order = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Layout Test",
                "customer_contact": "606-555-0113",
                "payload_json": json.dumps({
                    **quote_data,
                    "design_state": {
                        "opening_layout": "diptych",
                        "opening_spacing": "2.0",
                        "opening_offset_x": "0.5",
                        "opening_offset_y": "-0.25",
                        "opening_balance": "60",
                    },
                }),
                "subtotal": str(quote_data["subtotal"]),
                "tax": str(quote_data["tax"]),
                "total": str(quote_data["total"]),
            },
        )
        order_id = order.json()["order_id"]

        detail = self.client.get(f"/api/orders/{order_id}")
        payload = detail.json()["order"]["payload"]
        design = payload["design_state"]
        self.assertEqual(design["opening_layout"], "diptych")
        self.assertEqual(design["opening_spacing"], "2.0")
        self.assertEqual(design["opening_balance"], "60")

    def test_third_mat_requires_second_mat(self):
        """Verify API rejects third_mat_id when second_mat_id is missing."""
        imported = self.client.post(
            "/api/catalog/import",
            files={
                "file": (
                    "catalog.csv",
                    "sku,name,category,cost,width_in\nF1,Frame One,moulding,10,1.5\nM1,Top White,mat,3,0\nM3,Gold,mat,2.5,0\n",
                    "text/csv",
                )
            },
        )
        search = self.client.get("/api/catalog/search")
        by_sku = {item["sku"]: item["id"] for item in search.json()["items"]}

        bad = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "8",
                "height_in": "10",
                "labor_flat": "20",
                "moulding_id": str(by_sku["F1"]),
                "top_mat_id": str(by_sku["M1"]),
                "third_mat_id": str(by_sku["M3"]),
            },
        )
        self.assertEqual(bad.status_code, 400)
        self.assertIn("third_mat_id requires second_mat_id", bad.json()["detail"])

    def test_catalog_search_supports_category_filter(self):
        """Verify category filter narrows results to one material type."""
        csv_data = (
            "sku,name,category,cost,width_in\n"
            "F1,Frame A,moulding,10,1.5\n"
            "F2,Frame B,moulding,12,2.0\n"
            "M1,Mat A,mat,3,0\n"
            "G1,Glass A,glazing,4,0\n"
        )
        self.client.post(
            "/api/catalog/import",
            files={"file": ("catalog.csv", csv_data, "text/csv")},
        )

        mouldings = self.client.get("/api/catalog/search", params={"category": "moulding"})
        self.assertEqual(len(mouldings.json()["items"]), 2)
        for item in mouldings.json()["items"]:
            self.assertEqual(item["category"], "moulding")

        mats = self.client.get("/api/catalog/search", params={"category": "mat"})
        self.assertEqual(len(mats.json()["items"]), 1)
        self.assertEqual(mats.json()["items"][0]["category"], "mat")

    def test_catalog_item_update_and_search(self):
        """Verify items can be updated via the editor endpoint."""
        csv_data = "sku,name,category,cost,width_in\nF1,Frame A,moulding,10,1.5\n"
        self.client.post(
            "/api/catalog/import",
            files={"file": ("catalog.csv", csv_data, "text/csv")},
        )

        search = self.client.get("/api/catalog/search", params={"q": "Frame A"})
        item_id = search.json()["items"][0]["id"]

        updated = self.client.post(
            f"/api/catalog/items/{item_id}",
            data={
                "sku": "F1-UPD",
                "name": "Frame A Updated",
                "category": "moulding",
                "cost": "12",
                "width_in": "2.0",
                "active": "1",
            },
        )
        self.assertEqual(updated.status_code, 200)

        found = self.client.get("/api/catalog/search", params={"q": "Updated"})
        self.assertEqual(len(found.json()["items"]), 1)
        self.assertEqual(found.json()["items"][0]["sku"], "F1-UPD")
        self.assertEqual(found.json()["items"][0]["width_in"], 2.0)

    def test_image_upload_returns_valid_id(self):
        """Verify image upload stores dimensions and returns image ID."""
        image_bytes = io.BytesIO()
        Image.new("RGB", (200, 300), "blue").save(image_bytes, format="PNG")
        payload = image_bytes.getvalue()

        uploaded = self.client.post(
            "/api/images/upload",
            data={
                "width_in": "8",
                "height_in": "12",
                "ratio_label": "free",
                "crop_json": "{}",
                "rotation_deg": "0",
            },
            files={"file": ("test.png", payload, "image/png")},
        )
        self.assertEqual(uploaded.status_code, 200)
        image_id = uploaded.json()["id"]
        self.assertIsInstance(image_id, int)
        self.assertGreater(image_id, 0)

        images = self.client.get("/api/images")
        self.assertEqual(images.status_code, 200)
        image_rows = images.json()["images"]
        ids = [img["id"] for img in image_rows]
        self.assertIn(image_id, ids)
        row = next(img for img in image_rows if img["id"] == image_id)
        self.assertEqual(row["crop_json"], {})

    def test_image_metadata_update_persists_crop_settings(self):
        image_bytes = io.BytesIO()
        Image.new("RGB", (200, 300), "green").save(image_bytes, format="PNG")
        uploaded = self.client.post(
            "/api/images/upload",
            data={
                "width_in": "8",
                "height_in": "12",
                "ratio_label": "free",
                "crop_json": "{}",
                "rotation_deg": "0",
            },
            files={"file": ("editable.png", image_bytes.getvalue(), "image/png")},
        )
        self.assertEqual(uploaded.status_code, 200)
        image_id = uploaded.json()["id"]
        crop = {"zoom": 1.4, "offset_x": 12, "offset_y": -7, "ratio": 0.8, "ratio_w": 4, "ratio_h": 5}

        updated = self.client.patch(
            f"/api/images/{image_id}",
            data={
                "width_in": "9",
                "height_in": "11",
                "ratio_label": "custom",
                "crop_json": json.dumps(crop),
            },
        )
        self.assertEqual(updated.status_code, 200)
        body = updated.json()
        self.assertEqual(body["width_in"], 9)
        self.assertEqual(body["height_in"], 11)
        self.assertEqual(body["ratio_label"], "custom")
        self.assertEqual(body["crop_json"], crop)

        images = self.client.get("/api/images")
        row = next(img for img in images.json()["images"] if img["id"] == image_id)
        self.assertEqual(row["width_in"], 9)
        self.assertEqual(row["height_in"], 11)
        self.assertEqual(row["ratio_label"], "custom")
        self.assertEqual(row["crop_json"], crop)

    def test_image_metadata_update_rejects_invalid_values(self):
        image_bytes = io.BytesIO()
        Image.new("RGB", (100, 100), "white").save(image_bytes, format="PNG")
        uploaded = self.client.post(
            "/api/images/upload",
            data={
                "width_in": "8",
                "height_in": "10",
                "ratio_label": "free",
                "crop_json": "{}",
                "rotation_deg": "0",
            },
            files={"file": ("bad-edit.png", image_bytes.getvalue(), "image/png")},
        )
        image_id = uploaded.json()["id"]

        invalid_dimensions = self.client.patch(
            f"/api/images/{image_id}",
            data={"width_in": "0", "height_in": "10", "ratio_label": "free", "crop_json": "{}"},
        )
        self.assertEqual(invalid_dimensions.status_code, 400)
        self.assertIn("width_in must be positive", invalid_dimensions.json()["detail"])

        invalid_crop = self.client.patch(
            f"/api/images/{image_id}",
            data={"width_in": "8", "height_in": "10", "ratio_label": "free", "crop_json": "[]"},
        )
        self.assertEqual(invalid_crop.status_code, 400)
        self.assertIn("crop_json must be a JSON object", invalid_crop.json()["detail"])

    def test_customer_search_returns_partial_match(self):
        """Verify customer search matches on partial name."""
        self.client.post(
            "/api/customers",
            data={"name": "Katherine Potter", "contact": "606-555-0114", "notes": "owner"},
        )

        found = self.client.get("/api/customers", params={"q": "Kath"})
        self.assertEqual(found.status_code, 200)
        self.assertEqual(len(found.json()["customers"]), 1)
        self.assertEqual(found.json()["customers"][0]["name"], "Katherine Potter")

        not_found = self.client.get("/api/customers", params={"q": "Zzz"})
        self.assertEqual(len(not_found.json()["customers"]), 0)

    def test_order_status_history_preserves_notes(self):
        """Verify each status transition records its note."""
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "History Test",
                "customer_contact": "606-555-0115",
                "payload_json": json.dumps({"subtotal": 10, "tax": 0.6, "total": 10.6}),
                "subtotal": "10",
                "tax": "0.6",
                "total": "10.6",
            },
        )
        order_id = created.json()["order_id"]

        self.client.post(
            f"/api/orders/{order_id}/status",
            data={"status": "work_order", "note": "customer approved framing", "customer_approved": "1"},
        )
        self.client.post(
            f"/api/orders/{order_id}/status",
            data={"status": "invoice", "note": "picked up and paid", "work_completed": "1"},
        )

        detail = self.client.get(f"/api/orders/{order_id}")
        history = detail.json()["history"]
        notes = {h["status"]: h.get("note", "") for h in history}
        self.assertEqual(notes["work_order"], "customer approved framing")
        self.assertEqual(notes["invoice"], "picked up and paid")

    def test_multi_mat_stack_areas_exceed_single(self):
        """Verify stacked mats produce larger priced area than single mat."""
        csv_data = (
            "sku,name,category,cost,width_in\n"
            "F1,Frame One,moulding,10,1.5\n"
            "M1,White,mat,3,0\n"
            "M2,Black,mat,2.5,0\n"
        )
        self.client.post(
            "/api/catalog/import",
            files={"file": ("catalog.csv", csv_data, "text/csv")},
        )
        search = self.client.get("/api/catalog/search")
        by_sku = {item["sku"]: item["id"] for item in search.json()["items"]}

        single = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "10",
                "height_in": "12",
                "mat_border_in": "2.5",
                "labor_flat": "20",
                "moulding_id": str(by_sku["F1"]),
                "top_mat_id": str(by_sku["M1"]),
            },
        ).json()

        stacked = self.client.post(
            "/api/quotes/calculate",
            data={
                "width_in": "10",
                "height_in": "12",
                "mat_border_in": "2.5",
                "labor_flat": "20",
                "moulding_id": str(by_sku["F1"]),
                "top_mat_id": str(by_sku["M1"]),
                "second_mat_id": str(by_sku["M2"]),
                "second_mat_reveal_in": "0.25",
            },
        ).json()

        stacked_mat_total = stacked["line_items"]["mat"] + stacked["line_items"]["mat_second"]
        self.assertGreater(stacked_mat_total, single["line_items"]["mat"])

    def test_inventory_reconciliation_classifies_matched_discrepant_and_missing_rows(self):
        response = self.client.post(
            "/api/inventory/reconcile",
            json={
                "threshold": 1,
                "shelf_counts": [
                    {"sku": "FRM-100", "name": "Maple Frame", "count": 10},
                    {"name": "Barnwood Mat", "count": 4},
                    {"sku": "ONLY-SHELF", "name": "Shelf Only", "count": 2},
                ],
                "shopify_counts": [
                    {"sku": "frm-100", "name": "Maple Frame", "count": 9},
                    {"name": "Barnwood Mat", "count": 1},
                    {"sku": "ONLY-SHOPIFY", "name": "Shopify Only", "count": 7},
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["threshold"], 1)
        self.assertEqual(payload["summary"], {"matched": 1, "discrepant": 3, "warnings": 0, "total_products": 4})

        matched = payload["matched"]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["product"], "Maple Frame")
        self.assertEqual(matched[0]["delta"], 1)
        self.assertEqual(matched[0]["status"], "matched")

        statuses = {row["product"]: row["status"] for row in payload["discrepancies"]}
        self.assertEqual(statuses["Barnwood Mat"], "discrepant")
        self.assertEqual(statuses["Shelf Only"], "missing_match")
        self.assertEqual(statuses["Shopify Only"], "missing_match")

    def test_inventory_reconciliation_rejects_bad_payloads(self):
        response = self.client.post(
            "/api/inventory/reconcile",
            json={"shelf_counts": {}, "shopify_counts": []},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("must be arrays", response.json()["detail"])

    def test_price_table_mats_glazing_backing(self):
        """Verify price_table pricing works for mats, glazing, and backing."""
        from app.db_admin import init_admin_tables
        from app.pricing import (
            calculate_mat_price,
            calculate_glazing_price,
            calculate_backing_price,
            update_price_rule
        )
        
        # Initialize admin tables to create price_rules and price_table_entries
        init_admin_tables()

        # Update pricing rules to price_table method
        update_price_rule('mat', 'price_table', 1.0, 0.0)
        update_price_rule('glazing', 'price_table', 1.0, 0.0)
        update_price_rule('backing', 'price_table', 1.0, 0.0)

        conn = db.get_connection()
        cur = conn.cursor()

        # Insert price table entries for price code 'PC-TEST'
        price_entries = [
            ('PC-TEST', 20.0, 15.0),
            ('PC-TEST', 40.0, 25.0),
        ]
        cur.executemany(
            "INSERT INTO price_table_entries (price_code, half_perimeter, price) VALUES (?, ?, ?)",
            price_entries
        )

        # Insert items in catalog matching this price code
        cur.execute(
            "INSERT INTO catalog_items (sku, name, category, cost, metadata_json) VALUES "
            "('MAT-PT', 'Test Mat PT', 'mat', 5.0, '{\"price_code\": \"PC-TEST\"}')"
        )
        cur.execute(
            "INSERT INTO catalog_items (sku, name, category, cost, metadata_json) VALUES "
            "('GLZ-PT', 'Test Glazing PT', 'glazing', 4.0, '{\"price_code\": \"PC-TEST\"}')"
        )
        # Note: Bypassing catalog category restriction to insert backing catalog item for pricing.py test
        cur.execute(
            "INSERT INTO catalog_items (sku, name, category, cost, metadata_json) VALUES "
            "('BCK-PT', 'Test Backing PT', 'backing', 3.0, '{\"price_code\": \"PC-TEST\"}')"
        )
        conn.commit()
        conn.close()

        # 1. Test Mat price lookup
        # half_perimeter = 10 + 10 = 20. Should match 20.0 entry -> 15.0
        mat_res1 = calculate_mat_price('MAT-PT', 10.0, 10.0)
        self.assertEqual(mat_res1['price'], 15.0)
        self.assertEqual(mat_res1['method'], 'price_table')
        self.assertEqual(mat_res1['price_code'], 'PC-TEST')

        # half_perimeter = 12 + 10 = 22. Should match 40.0 entry -> 25.0
        mat_res2 = calculate_mat_price('MAT-PT', 12.0, 10.0)
        self.assertEqual(mat_res2['price'], 25.0)

        # half_perimeter = 30 + 20 = 50. Should fallback to largest entry (40.0) -> 25.0
        mat_res3 = calculate_mat_price('MAT-PT', 30.0, 20.0)
        self.assertEqual(mat_res3['price'], 25.0)

        # 2. Test Glazing price lookup
        glz_res1 = calculate_glazing_price('GLZ-PT', 10.0, 10.0)
        self.assertEqual(glz_res1['price'], 15.0)

        # 3. Test Backing price lookup
        bck_res1 = calculate_backing_price('BCK-PT', 10.0, 10.0)
        self.assertEqual(bck_res1['price'], 15.0)

    def test_order_notes_endpoint_and_timeline(self):
        """Verify adding order notes and timeline rendering works."""
        # 1. Create order
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "Notes Timeline Test",
                "customer_contact": "606-555-0116",
                "payload_json": json.dumps({"subtotal": 10, "tax": 0.6, "total": 10.6}),
                "subtotal": "10",
                "tax": "0.6",
                "total": "10.6",
            },
        )
        self.assertEqual(created.status_code, 200)
        order_id = created.json()["order_id"]

        # 2. Add notes
        note_res = self.client.post(
            f"/api/orders/{order_id}/notes",
            data={"note": "Handoff text prepared for contact: 606-555-0116"}
        )
        self.assertEqual(note_res.status_code, 200)
        self.assertEqual(note_res.json()["note"], "Handoff text prepared for contact: 606-555-0116")

        # 3. Add second note
        note_res2 = self.client.post(
            f"/api/orders/{order_id}/notes",
            data={"note": "Email handoff draft opened (mailto link clicked)"}
        )
        self.assertEqual(note_res2.status_code, 200)

        # 4. Retrieve order detail and verify status history/timeline notes
        detail = self.client.get(f"/api/orders/{order_id}")
        self.assertEqual(detail.status_code, 200)
        history = detail.json()["history"]
        
        # Verify notes are saved in order status history with same status (quote)
        history_notes = [h["note"] for h in history if h["status"] == "quote"]
        self.assertIn("Handoff text prepared for contact: 606-555-0116", history_notes)
        self.assertIn("Email handoff draft opened (mailto link clicked)", history_notes)

        # 5. Error conditions
        bad_note = self.client.post(
            f"/api/orders/{order_id}/notes",
            data={"note": "  "}
        )
        self.assertEqual(bad_note.status_code, 400)

        not_found_note = self.client.post(
            "/api/orders/999999/notes",
            data={"note": "valid note"}
        )
        self.assertEqual(not_found_note.status_code, 404)

    def test_pdf_exports_with_boxed_disclaimers(self):
        """Verify PDF generation runs without errors for quote, work_order, and invoice."""
        # Create a mock order with some dummy design details
        created = self.client.post(
            "/api/orders",
            data={
                "customer_name": "PDF Disclaimer Test",
                "customer_contact": "606-555-0117",
                "payload_json": json.dumps(
                    {
                        "subtotal": 100,
                        "tax": 6,
                        "total": 106,
                        "design_state": {"opening_layout": "single"},
                        "selected": {
                            "moulding": {"sku": "M-TEST", "name": "Test Frame"},
                            "mats": [{"slot": "top", "item": {"sku": "MAT-TEST", "name": "Test Mat"}}],
                            "glazing": {"sku": "GLZ-TEST", "name": "Test Glass"},
                            "mat_border_in": 2,
                        },
                        "line_items": {"moulding": 50, "mat": 30, "glazing": 20},
                    }
                ),
                "subtotal": "100",
                "tax": "6",
                "total": "106",
            },
        )
        self.assertEqual(created.status_code, 200)
        order_id = created.json()["order_id"]

        # Export as quote PDF
        quote_pdf = self.client.get(f"/api/orders/{order_id}/export", params={"format": "pdf", "document": "quote"})
        self.assertEqual(quote_pdf.status_code, 200)
        self.assertEqual(quote_pdf.headers["content-type"], "application/pdf")
        self.assertGreater(len(quote_pdf.content), 100)

        # Export as work_order PDF
        wo_pdf = self.client.get(f"/api/orders/{order_id}/export", params={"format": "pdf", "document": "work_order"})
        self.assertEqual(wo_pdf.status_code, 200)
        self.assertEqual(wo_pdf.headers["content-type"], "application/pdf")

        # Export as invoice PDF
        inv_pdf = self.client.get(f"/api/orders/{order_id}/export", params={"format": "pdf", "document": "invoice"})
        self.assertEqual(inv_pdf.status_code, 200)
        self.assertEqual(inv_pdf.headers["content-type"], "application/pdf")


if __name__ == "__main__":
    unittest.main()
