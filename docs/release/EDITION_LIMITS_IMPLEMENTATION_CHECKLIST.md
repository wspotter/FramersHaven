# Edition Limits Implementation Checklist

## 1. Goal

- **Community remains useful**: The Community edition provides a functional framing workstation tool for basic operations including manual catalog entry, standard exports, and manual backups.
- **Paid Workstation removes scale/convenience limits**: The Workstation edition removes all item/quote caps, adds branded templates, accounting export, and Windows-ready packaging.
- **No hosted licensing or DRM for v1**: All enforcement is offline, self-contained, with no external license servers or subscription checks required.

## 2. Current Reality

- [x] Community catalog, saved order/quote, and successful package-import limits are enforced.
- [x] Workstation removes those scale limits and includes local accounting CSV export.
- [x] The active edition and current usage are shown in Admin.
- [x] Current GitHub `main` contains the implemented workflow and tests.
- [ ] Paid Windows distribution, expanded branded templates, and support terms remain release decisions.

## 3. Proposed Community Limits

- [ ] 1 studio profile
- [ ] Up to 50 active catalog items
- [ ] Up to 25 saved quotes/orders
- [ ] Up to 1 successful local catalog package import
- [ ] No accounting CSV export
- [ ] No paid Windows package entitlement
- [ ] Basic/manual branding only
- [ ] Manual catalog entry remains available
- [ ] PDF/JPG exports remain available
- [ ] Manual backups remain available
- [ ] Existing over-limit data remains readable

## 4. Proposed Workstation Features

- [ ] Unlimited active catalog items
- [ ] Unlimited saved quotes/orders
- [ ] Unlimited local catalog package imports
- [ ] Branded document templates
- [ ] Accounting CSV export
- [ ] Windows-ready ZIP/folder package
- [ ] Optional setup/support workflow
- [ ] Future update path, not promised yet

## 5. Implementation Phases

### Edition configuration module
- [ ] Create `app/edition.py` with edition detection logic
- [ ] Add `FRAMERSHAVEN_EDITION` environment variable support
- [ ] Implement `get_edition()` function returning `community` or `workstation`
- [ ] Add fallback to Community for unknown values

### `/api/edition` endpoint
- [ ] Add endpoint in `app/main.py` to return current edition
- [ ] Include feature flags for each gated capability
- [ ] Return edition name and limit values

### Server-side catalog item limit
- [ ] Add count check before new catalog item creation
- [ ] Return appropriate error when limit reached
- [ ] Ensure read operations always succeed for existing data

### Server-side quote/order save limit
- [ ] Add count check before saving new quotes/orders
- [ ] Return appropriate error when limit reached
- [ ] Ensure read operations always succeed for existing data

### Server-side catalog package import limit
- [ ] Track successful imports in database or config
- [ ] Add check before allowing new import
- [ ] Failed imports do not count against limit

### Accounting CSV export gate
- [ ] Check edition before CSV export generation
- [ ] Return appropriate error for Community users
- [ ] Keep export activity local; do not send audit data to external services

### Admin UI edition panel
- [ ] Add edition status display in admin interface
- [ ] Show current usage vs limits
- [ ] Non-editable display for v1

### User-facing limit messages
- [ ] Add toast/snackbar notifications for limit warnings
- [ ] Display appropriate messaging without hard sell
- [ ] Provide clear edition information without requiring an external billing link

### Tests
- [ ] Add edition-related tests in `tests/test_edition.py`
- [ ] Test all limit enforcement scenarios
- [ ] Test fallback behavior
- [ ] Test data retention after limit changes

### Documentation updates
- [ ] Update `README.md` with edition information
- [ ] Update `docs/USER_MANUAL.md` with limit details
- [ ] Update `app/static/help/admin-pricing.html` if exists

## 6. Suggested Files To Change Later

- `app/edition.py` (new)
- `app/main.py`
- `app/db.py`
- `app/static/app.js`
- `app/templates/index.html`
- `app/static/help/admin-pricing.html`
- `docs/USER_MANUAL.md`
- `README.md`
- `tests/test_api.py`
- `tests/test_pricing.py`
- `tests/test_edition.py` (new)

## 7. Error Message Drafts

**catalog item limit reached:**
> "Community edition includes up to 50 active catalog items. This item was not added, and existing catalog data was not changed."

**order/quote limit reached:**
> "Community edition includes up to 25 saved quotes/orders. This quote was not saved, and existing records remain available."

**package import limit reached:**
> "Community edition includes one successful catalog package import. This import was not applied. Failed imports do not count toward the allowance."

**accounting CSV export unavailable in Community:**
> "Accounting CSV export is available in Workstation Edition. Community data remains unchanged."

**unknown edition fallback:**
> "Edition could not be determined. Running in Community mode with default local limits."

## 8. Test Checklist

- [ ] Default edition is Community
- [ ] `FRAMERSHAVEN_EDITION=workstation` can set Workstation
- [ ] Unknown edition falls back to Community
- [ ] Community limit checks trigger appropriately
- [ ] Workstation bypasses all limits
- [ ] Existing over-limit database still boots and reads
- [ ] Failed package imports do not consume allowance
- [ ] Browser smoke tests still pass
- [ ] Private footprint scan still passes

## 9. Human Decisions Still Needed

- [ ] Final Community limits (current values may need adjustment)
- [ ] Whether branding is limited or fully available in Community
- [ ] Exact Workstation distribution method
- [ ] Whether license key exists in later versions
- [ ] Support/update promise for Workstation edition
- [ ] Accounting CSV target format (CSV headers, date format, encoding)

## 10. Out-of-Scope For v1

- [ ] Online license server
- [ ] Subscription enforcement
- [ ] Cloud sync
- [ ] Payment processing
- [ ] Accounting API sync
- [ ] Bundled vendor catalogs
- [ ] Automatic email/SMS sending
