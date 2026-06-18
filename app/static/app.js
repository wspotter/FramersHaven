let lastQuote = null;
let editingOrderId = null;
let editingOrderNumber = '';
let selectedOrderId = null;
let selectedOrderDetail = null;
let selectedImageId = null;
let galleryMode = 'new';
let localPreviewVersion = 0;
let localPreviewPromise = Promise.resolve(null);
let rotatePreviewTimer = null;
let artworkCropper = null;
let activeArtworkCropJson = {};
let selectedCustomerId = null;
let inlineCustomerPreviousId = null;
let selectedMaterials = { moulding: null, topMat: null, secondMat: null, thirdMat: null, glazing: null };
let imagesCache = [];
let customersCache = [];
let ordersCache = [];
let visibleOrdersCache = [];
let orderStage = '';
let orderSortKey = 'created_at';
let orderSortDirection = 'desc';
let orderInspectorReturnFocus = null;
let catalogCache = [];
let adminCatalogCategory = '';
let adminCatalogSortKey = 'sku';
let adminCatalogSortDirection = 'asc';
let adminCatalogRenderLimit = 300;
let adminCatalogEditorReturnFocus = null;
let pricingSettings = null;
let serviceOptionsCache = [];
let editionStatusCache = null;
let customerSearchTimer = null;
let orderSearchTimer = null;
let designSearchTimer = null;
const previewImageCache = new Map();
const mouldingTextureCache = new Map();
let activeMatSlot = 'topMat';
let selectedCatalogItemId = null;
let handoffCache = null;
let previewedOrderDocument = null;
const catalogDrawerState = { kind: 'mat', slot: 'topMat' };
const mockupInteraction = { type: null, scale: 1, handle: null, positionBox: null };
let pendingOpeningArtworkId = null;
const openingArtworkCache = new Map();
const DESIGN_PRESETS = {
  single_mat: {
    label: 'Moulding & Single Mat',
    note: 'Standard single-opening frame with one visible mat.',
    itemName: 'Moulding & Single Mat',
    openingLayout: 'single',
    useSecondMat: false,
    useThirdMat: false,
    clearMoulding: false,
    clearTopMat: false,
  },
  double_mat: {
    label: 'Moulding & Double Mat',
    note: 'Two mat layers with reveal control on the lower layer.',
    itemName: 'Moulding & Double Mat',
    openingLayout: 'single',
    useSecondMat: true,
    useThirdMat: false,
    clearMoulding: false,
    clearTopMat: false,
  },
  fillet: {
    label: 'Moulding, Mat & Fillet',
    note: 'Using the current builder as a practical stand-in for fillet work.',
    itemName: 'Moulding, Mat & Fillet',
    openingLayout: 'single',
    useSecondMat: true,
    useThirdMat: false,
    clearMoulding: false,
    clearTopMat: false,
  },
  liner: {
    label: 'Moulding & Liner',
    note: 'Frame-led beta path for liner-style jobs.',
    itemName: 'Moulding & Liner',
    openingLayout: 'single',
    useSecondMat: false,
    useThirdMat: false,
    clearMoulding: false,
    clearTopMat: true,
  },
  frame_only: {
    label: 'Frame Only',
    note: 'Skip mats and start from a plain framed artwork.',
    itemName: 'Frame Only',
    openingLayout: 'single',
    useSecondMat: false,
    useThirdMat: false,
    clearMoulding: false,
    clearTopMat: true,
  },
  mat_only: {
    label: 'Mat Only',
    note: 'Use mats and openings without an exterior frame.',
    itemName: 'Mat Only',
    openingLayout: 'single',
    useSecondMat: false,
    useThirdMat: false,
    clearMoulding: true,
    clearTopMat: false,
  },
  stretched_canvas: {
    label: 'Stretched Canvas - Mirror Side',
    note: 'Frame-led beta setup for wrapped or mirrored-edge art.',
    itemName: 'Stretched Canvas - Mirror Side',
    openingLayout: 'single',
    useSecondMat: false,
    useThirdMat: false,
    clearMoulding: false,
    clearTopMat: true,
  },
  two_openings: {
    label: 'Frame & Mat - 2 Openings',
    note: 'Launch directly into the current two-opening layout.',
    itemName: 'Frame & Mat - 2 Openings',
    openingLayout: 'diptych',
    useSecondMat: false,
    useThirdMat: false,
    clearMoulding: false,
    clearTopMat: false,
  },
};
let activeDesignPreset = 'single_mat';
let designLauncherExpanded = false;
const PRESET_DEFAULTS = {
  matBorder: 2,
  secondMatReveal: 0.25,
  thirdMatReveal: 0.25,
  openingSpacing: 1.5,
  openingBalance: 50,
  openingOffsetX: 0,
  openingOffsetY: 0,
};
const OPTION_SELECTS = [
  { key: 'backing', selectId: 'optionBacking', priceId: 'priceBacking', countId: 'countBacking' },
  { key: 'mounting', selectId: 'optionMounting', priceId: 'priceMounting', countId: 'countMounting' },
  { key: 'frame_mounting', selectId: 'optionFrameMounting', priceId: 'priceFrameMounting', countId: 'countFrameMounting' },
  { key: 'printing', selectId: 'optionPrinting', priceId: 'pricePrinting', countId: 'countPrinting' },
  { key: 'various', selectId: 'optionVarious', priceId: 'priceVarious', countId: 'countVarious' },
  { key: 'assembly', selectId: 'optionAssembly', priceId: 'priceAssembly', countId: 'countAssembly' },
  { key: 'royalties', selectId: 'optionRoyalties', priceId: 'priceRoyalties', countId: 'countRoyalties' },
  { key: 'custom_1', selectId: 'optionCustom1', priceId: 'priceCustom1', countId: 'countCustom1' },
  { key: 'custom_2', selectId: 'optionCustom2', priceId: 'priceCustom2', countId: 'countCustom2' },
];
const SERVICE_ADMIN_ROWS = [
  ['glazing_reg_glass', 'serviceGlazingRegGlass'],
  ['glazing_anti_reflection_glass', 'serviceGlazingAntiReflectionGlass'],
  ['glazing_acrylic', 'serviceGlazingAcrylic'],
  ['glazing_anti_reflection_acrylic', 'serviceGlazingAntiReflectionAcrylic'],
  ['backing', 'serviceBacking'],
  ['mounting', 'serviceMounting'],
  ['frame_mounting', 'serviceFrameMounting'],
  ['printing', 'servicePrinting'],
  ['various', 'serviceVarious'],
  ['assembly', 'serviceAssembly'],
  ['royalties', 'serviceRoyalties'],
  ['custom_1', 'serviceCustom1'],
  ['custom_2', 'serviceCustom2'],
];
const THEMES = {
  classic: {
    label: 'Classic',
    detail: 'Warm neutral default',
  },
  framershaven: {
    label: 'FramersHaven',
    detail: 'FramersHaven pink, teal, black, and white',
  },
  gallery: {
    label: 'Gallery Neon (Light)',
    detail: 'Premium light mode with pink and teal accents',
  },
};
const DRAWER_RESULT_LIMIT = 500;
const GLAZING_SERVICE_KEYS = new Set(SERVICE_ADMIN_ROWS.slice(0, 4).map(([key]) => key));

const cropState = { img: null, ratio: null };
const adminTextureState = { img: null, bandHeight: 35, bandCenter: 50 };

const tabMeta = {
  design: {
    title: 'Design Desk',
    subtitle: 'Quote, materials, and preview.',
  },
  gallery: {
    title: 'Gallery',
    subtitle: 'Intake, crop, and staged artwork.',
  },
  orders: {
    title: 'Orders / Quotes',
    subtitle: 'Quote history, status, and exports.',
  },
  customers: {
    title: 'Customers',
    subtitle: 'Contacts and repeat jobs.',
  },
  admin: {
    title: 'Catalog Manager',
    subtitle: 'Browse materials first; open utilities when needed.',
  },
};

function show(data) {
  document.getElementById('out').textContent = JSON.stringify(data, null, 2);
}

function setNotice(message, tone = 'success') {
  const notice = document.getElementById('notice');
  const text = String(message || '').trim();
  if (!text || text === 'Not Found') {
    clearNotice();
    return;
  }
  notice.textContent = text;
  notice.className = `notice visible ${tone}`;
}

function clearNotice() {
  const notice = document.getElementById('notice');
  notice.textContent = '';
  notice.className = 'notice';
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.detail || response.statusText || 'Request failed');
  }
  return data;
}

function switchTab(tab, button) {
  if (!tabMeta[tab]) return;
  if (tab !== 'orders') closeOrderInspector({ restoreFocus: false });
  const showSidebar = window.WorkspaceUI?.shouldShowDesignSidebar(tab) ?? tab === 'design';
  document.body.dataset.workspace = tab;
  document.querySelector('.sidebar')?.setAttribute('aria-hidden', String(!showSidebar));
  document.querySelectorAll('.tab-panel').forEach((panel) => {
    panel.classList.toggle('active', panel.id === `tab-${tab}`);
  });

  document.querySelectorAll('[data-tab]').forEach((node) => {
    node.classList.toggle('active', node.dataset.tab === tab);
  });

  if (button) {
    button.classList.add('active');
  }

  document.getElementById('pageTitle').textContent = tabMeta[tab].title;
  document.getElementById('pageSubtitle').textContent = tabMeta[tab].subtitle;
  if (tab === 'admin') loadEditionStatus();
}

function formatCurrency(value) {
  const amount = Number(value || 0);
  return `$${amount.toFixed(2)}`;
}

function formatInches(value) {
  return Number(value || 0).toFixed(2).replace(/\.00$/, '').replace(/(\.\d)0$/, '$1');
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function setFieldDisplay(id, value) {
  const node = document.getElementById(id);
  if (!node) return;
  if ('value' in node) {
    node.value = value;
  } else {
    node.textContent = value;
  }
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function hasCustomerPhone(value) {
  return String(value || '').replace(/\D/g, '').length >= 7;
}

function validateCustomerIdentity(name, phone) {
  if (!String(name || '').trim()) {
    return 'Customer name is required before saving a quote.';
  }
  if (!hasCustomerPhone(phone)) {
    return 'Customer phone number is required before saving a quote.';
  }
  return '';
}

function parseCatalogMetadata(item) {
  try {
    return item?.metadata_json ? JSON.parse(item.metadata_json) : {};
  } catch {
    return {};
  }
}

function formatBoardSize(item, meta = parseCatalogMetadata(item)) {
  const raw = meta.board_size || meta.size;
  if (raw) {
    return String(raw).replace(/\s*x\s*/i, '×').replace(/"?$/, '"');
  }
  if (item?.width_in && item?.height_in) {
    return `${formatInches(item.width_in)}×${formatInches(item.height_in)}"`;
  }
  return '';
}

function formatMatCore(core) {
  const raw = String(core || '').trim();
  if (!raw) return '';
  const normalized = raw.toLowerCase();
  if (normalized.startsWith('wh')) return 'White Core';
  if (normalized.startsWith('bk') || normalized.includes('black')) return 'Black Core';
  if (normalized.includes('cream')) return 'Cream Core';
  return raw.replace(/[_-]+/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

function getMatSlotLabel(slot) {
  if (slot === 'secondMat') return '2nd mat';
  if (slot === 'thirdMat') return '3rd mat';
  return 'Top mat';
}

function catalogCategory(item) {
  return String(item?.category || '').toLowerCase();
}

function catalogText(item, field) {
  return String(item?.[field] || '');
}

function invalidateQuote() {
  if (!lastQuote) return;
  lastQuote = null;
  updateQuoteSummary(null);
}

function isPricedMoulding(item) {
  return Number(item?.cost || 0) > 0;
}

function isSampleMoulding(item) {
  const label = `${item?.sku || ''} ${item?.name || ''}`.toLowerCase();
  return catalogCategory(item).includes('mould') && !isPricedMoulding(item) && /sample|corner set|sample set/.test(label);
}

function hasCatalogPreview(item) {
  return Boolean(item?.preview_url);
}

function compareCatalogBrowseOrder(a, b) {
  const previewDiff = Number(hasCatalogPreview(b)) - Number(hasCatalogPreview(a));
  if (previewDiff) return previewDiff;
  const pricedDiff = Number(isPricedMoulding(b)) - Number(isPricedMoulding(a));
  if (pricedDiff) return pricedDiff;
  const sampleDiff = Number(isSampleMoulding(a)) - Number(isSampleMoulding(b));
  if (sampleDiff) return sampleDiff;
  return `${a.sku}`.localeCompare(`${b.sku}`);
}

function showWorkspaceState() {
  show({
    theme: document.body.dataset.theme || 'classic',
    selectedImageId,
    selectedCustomerId,
    selectedOrderId,
    selectedMaterials,
    selectedCatalogItemId,
    pricingSettings,
    handoffCache,
    lastQuote,
  });
}

function applyTheme(themeName, persist = true) {
  const theme = THEMES[themeName] ? themeName : 'gallery';
  document.body.dataset.theme = theme;
  const select = document.getElementById('themeSelect');
  const status = document.getElementById('themeStatus');
  if (select) {
    select.value = theme;
  }
  if (status) {
    status.textContent = THEMES[theme].detail;
  }
  if (persist) {
    window.localStorage.setItem('framershaven-theme', theme);
  }
}

function onThemeChange(themeName) {
  applyTheme(themeName);
  setNotice(`Theme switched to ${THEMES[themeName]?.label || THEMES.classic.label}.`, 'success');
}

function updatePricingInputs(settings) {
  if (!settings) return;
  pricingSettings = settings;
  document.getElementById('settingTaxRate').value = settings.tax_rate;
  document.getElementById('settingMarkupMoulding').value = settings.markup_moulding;
  document.getElementById('settingMarkupMat').value = settings.markup_mat;
  document.getElementById('settingMarkupGlazing').value = settings.markup_glazing;
  setFieldDisplay('quoteTaxRate', `${(settings.tax_rate * 100).toFixed(2)}%`);
}

function getSelectedMaterial(type) {
  return catalogCache.find((item) => item.id === selectedMaterials[type]) || null;
}

function setActiveMatSlot(type) {
  activeMatSlot = type;
  updateMatSlotState();
  searchCatalog();
}

function activateMatSlot(type) {
  if (type === 'secondMat' && !document.getElementById('useSecondMat')?.checked) {
    document.getElementById('useSecondMat').checked = true;
  }
  if (type === 'thirdMat') {
    if (!document.getElementById('useSecondMat')?.checked) {
      document.getElementById('useSecondMat').checked = true;
    }
    if (!document.getElementById('useThirdMat')?.checked) {
      document.getElementById('useThirdMat').checked = true;
    }
  }
  syncMatLayerUI();
  setActiveMatSlot(type);
  document.getElementById('catalogDrawerSearch')?.focus();
  setNotice('Choose a mat from the drawer.', 'success');
}

function closeCatalogDrawer() {
  const drawer = document.getElementById('catalogDrawer');
  drawer?.classList.add('visible');
  drawer?.setAttribute('aria-hidden', 'false');
  document.getElementById('openingDrawer')?.classList.remove('visible');
  document.getElementById('openingDrawer')?.setAttribute('aria-hidden', 'true');
  document.querySelector('.sidebar')?.classList.add('drawer-active');
  renderCatalogDrawer();
}

function openOpeningDrawer() {
  const catalogDrawer = document.getElementById('catalogDrawer');
  const openingDrawer = document.getElementById('openingDrawer');
  catalogDrawer?.classList.remove('visible');
  catalogDrawer?.setAttribute('aria-hidden', 'true');
  openingDrawer?.classList.add('visible');
  openingDrawer?.setAttribute('aria-hidden', 'false');
  document.querySelector('.sidebar')?.classList.add('drawer-active');
  syncOpeningPositionInputs();
  renderOpeningArtworkPicker();
  document.getElementById('openingOffsetX')?.focus();
}

function getOpeningArtworkTarget() {
  return customOpenings.find((opening) => opening.id === pendingOpeningArtworkId) || null;
}

function getOpeningArtworkLabel(opening) {
  if (!opening) return 'window';
  const index = customOpenings.findIndex((item) => item.id === opening.id);
  return index >= 0 ? `window #${index + 1}` : 'window';
}

function resetOpeningArtworkPickerSearch() {
  const input = document.getElementById('openingArtworkPickerSearch');
  if (input) input.value = '';
  renderOpeningArtworkPicker();
}

function closeOpeningArtworkPicker() {
  pendingOpeningArtworkId = null;
  renderOpeningArtworkPicker();
}

function openOpeningArtworkPicker(openingId) {
  pendingOpeningArtworkId = openingId;
  openOpeningDrawer();
  renderOpeningArtworkPicker();
  const target = getOpeningArtworkTarget();
  setNotice(`Choose a gallery image for ${getOpeningArtworkLabel(target)}.`, 'success');
  window.requestAnimationFrame(() => {
    document.getElementById('openingArtworkPickerSearch')?.focus();
  });
}

function loadImageElement(src) {
  if (!src) return Promise.reject(new Error('Missing image source.'));
  if (openingArtworkCache.has(src)) {
    const cached = openingArtworkCache.get(src);
    if (cached?.complete && cached.naturalWidth) {
      return Promise.resolve(cached);
    }
  }
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      openingArtworkCache.set(src, img);
      resolve(img);
    };
    img.onerror = () => reject(new Error('Could not load gallery image.'));
    img.src = src;
  });
}

async function assignGalleryArtworkToOpening(imageOrId) {
  const image = typeof imageOrId === 'object'
    ? imageOrId
    : imagesCache.find((item) => item.id === Number(imageOrId));
  const opening = getOpeningArtworkTarget();
  if (!opening) {
    setNotice('Pick a window first.', 'error');
    return;
  }
  if (!image) {
    setNotice('Gallery image not found.', 'error');
    return;
  }
  const loaded = await loadImageElement(image.url);
  opening.artworkUrl = image.url;
  opening.artworkImg = loaded;
  opening.artworkImageId = image.id;
  opening.artworkLabel = image.filename;
  pendingOpeningArtworkId = null;
  renderOpeningArtworkPicker();
  syncMultiOpeningsList();
  renderMockup();
  scheduleDesignHistorySnapshot();
  setNotice(`Assigned ${image.filename} to ${getOpeningArtworkLabel(opening)}.`, 'success');
}

function renderOpeningArtworkPicker() {
  const panel = document.getElementById('openingArtworkPicker');
  const root = document.getElementById('openingArtworkPickerResults');
  const status = document.getElementById('openingArtworkPickerStatus');
  if (!panel || !root || !status) return;

  const target = getOpeningArtworkTarget();
  const active = Boolean(target);
  panel.classList.toggle('hidden', !active);
  panel.setAttribute('aria-hidden', active ? 'false' : 'true');
  root.innerHTML = '';

  if (!active) {
    status.textContent = 'Choose an image from the app gallery for a window.';
    return;
  }

  const query = (document.getElementById('openingArtworkPickerSearch')?.value || '').trim().toLowerCase();
  const rows = imagesCache.filter((img) => {
    if (!query) return true;
    return String(img.filename || '').toLowerCase().includes(query)
      || String(img.ratio_label || '').toLowerCase().includes(query)
      || String(img.id || '').includes(query);
  });

  status.textContent = `${getOpeningArtworkLabel(target)} · ${rows.length} gallery image${rows.length === 1 ? '' : 's'} available`;

  if (!rows.length) {
    root.innerHTML = '<div class="item"><strong>No gallery images</strong><span>Upload artwork in Gallery first.</span></div>';
    return;
  }

  rows.slice(0, 18).forEach((image) => {
    const row = document.createElement('div');
    const activeImage = target.artworkImageId === image.id;
    row.className = `item${activeImage ? ' selected' : ''}`;
    row.innerHTML = `
      <img class="opening-artwork-picker-thumb" src="${escapeHtml(image.url)}" alt="" loading="lazy" />
      <div>
        <strong>#${Number(image.id || 0)} ${escapeHtml(image.filename)}</strong>
        <span>${formatInches(image.width_in)} x ${formatInches(image.height_in)} in</span>
        <small>${escapeHtml(image.ratio_label || 'free')} · ${escapeHtml(image.created_at)}</small>
      </div>
      <button type="button" class="secondary opening-artwork-picker-cta">${activeImage ? 'Current' : 'Use'}</button>
    `;
    const button = row.querySelector('button');
    button.disabled = activeImage;
    button.onclick = (event) => {
      event.stopPropagation();
      assignGalleryArtworkToOpening(image).catch((error) => setNotice(error.message, 'error'));
    };
    row.onclick = () => assignGalleryArtworkToOpening(image).catch((error) => setNotice(error.message, 'error'));
    root.appendChild(row);
  });
}

async function ensureCatalogCache(forceRefresh = false) {
  if (!forceRefresh && catalogCache.length) {
    return catalogCache;
  }
  const data = await fetchJson('/api/catalog/search?q=&limit=0');
  catalogCache = [...data.items];
  show(data);
  return catalogCache;
}

function resetCatalogDrawerSearch() {
  const input = document.getElementById('catalogDrawerSearch');
  if (input) input.value = '';
  renderCatalogDrawer();
}

function renderCatalogDrawer() {
  const title = document.getElementById('catalogDrawerTitle');
  const slot = document.getElementById('catalogDrawerSlot');
  const count = document.getElementById('catalogDrawerCount');
  const root = document.getElementById('catalogDrawerResults');
  if (!title || !root) return;

  const query = (document.getElementById('catalogDrawerSearch')?.value || '').trim().toLowerCase();
  const isMoulding = catalogDrawerState.kind === 'moulding';
  const rows = catalogCache.filter((item) => {
    if (catalogDrawerState.kind === 'moulding') {
      return catalogCategory(item).includes('mould');
    }
    return catalogCategory(item).includes('mat');
  }).filter((item) => {
    if (!query) return true;
    return catalogText(item, 'sku').toLowerCase().includes(query)
      || catalogText(item, 'name').toLowerCase().includes(query)
      || catalogText(item, 'vendor').toLowerCase().includes(query);
  }).sort((a, b) => {
    if (!isMoulding) {
      const photoDiff = Number(hasCatalogPreview(b)) - Number(hasCatalogPreview(a));
      if (photoDiff) return photoDiff;
      return catalogText(a, 'sku').localeCompare(catalogText(b, 'sku'), undefined, { numeric: true, sensitivity: 'base' });
    }
    return compareCatalogBrowseOrder(a, b);
  });

  const activeLabel = isMoulding ? 'Exterior frame' : getMatSlotLabel(catalogDrawerState.slot);
  title.textContent = isMoulding ? 'Select Moulding' : `Select ${activeLabel}`;
  if (slot) {
    slot.textContent = activeLabel;
  }
  if (count) {
    const capText = rows.length > DRAWER_RESULT_LIMIT ? ` · showing first ${DRAWER_RESULT_LIMIT}` : '';
    count.textContent = `${rows.length} match${rows.length === 1 ? '' : 'es'}${query ? ` for "${query}"` : ''}${capText}`;
  }
  root.innerHTML = '';
  if (!rows.length) {
    root.innerHTML = '<div class="material-results-empty">No matches</div>';
    return;
  }

  rows.slice(0, DRAWER_RESULT_LIMIT).forEach((item) => {
    const div = document.createElement('div');
    const selectedId = isMoulding ? selectedMaterials.moulding : selectedMaterials[catalogDrawerState.slot];
    div.className = `catalog-result${selectedId === item.id ? ' selected' : ''}`;
    div.tabIndex = 0;
    const sampleMoulding = isMoulding && isSampleMoulding(item);
    if (sampleMoulding) {
      div.classList.add('sample');
    }
    let detail;
    if (isMoulding) {
      const parts = [];
      if (item.vendor) parts.push(item.vendor);
      if (item.width_in) parts.push(`W: ${formatInches(item.width_in)}"`);
      if (item.height_in) parts.push(`H: ${formatInches(item.height_in)}"`);
      if (item.rabbet_in) parts.push(`R: ${formatInches(item.rabbet_in)}"`);
      if (sampleMoulding) parts.push('Sample / no price');
      if (!item.preview_url) parts.push('No photo');
      detail = parts.join(' · ');
    } else {
      const parts = [];
      if (item.vendor) parts.push(item.vendor);
      const meta = parseCatalogMetadata(item);
      const boardSize = formatBoardSize(item, meta);
      if (boardSize) parts.push(`${boardSize} board`);
      const coreLabel = formatMatCore(meta.core);
      if (coreLabel) parts.push(coreLabel);
      if (meta.thickness) parts.push(`${formatInches(meta.thickness)} ply`);
      detail = parts.join(' · ');
    }
    const costStr = item.cost ? ` · ${formatCurrency(item.cost)}` : '';
    const sampleBadge = sampleMoulding ? '<span class="catalog-result-flag">Sample set</span>' : '';
    const noPhotoBadge = !item.preview_url ? '<span class="catalog-result-flag">No photo</span>' : '';
    const swatchColor = isMoulding ? inferMouldingColors(item)[1] : inferMatColor(item, 0);
    const thumb = item.preview_url
      ? `<img class="catalog-result-thumb" src="${escapeHtml(item.preview_url)}" alt="" loading="lazy" />`
      : `<span class="catalog-result-swatch" style="background:${escapeHtml(swatchColor)}"></span>`;
    div.innerHTML = `
      ${thumb}
      <div class="catalog-result-main">
        <strong>${escapeHtml(item.sku)}</strong>
        <span>${escapeHtml(item.name)}</span>
        <small>${escapeHtml(detail)}${escapeHtml(costStr)}</small>
        ${sampleBadge}
        ${noPhotoBadge}
      </div>
    `;
    const selectItem = () => {
      if (catalogDrawerState.kind === 'moulding') {
        selectedMaterials.moulding = item.id;
      } else {
        selectedMaterials[catalogDrawerState.slot] = item.id;
      }
      invalidateQuote();
      updateSelectionSummary();
      searchCatalog();
      renderCatalogDrawer();
      if (sampleMoulding) {
        setNotice('Sample-set moulding selected. Quotes will show $0 until you choose a priced profile.', 'error');
      } else {
        setNotice(`${activeLabel} selected. Recalculate quote before saving.`, 'success');
      }
    };
    div.onclick = selectItem;
    div.onkeydown = (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        selectItem();
      }
    };
    root.appendChild(div);
  });
}

async function openCatalogDrawer(kind, slot = 'topMat') {
  if (kind === 'mat') {
    activateMatSlot(slot);
  }
  catalogDrawerState.kind = kind;
  catalogDrawerState.slot = slot;
  await ensureCatalogCache();
  const drawer = document.getElementById('catalogDrawer');
  document.getElementById('openingDrawer')?.classList.remove('visible');
  document.getElementById('openingDrawer')?.setAttribute('aria-hidden', 'true');
  drawer?.classList.add('visible');
  drawer?.setAttribute('aria-hidden', 'false');
  document.querySelector('.sidebar')?.classList.add('drawer-active');
  renderCatalogDrawer();
  document.getElementById('catalogDrawerSearch')?.focus();
}

function syncDesignLauncherState() {
  const panel = document.getElementById('designHomePanel');
  const toggle = document.getElementById('designLauncherToggle');
  if (!panel || !toggle) return;
  panel.classList.toggle('compact', !designLauncherExpanded);
  toggle.textContent = designLauncherExpanded ? 'Collapse Launcher' : 'Expand Launcher';
}

function toggleDesignLauncher() {
  designLauncherExpanded = !designLauncherExpanded;
  syncDesignLauncherState();
}

function getActivePreset() {
  return DESIGN_PRESETS[activeDesignPreset] || DESIGN_PRESETS.single_mat;
}

function updatePresetUI() {
  const preset = getActivePreset();
  document.querySelectorAll('[data-preset]').forEach((node) => {
    node.classList.toggle('active', node.dataset.preset === activeDesignPreset);
  });
  setFieldDisplay('activePresetLabel', preset.label);
  setFieldDisplay('activePresetNote', preset.note);
  setFieldDisplay('designHomeStatusTitle', preset.label);
  setFieldDisplay(
    'designHomeStatusBody',
    selectedImageId
      ? 'Preset loaded. The builder below is ready with the current artwork and quote state.'
      : 'Preset loaded. Bring in artwork from Gallery or keep building in measurement view.',
  );
  setFieldDisplay(
    'designHomeStatusMeta',
    `${preset.itemName} · ${preset.openingLayout === 'diptych' ? '2 openings' : 'single opening'}`,
  );
  syncDesignLauncherState();
}

function scrollDesignBuilderIntoView() {
  document.getElementById('designWorkspace')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function browseActiveMatSlot() {
  openCatalogDrawer('mat', activeMatSlot);
}

function openDesignPreset(key) {
  const preset = DESIGN_PRESETS[key];
  if (!preset) return;
  activeDesignPreset = key;
  const openingLayout = document.getElementById('openingLayout');
  const secondToggle = document.getElementById('useSecondMat');
  const thirdToggle = document.getElementById('useThirdMat');
  if (openingLayout) openingLayout.value = preset.openingLayout;
  if (secondToggle) secondToggle.checked = preset.useSecondMat;
  if (thirdToggle) thirdToggle.checked = preset.useThirdMat;
  setFieldDisplay('matBorder', PRESET_DEFAULTS.matBorder);
  setFieldDisplay('secondMatReveal', PRESET_DEFAULTS.secondMatReveal);
  setFieldDisplay('thirdMatReveal', PRESET_DEFAULTS.thirdMatReveal);
  setFieldDisplay('openingSpacing', PRESET_DEFAULTS.openingSpacing);
  setFieldDisplay('openingBalance', PRESET_DEFAULTS.openingBalance);
  setFieldDisplay('openingOffsetX', PRESET_DEFAULTS.openingOffsetX);
  setFieldDisplay('openingOffsetY', PRESET_DEFAULTS.openingOffsetY);
  if (preset.clearMoulding) {
    selectedMaterials.moulding = null;
  }
  if (preset.clearTopMat) {
    selectedMaterials.topMat = null;
    selectedMaterials.secondMat = null;
    selectedMaterials.thirdMat = null;
  }
  if (!preset.useSecondMat) {
    selectedMaterials.secondMat = null;
    selectedMaterials.thirdMat = null;
  } else if (!preset.useThirdMat) {
    selectedMaterials.thirdMat = null;
  }
  activeMatSlot = 'topMat';
  lastQuote = null;
  syncMatLayerUI();
  syncOpeningPositionInputs();
  updateQuoteSummary(null);
  updatePresetUI();
  updateSelectionSummary();
  renderMockup();
  scrollDesignBuilderIntoView();
  designLauncherExpanded = false;
  syncDesignLauncherState();
  setNotice(`${preset.label} preset loaded.`, 'success');
}

function updateMatSlotState() {
  [
    ['topMatSlot', 'topMat'],
    ['secondMatCard', 'secondMat'],
    ['thirdMatCard', 'thirdMat'],
  ].forEach(([id, slot]) => {
    const node = document.getElementById(id);
    if (!node) return;
    const item = getSelectedMaterial(slot);
    node.classList.remove('active');
    node.classList.toggle('has-selection', Boolean(item));
    node.querySelectorAll('.slot-active-badge, .slot-selected-badge').forEach((badge) => badge.remove());
    node.querySelector('.material-slot-preview')?.remove();
    if (item) {
      const selectedBadge = document.createElement('span');
      selectedBadge.className = 'slot-selected-badge';
      selectedBadge.textContent = 'set';
      node.querySelector('.material-slot-title')?.appendChild(selectedBadge);
      const preview = document.createElement(item.preview_url ? 'img' : 'span');
      preview.className = 'material-slot-preview';
      preview.title = item.preview_url ? `${item.sku} preview` : `${item.sku} color swatch`;
      if (item.preview_url) {
        preview.src = item.preview_url;
        preview.alt = '';
        preview.loading = 'lazy';
      } else {
        preview.style.background = inferMatColor(item, slot === 'topMat' ? 0 : slot === 'secondMat' ? 1 : 2);
      }
      node.querySelector('.material-slot-head')?.prepend(preview);
    }
  });
  const activeId = activeMatSlot === 'topMat'
    ? 'topMatSlot'
    : activeMatSlot === 'secondMat'
      ? 'secondMatCard'
      : 'thirdMatCard';
  const activeNode = document.getElementById(activeId);
  if (activeNode) {
    activeNode.classList.add('active');
    if (!activeNode.querySelector('.slot-active-badge')) {
      const badge = document.createElement('span');
      badge.className = 'slot-active-badge';
      badge.textContent = 'active';
      activeNode.querySelector('.material-slot-title')?.appendChild(badge);
    }
  }
}

function updateMouldingSlotState() {
  const node = document.querySelector('.material-slot[data-slot="moulding"]');
  if (!node) return;
  const item = getSelectedMaterial('moulding');
  node.classList.toggle('has-selection', Boolean(item));
  node.querySelector('.material-slot-preview')?.remove();
  if (!item) return;
  const preview = document.createElement(item.preview_url ? 'img' : 'span');
  preview.className = 'material-slot-preview';
  preview.title = item.preview_url ? `${item.sku} preview` : `${item.sku} color swatch`;
  if (item.preview_url) {
    preview.src = item.preview_url;
    preview.alt = '';
    preview.loading = 'lazy';
  } else {
    preview.style.background = inferMouldingColors(item)[1];
  }
  node.querySelector('.material-slot-head')?.prepend(preview);
}

function syncGlazingSelection() {
  selectedMaterials.glazing = null;
  invalidateQuote();
  updateSelectionSummary();
}

function getSelectedMatLayers() {
  const layers = [];
  const topMat = getSelectedMaterial('topMat');
  const secondMat = getSelectedMaterial('secondMat');
  const thirdMat = getSelectedMaterial('thirdMat');

  if (topMat) {
    layers.push({ slot: 'top', item: topMat, reveal_in: 0 });
  }
  if (secondMat && document.getElementById('useSecondMat')?.checked) {
    layers.push({
      slot: 'second',
      item: secondMat,
      reveal_in: Number(document.getElementById('secondMatReveal')?.value || 0.25),
    });
  }
  if (thirdMat && document.getElementById('useThirdMat')?.checked) {
    layers.push({
      slot: 'third',
      item: thirdMat,
      reveal_in: Number(document.getElementById('thirdMatReveal')?.value || 0.25),
    });
  }
  return layers;
}

function getEffectiveOpeningOffsets() {
  const matBorder = Number(document.getElementById('matBorder')?.value || 2);
  const offsetX = clamp(Number(document.getElementById('openingOffsetX')?.value || 0), -matBorder, matBorder);
  const offsetY = clamp(Number(document.getElementById('openingOffsetY')?.value || 0), -matBorder, matBorder);
  return { offsetX, offsetY, matBorder };
}

function syncOpeningPositionInputs(sourceId = '') {
  const openingLayout = document.getElementById('openingLayout')?.value || 'single';
  document.querySelector('.design-builder-card')?.classList.toggle('single-opening', openingLayout !== 'diptych');
  document.getElementById('openingDrawer')?.classList.toggle('single-opening', openingLayout !== 'diptych');
  const { offsetX, offsetY, matBorder } = getEffectiveOpeningOffsets();
  const spacingInput = document.getElementById('openingSpacing');
  const balanceInput = document.getElementById('openingBalance');
  const offsetXInput = document.getElementById('openingOffsetX');
  const offsetYInput = document.getElementById('openingOffsetY');
  const spacingValue = document.getElementById('openingSpacingValue');
  const balanceValue = document.getElementById('openingBalanceValue');
  const offsetXValue = document.getElementById('openingOffsetXValue');
  const offsetYValue = document.getElementById('openingOffsetYValue');
  if (offsetXInput) {
    offsetXInput.min = String(-matBorder);
    offsetXInput.max = String(matBorder);
    offsetXInput.value = offsetX.toFixed(2);
  }
  if (offsetYInput) {
    offsetYInput.min = String(-matBorder);
    offsetYInput.max = String(matBorder);
    offsetYInput.value = offsetY.toFixed(2);
  }
  if (spacingValue && spacingInput) {
    spacingValue.textContent = `${Number(spacingInput.value || 1.5).toFixed(2)} in`;
  }
  if (balanceValue && balanceInput) {
    balanceValue.textContent = `${Number(balanceInput.value || 50).toFixed(0)}%`;
  }
  if (offsetXValue) {
    offsetXValue.textContent = `${offsetX.toFixed(2)} in`;
  }
  if (offsetYValue) {
    offsetYValue.textContent = `${offsetY.toFixed(2)} in`;
  }
}

function syncMatLayerUI() {
  const secondEnabled = document.getElementById('useSecondMat')?.checked;
  const thirdToggle = document.getElementById('useThirdMat');
  const thirdEnabled = thirdToggle?.checked;
  const secondCard = document.getElementById('secondMatCard');
  const thirdCard = document.getElementById('thirdMatCard');

  if (secondCard) {
    secondCard.classList.toggle('hidden', !secondEnabled);
  }

  if (!secondEnabled && thirdToggle) {
    thirdToggle.checked = false;
    selectedMaterials.secondMat = null;
    selectedMaterials.thirdMat = null;
  }

  if (thirdToggle) {
    thirdToggle.disabled = !secondEnabled;
  }
  if (thirdCard) {
    thirdCard.classList.toggle('hidden', !secondEnabled || !thirdEnabled);
  }

  if ((!secondEnabled || !thirdEnabled) && thirdCard) {
    selectedMaterials.thirdMat = thirdEnabled && secondEnabled ? selectedMaterials.thirdMat : null;
  }
  if ((!secondEnabled && activeMatSlot === 'secondMat') || (!thirdEnabled && activeMatSlot === 'thirdMat')) {
    activeMatSlot = 'topMat';
  }
  updateMatSlotState();
}

function toggleMatLayer(layer) {
  if (layer === 'third' && !document.getElementById('useSecondMat')?.checked) {
    document.getElementById('useThirdMat').checked = false;
  }
  invalidateQuote();
  syncMatLayerUI();
  searchCatalog();
  updateSelectionSummary();
}

function clearMaterialSelection(type) {
  selectedMaterials[type] = null;
  invalidateQuote();
  if (type === 'topMat') {
    document.getElementById('useSecondMat').checked = false;
    document.getElementById('useThirdMat').checked = false;
    selectedMaterials.secondMat = null;
    selectedMaterials.thirdMat = null;
  }
  if (type === 'secondMat') {
    document.getElementById('useThirdMat').checked = false;
    selectedMaterials.thirdMat = null;
  }
  if (activeMatSlot === 'thirdMat' && !document.getElementById('useThirdMat')?.checked) {
    activeMatSlot = 'topMat';
  }
  syncMatLayerUI();
  searchCatalog();
  updateSelectionSummary();
  scheduleDesignHistorySnapshot();
}

function resetOpeningPosition() {
  document.getElementById('openingOffsetX').value = '0';
  document.getElementById('openingOffsetY').value = '0';
  syncOpeningPositionInputs();
  updateSelectionSummary();
  scheduleDesignHistorySnapshot();
}

function getMatLayerDisplay(layer) {
  const slotLabel = layer.slot === 'top' ? 'Top' : layer.slot === 'second' ? '2nd' : '3rd';
  if (!layer.item) {
    return `${slotLabel}: None`;
  }
  if (layer.slot === 'top') {
    return `${slotLabel}: ${layer.item.sku} · ${layer.item.name}`;
  }
  return `${slotLabel}: ${layer.item.sku} · ${layer.item.name} · reveal ${formatInches(layer.reveal_in)} in`;
}

function inferMatColor(item, index) {
  const label = `${item?.name || ''} ${item?.sku || ''}`.toLowerCase();
  const keywordMap = [
    ['black', '#222222'],
    ['white', '#f7f3ea'],
    ['ivory', '#efe6d4'],
    ['cream', '#eadfc8'],
    ['beige', '#dbcab2'],
    ['tan', '#ccb590'],
    ['gray', '#8d8c8f'],
    ['grey', '#8d8c8f'],
    ['silver', '#c8ccd2'],
    ['blue', '#5d708f'],
    ['green', '#67795d'],
    ['red', '#94545a'],
    ['burgundy', '#7a3540'],
    ['gold', '#b08a3d'],
    ['olive', '#7a7d5e'],
    ['navy', '#2a3d5f'],
    ['burgundy', '#7a3540'],
    ['brown', '#7a5c3e'],
  ];
  const matched = keywordMap.find(([keyword]) => label.includes(keyword));
  if (matched) {
    return matched[1];
  }
  return ['#f6f0e7', '#c8b08a', '#6a5d4f'][index] || '#f6f0e7';
}

function tintHex(hex, amount) {
  const value = hex.replace('#', '');
  const num = Number.parseInt(value, 16);
  const adjust = (channel) => clamp(channel + amount, 0, 255);
  const r = adjust((num >> 16) & 255);
  const g = adjust((num >> 8) & 255);
  const b = adjust(num & 255);
  return `rgb(${r}, ${g}, ${b})`;
}

function inferMouldingColors(item) {
  const label = `${item?.name || ''} ${item?.sku || ''}`.toLowerCase();

  // Metals & metallics
  if (label.includes('gold') || label.includes('champagne')) return ['#c9a063', '#946735', '#5b391d'];
  if (label.includes('bronze') && label.includes('dark')) return ['#5a422e', '#3d2a1a', '#231610'];
  if (label.includes('bronze')) return ['#8b6f47', '#6b5030', '#3b2915'];
  if (label.includes('pewter') || label.includes('nickel') || label.includes('steel')) return ['#8a8d95', '#6b6f78', '#45484f'];
  if (label.includes('brass')) return ['#b5973a', '#8c7428', '#5a4a15'];
  if (label.includes('copper')) return ['#b87333', '#8a5425', '#5c3618'];
  if (label.includes('silver')) return ['#d5d8de', '#9ea5af', '#626975'];
  if (label.includes('pearl') || label.includes('alabaster')) return ['#ece6da', '#d4ccc0', '#b8ae9e'];

  // Dark finishes
  if (label.includes('ebony') || label.includes('onyx')) return ['#2a2420', '#3d362f', '#14120f'];
  if (label.includes('charcoal') || label.includes('slate')) return ['#4a4e52', '#6a6d72', '#2e3136'];
  if (label.includes('black') && label.includes('lacquer')) return ['#1a1a1a', '#0a0a0a', '#333333'];
  if (label.includes('black')) return ['#1f1d1b', '#4a4744', '#0d0c0c'];
  if (label.includes('plum')) return ['#4a2040', '#30142a', '#6a3058'];

  // Light finishes
  if (label.includes('white') && label.includes('gloss')) return ['#f5f2ea', '#e8e3d8', '#d0c9b8'];
  if (label.includes('dove')) return ['#b8b2a8', '#a49e94', '#8a857c'];
  if (label.includes('white')) return ['#f3eee7', '#d4cec6', '#a79f94'];
  if (label.includes('cream') || label.includes('ivory')) return ['#f5edd5', '#e5d9be', '#c7b898'];
  if (label.includes('almond') || label.includes('champagne')) return ['#f0e0c0', '#d8c49a', '#b8a070'];

  // Warm woods
  if (label.includes('walnut') && label.includes('espresso')) return ['#4a3018', '#2d1c0c', '#6b4825'];
  if (label.includes('walnut')) return ['#6d4a2e', '#9f7650', '#392516'];
  if (label.includes('mahogany')) return ['#5c2010', '#8b3018', '#3d1008'];
  if (label.includes('cherry')) return ['#8b3a2a', '#a84838', '#5c2418'];
  if (label.includes('rose')) return ['#b87870', '#985850', '#784038'];
  if (label.includes('sienna')) return ['#a0522d', '#7a3e20', '#5a2a12'];
  if (label.includes('espresso')) return ['#3c2415', '#5a3820', '#201008'];
  if (label.includes('maple') || label.includes('birch')) return ['#ceb08a', '#e5ccad', '#8b6848'];
  if (label.includes('oak')) return ['#b08850', '#8a6830', '#6a5020'];
  if (label.includes('pine') || label.includes('wheat')) return ['#d8c48c', '#bfa870', '#9a8850'];
  if (label.includes('ash')) return ['#c8b89a', '#a89878', '#887a60'];
  if (label.includes('teak')) return ['#8b6520', '#a87d2d', '#5a4210'];
  if (label.includes('wood')) return ['#9f7650', '#6d4a2e', '#392516'];
  if (label.includes('natural')) return ['#c8b088', '#a89068', '#887248'];

  // Cool tones
  if (label.includes('grey') || label.includes('gray')) return ['#8a8a8a', '#6a6a6a', '#4a4a4a'];
  if (label.includes('blue')) return ['#4a6a8a', '#3a5570', '#2a4058'];
  if (label.includes('green') || label.includes('olive')) return ['#6a7a5a', '#4a5a3a', '#3a4828'];
  if (label.includes('teal') || label.includes('aqua')) return ['#3a7a7a', '#2a5a5a', '#1a4040'];

  // Warm accents
  if (label.includes('red')) return ['#8b3030', '#a84040', '#5c1a1a'];
  if (label.includes('rust')) return ['#8b4513', '#a05520', '#5c2d0a'];
  if (label.includes('brown') && label.includes('dark')) return ['#4a3520', '#342210', '#604020'];
  if (label.includes('brown')) return ['#7a5a3a', '#5a3a20', '#9a7a50'];
  if (label.includes('tan')) return ['#c4a882', '#a88a68', '#8a7050'];
  if (label.includes('burgundy') || label.includes('wine')) return ['#5c1020', '#7a1830', '#3d0810'];

  // Textured finishes
  if (label.includes('lacquer') && label.includes('gloss')) return ['#3a3028', '#2a2018', '#4a4038'];
  if (label.includes('lacquer')) return ['#4a4038', '#3a3028', '#2a2018'];
  if (label.includes('linen') || label.includes('canvas')) return ['#d8d0c0', '#c0b8a8', '#a8a090'];

  // Material fallbacks based on style
  const style = parseCatalogMetadata(item).style || '';
  if (style === 'Floater') return ['#5a4a38', '#7a6a58', '#3a2a18'];
  if (style === 'Liner') return ['#c8c0b0', '#a8a090', '#888070'];

  // Generic fallbacks - wider variety than before
  const palettes = [
    ['#85623f', '#b99162', '#43301f'],
    ['#7d6752', '#af9376', '#3f3024'],
    ['#6d5441', '#9b7c5f', '#34281d'],
    ['#85795e', '#bbb090', '#423a2b'],
    ['#6a5a48', '#8a7a68', '#4a3a28'],
    ['#7a6850', '#a08a6a', '#504030'],
    ['#907860', '#b8a080', '#604830'],
    ['#8a7060', '#b09878', '#5a4030'],
  ];
  return palettes[hashString(label) % palettes.length];
}

function getPreviewImage(url) {
  if (!url) return null;
  const existing = previewImageCache.get(url);
  if (existing) {
    return existing.complete && existing.naturalWidth ? existing : null;
  }
  const img = new Image();
  img.onload = () => renderMockup();
  img.src = url;
  previewImageCache.set(url, img);
  return null;
}

function hashString(value) {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = ((hash << 5) - hash) + value.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function getMouldingProfile(item, scale) {
  const faceIn = Math.max(Number(item?.width_in || 0) || 1.5, 0.6);
  const depthIn = Math.max(Number(item?.height_in || 0) || (faceIn * 0.9), faceIn * 0.8);
  const rabbetIn = Math.max(Number(item?.rabbet_in || 0) || (faceIn * 0.16), faceIn * 0.12);
  const facePx = clamp(faceIn * scale, 18, 120);
  const depthRatio = clamp(depthIn / Math.max(faceIn, 0.1), 0.5, 2.5);
  const depthPx = clamp(facePx * depthRatio * 0.58, facePx * 0.66, facePx * 1.3);
  const lipPx = clamp(rabbetIn * scale * 0.9, 5, facePx * 0.38);
  const miterPx = clamp(facePx * 0.30, 5, 18);
  return {
    faceIn,
    depthIn,
    rabbetIn,
    facePx,
    depthPx,
    lipPx,
    miterPx,
  };
}

function drawPathPoints(ctx, points) {
  if (!points.length) return;
  ctx.beginPath();
  ctx.moveTo(points[0][0], points[0][1]);
  for (let i = 1; i < points.length; i += 1) {
    ctx.lineTo(points[i][0], points[i][1]);
  }
  ctx.closePath();
}

function getRailPoints(position, x, y, w, h, profile) {
  const faceRef = Math.min(w, h);
  const miter = Math.round(faceRef);
  switch (position) {
    case 'top':
      return [
        [x, y],
        [x + w, y],
        [x + w - miter, y + h],
        [x + miter, y + h],
      ];
    case 'bottom':
      return [
        [x + miter, y],
        [x + w - miter, y],
        [x + w, y + h],
        [x, y + h],
      ];
    case 'left':
      return [
        [x, y],
        [x + w, y + miter],
        [x + w, y + h - miter],
        [x, y + h],
      ];
    case 'right':
      return [
        [x, y + miter],
        [x + w, y],
        [x + w, y + h],
        [x, y + h - miter],
      ];
    default:
      return [
        [x, y],
        [x + w, y],
        [x + w, y + h],
        [x, y + h],
      ];
  }
}

function extractMouldingSlice(preview, profile) {
  const srcW = preview.naturalWidth || preview.width;
  const srcH = preview.naturalHeight || preview.height;
  if (!srcW || !srcH) return null;

  const aspect = srcW / srcH;
  let cropX = 0;
  let cropY = 0;
  let cropW = srcW;
  let cropH = srcH;

  if (aspect <= 1.6) {
    const faceRatio = clamp(
      profile.faceIn / Math.max(profile.faceIn + profile.depthIn + (profile.rabbetIn * 0.4), 0.01),
      0.42,
      0.78,
    );
    cropH = Math.max(1, Math.round(srcH * faceRatio));
    cropY = Math.round((srcH - cropH) / 2);
  }

  const slice = document.createElement('canvas');
  slice.width = cropW;
  slice.height = cropH;
  const sctx = slice.getContext('2d');
  sctx.drawImage(preview, cropX, cropY, cropW, cropH, 0, 0, cropW, cropH);
  return slice;
}

function rotateAndCropCorner(preview) {
  const srcW = preview.naturalWidth || preview.width;
  const srcH = preview.naturalHeight || preview.height;
  if (!srcW || !srcH) return null;
  const diag = Math.ceil(Math.sqrt(srcW * srcW + srcH * srcH));
  const canvas = document.createElement('canvas');
  canvas.width = diag;
  canvas.height = diag;
  const ctx = canvas.getContext('2d');
  ctx.translate(diag / 2, diag / 2);
  ctx.rotate(-Math.PI / 4);
  ctx.drawImage(preview, -srcW / 2, -srcH / 2);
  ctx.setTransform(1, 0, 0, 1, 0, 0);

  const imgData = ctx.getImageData(0, 0, diag, diag);
  const data = imgData.data;
  let minX = diag;
  let minY = diag;
  let maxX = 0;
  let maxY = 0;
  const whiteThreshold = 245;
  for (let y = 0; y < diag; y += 2) {
    for (let x = 0; x < diag; x += 2) {
      const idx = (y * diag + x) * 4;
      const r = data[idx];
      const g = data[idx + 1];
      const b = data[idx + 2];
      const a = data[idx + 3];
      if (a < 10) continue;
      if (r > whiteThreshold && g > whiteThreshold && b > whiteThreshold) continue;
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
    }
  }
  if (minX >= maxX || minY >= maxY) return canvas;
  const cropW = Math.max(1, maxX - minX + 1);
  const cropH = Math.max(1, maxY - minY + 1);
  const crop = document.createElement('canvas');
  crop.width = cropW;
  crop.height = cropH;
  crop.getContext('2d').drawImage(canvas, minX, minY, cropW, cropH, 0, 0, cropW, cropH);
  return crop;
}

function extractCornerStrip(preview, profile) {
  const rotated = rotateAndCropCorner(preview);
  if (!rotated) return null;
  const srcW = rotated.width;
  const srcH = rotated.height;
  if (!srcW || !srcH) return null;
  const faceRatio = clamp(
    profile.faceIn / Math.max(profile.faceIn + profile.depthIn + (profile.rabbetIn * 0.5), 0.01),
    0.22,
    0.5,
  );
  const stripH = Math.max(1, Math.round(srcH * faceRatio));
  const stripW = Math.max(1, Math.round(srcW * faceRatio));

  const midRatio = 0.5;
  const midWidth = Math.max(1, Math.round(srcW * midRatio));
  const midStart = Math.max(0, Math.round((srcW - midWidth) / 2));
  const bottomTrim = 3;

  const hStrip = document.createElement('canvas');
  hStrip.width = midWidth;
  hStrip.height = Math.max(1, stripH - bottomTrim);
  hStrip.getContext('2d').drawImage(
    rotated,
    midStart,
    0,
    midWidth,
    Math.max(1, stripH - bottomTrim),
    0,
    0,
    midWidth,
    Math.max(1, stripH - bottomTrim),
  );

  return hStrip;
}

function isLikelyMouldingStrip(preview, item = null) {
  const srcW = preview?.naturalWidth || preview?.width || 0;
  const srcH = preview?.naturalHeight || preview?.height || 0;
  if (!srcW || !srcH) return false;
  const url = item?.preview_url || '';
  const aspect = srcW / srcH;
  return url.includes('-strip.') || aspect >= 2.2;
}

function extractMouldingStripRun(preview) {
  const srcW = preview?.naturalWidth || preview?.width || 0;
  const srcH = preview?.naturalHeight || preview?.height || 0;
  if (!srcW || !srcH) return preview;

  const aspect = srcW / srcH;
  if (aspect < 4) return preview;

  const cropX = Math.round(srcW * 0.08);
  const cropW = Math.max(1, Math.round(srcW * 0.76));
  const strip = document.createElement('canvas');
  strip.width = cropW;
  strip.height = srcH;
  const sctx = strip.getContext('2d');
  sctx.imageSmoothingEnabled = true;
  sctx.imageSmoothingQuality = 'high';
  sctx.drawImage(preview, cropX, 0, cropW, srcH, 0, 0, cropW, srcH);
  return strip;
}

function getMouldingRailOrientation(position) {
  return position === 'top' || position === 'bottom' ? 'horizontal' : 'vertical';
}

function createMouldingSideTile(stripSource, position, railFacePx) {
  const srcW = stripSource?.width || 0;
  const srcH = stripSource?.height || 0;
  if (!srcW || !srcH) return null;

  const tileLength = Math.max(1, Math.round(railFacePx * (srcW / srcH)));
  const base = document.createElement('canvas');
  base.width = tileLength;
  base.height = railFacePx;
  const bctx = base.getContext('2d');
  bctx.imageSmoothingEnabled = true;
  bctx.imageSmoothingQuality = 'high';
  bctx.drawImage(stripSource, 0, 0, srcW, srcH, 0, 0, tileLength, railFacePx);

  if (position === 'top') {
    return base;
  }

  const vertical = position === 'left' || position === 'right';
  const tile = document.createElement('canvas');
  tile.width = vertical ? railFacePx : tileLength;
  tile.height = vertical ? tileLength : railFacePx;
  const tctx = tile.getContext('2d');
  tctx.imageSmoothingEnabled = true;
  tctx.imageSmoothingQuality = 'high';

  if (position === 'bottom') {
    tctx.translate(tileLength, railFacePx);
    tctx.rotate(Math.PI);
  } else if (position === 'right') {
    tctx.translate(railFacePx, 0);
    tctx.rotate(Math.PI / 2);
  } else {
    tctx.translate(0, tileLength);
    tctx.rotate(-Math.PI / 2);
  }
  tctx.drawImage(base, 0, 0);
  return tile;
}

function paintMouldingStripRail(ctx, position, x, y, w, h, stripSource) {
  const srcW = stripSource?.width || 0;
  const srcH = stripSource?.height || 0;
  if (!srcW || !srcH) return false;

  const orientation = getMouldingRailOrientation(position);
  const facePx = orientation === 'horizontal' ? h : w;
  const railLength = orientation === 'horizontal' ? w : h;
  const drawScale = facePx / srcH;
  const tileW = srcW * drawScale;

  const drawRun = () => {
    if (tileW >= railLength) {
      ctx.drawImage(stripSource, -(tileW - railLength) / 2, 0, tileW, facePx);
      return;
    }
    let offset = 0;
    while (offset < railLength) {
      ctx.drawImage(stripSource, offset, 0, tileW, facePx);
      offset += tileW;
    }
  };

  ctx.save();
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';

  if (position === 'top') {
    ctx.translate(x, y);
    drawRun();
  } else if (position === 'bottom') {
    ctx.translate(x + w, y + facePx);
    ctx.rotate(Math.PI);
    drawRun();
  } else if (position === 'right') {
    ctx.translate(x + facePx, y);
    ctx.rotate(Math.PI / 2);
    drawRun();
  } else {
    ctx.translate(x, y + h);
    ctx.rotate(-Math.PI / 2);
    drawRun();
  }

  ctx.restore();
  return true;
}

function paintMouldingPlaceholderRail(ctx, position, x, y, w, h, label = 'NO IMAGE') {
  const orientation = getMouldingRailOrientation(position);
  ctx.save();
  ctx.fillStyle = '#eef2f6';
  ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = 'rgba(32, 71, 79, 0.24)';
  ctx.lineWidth = 1;
  ctx.setLineDash([6, 4]);
  ctx.strokeRect(x + 0.5, y + 0.5, Math.max(1, w - 1), Math.max(1, h - 1));
  ctx.setLineDash([]);
  ctx.fillStyle = 'rgba(32, 71, 79, 0.58)';
  ctx.font = 'bold 10px Georgia';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  if (orientation === 'horizontal') {
    ctx.fillText(label, x + (w / 2), y + (h / 2));
  } else {
    ctx.translate(x + (w / 2), y + (h / 2));
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(label, 0, 0);
  }
  ctx.restore();
}

function paintRepeatedMouldingTile(ctx, canvas, tile, position) {
  if (!tile) return;
  const orientation = getMouldingRailOrientation(position);
  if (orientation === 'horizontal') {
    let drawn = 0;
    while (drawn < canvas.width) {
      ctx.drawImage(tile, drawn, 0);
      drawn += tile.width;
    }
    return;
  }

  let drawn = 0;
  while (drawn < canvas.height) {
    ctx.drawImage(tile, 0, drawn);
    drawn += tile.height;
  }
}

function createMouldingTexture(item, position, profile, preview) {
  const orientation = getMouldingRailOrientation(position);
  const previewKey = preview ? (item?.preview_url || item?.sku || item?.name || 'preview') : 'fallback';
  const sourceMode = preview && isLikelyMouldingStrip(preview, item) ? 'photo-strip' : 'derived-strip';
  const cacheKey = `${previewKey}:${position}:${sourceMode}:${Math.round(profile.facePx)}:${Math.round(profile.depthPx)}:${Math.round(profile.lipPx)}`;
  const existing = mouldingTextureCache.get(cacheKey);
  if (existing) {
    return existing;
  }

  const canvas = document.createElement('canvas');
  const railFacePx = Math.round(profile.facePx);

  canvas.width = orientation === 'horizontal' ? 320 : railFacePx;
  canvas.height = orientation === 'horizontal' ? railFacePx : 320;
  const ctx = canvas.getContext('2d');

  if (preview) {
    const isPreCroppedStrip = isLikelyMouldingStrip(preview, item);
    const stripSource = isPreCroppedStrip
      ? extractMouldingStripRun(preview)
      : (extractCornerStrip(preview, profile) || extractMouldingSlice(preview, profile));
    const srcW = stripSource?.width || 0;
    const srcH = stripSource?.height || 0;
    if (srcW > 0 && srcH > 0 && stripSource) {
      ctx.save();
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      const tile = createMouldingSideTile(stripSource, position, railFacePx);
      paintRepeatedMouldingTile(ctx, canvas, tile, position);
      ctx.restore();
    } else {
      _drawProceduralTexture(ctx, canvas, item, orientation, profile);
    }
  } else {
    _drawProceduralTexture(ctx, canvas, item, orientation, profile);
  }

  mouldingTextureCache.set(cacheKey, canvas);
  return canvas;
}

function _drawProceduralTexture(ctx, canvas, item, orientation, profile) {
  const [light, mid, dark] = inferMouldingColors(item);
  const seed = hashString(`${item?.sku || item?.name || ''}:${canvas.width}:${canvas.height}`);

  // Base gradient — three-stop for richer depth
  const baseGradient = orientation === 'horizontal'
    ? ctx.createLinearGradient(0, 0, 0, canvas.height)
    : ctx.createLinearGradient(0, 0, canvas.width, 0);
  baseGradient.addColorStop(0, tintHex(light, 14));
  baseGradient.addColorStop(0.35, mid);
  baseGradient.addColorStop(1, tintHex(dark, -12));
  ctx.fillStyle = baseGradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Fine grain layer — dense, subtle lines
  ctx.save();
  ctx.globalAlpha = 0.35;
  const fineCount = 12 + (seed % 6);
  const fineStep = orientation === 'horizontal'
    ? canvas.height / (fineCount + 1)
    : canvas.width / (fineCount + 1);
  for (let i = 1; i <= fineCount; i += 1) {
    const offset = fineStep * i;
    const wobble = ((seed % 5) + 1) * 0.3;
    ctx.strokeStyle = i % 3 === 0 ? 'rgba(0,0,0,0.12)' : 'rgba(255,255,255,0.08)';
    ctx.lineWidth = 0.5 + (seed % 3) * 0.2;
    ctx.beginPath();
    if (orientation === 'horizontal') {
      ctx.moveTo(0, offset - wobble);
      ctx.bezierCurveTo(canvas.width * 0.15, offset + wobble * 0.6, canvas.width * 0.55, offset - wobble * 0.4, canvas.width, offset + wobble * 0.8);
    } else {
      ctx.moveTo(offset - wobble, 0);
      ctx.bezierCurveTo(offset + wobble * 0.6, canvas.height * 0.15, offset - wobble * 0.4, canvas.height * 0.55, offset + wobble * 0.8, canvas.height);
    }
    ctx.stroke();
  }
  ctx.restore();

  // Coarse grain layer — fewer, bolder lines
  ctx.save();
  ctx.globalAlpha = 0.45;
  const coarseCount = 3 + (seed % 3);
  const coarseStep = orientation === 'horizontal'
    ? canvas.height / (coarseCount + 1)
    : canvas.width / (coarseCount + 1);
  for (let i = 1; i <= coarseCount; i += 1) {
    const offset = coarseStep * i + (seed % 5);
    const wobble = ((seed % 9) + 3) * 0.7;
    ctx.strokeStyle = 'rgba(0,0,0,0.18)';
    ctx.lineWidth = 1.5 + (seed % 4) * 0.4;
    ctx.beginPath();
    if (orientation === 'horizontal') {
      ctx.moveTo(0, offset - wobble);
      ctx.bezierCurveTo(canvas.width * 0.28, offset + wobble * 0.5, canvas.width * 0.68, offset - wobble * 0.3, canvas.width, offset + wobble * 0.7);
    } else {
      ctx.moveTo(offset - wobble, 0);
      ctx.bezierCurveTo(offset + wobble * 0.5, canvas.height * 0.28, offset - wobble * 0.3, canvas.height * 0.68, offset + wobble * 0.7, canvas.height);
    }
    ctx.stroke();
  }
  ctx.restore();

  // Subtle knot simulation
  if (seed % 3 === 0) {
    ctx.save();
    ctx.globalAlpha = 0.1;
    const knotX = (seed % 80) + 40;
    const knotY = (seed % 40) + 20;
    const knotRx = 8 + (seed % 6);
    const knotRy = 4 + (seed % 4);
    ctx.fillStyle = dark;
    ctx.beginPath();
    if (orientation === 'horizontal') {
      ctx.ellipse(knotX, knotY, knotRx, knotRy, 0, 0, Math.PI * 2);
    } else {
      ctx.ellipse(knotX, knotY, knotRy, knotRx, 0, 0, Math.PI * 2);
    }
    ctx.fill();
    ctx.strokeStyle = tintHex(dark, -20);
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.restore();
  }

  // 3D bevel
  const bevel = orientation === 'horizontal'
    ? ctx.createLinearGradient(0, 0, 0, canvas.height)
    : ctx.createLinearGradient(0, 0, canvas.width, 0);
  bevel.addColorStop(0, 'rgba(255,255,255,0.30)');
  bevel.addColorStop(0.12, 'rgba(255,255,255,0.08)');
  bevel.addColorStop(0.55, 'rgba(0,0,0,0.03)');
  bevel.addColorStop(0.80, 'rgba(0,0,0,0.08)');
  bevel.addColorStop(1, 'rgba(0,0,0,0.25)');
  ctx.fillStyle = bevel;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Grain pattern
  ctx.save();
  ctx.globalAlpha = 0.4;
  const grainSize = orientation === 'horizontal' ? 2 : 1;
  const grainCount = orientation === 'horizontal' ? canvas.height : canvas.width;
  ctx.lineWidth = 1;
  for (let i = 0; i < grainCount; i += 2) {
    const darkness = (hashString(seed + "_" + i) % 40);
    ctx.strokeStyle = `rgba(0,0,0,${darkness / 255})`;
    ctx.beginPath();
    if (orientation === 'horizontal') {
      ctx.moveTo(0, i);
      ctx.lineTo(canvas.width, i);
    } else {
      ctx.moveTo(i, 0);
      ctx.lineTo(i, canvas.height);
    }
    ctx.stroke();
  }
  ctx.restore();

  // Edge highlights
  ctx.save();
  ctx.globalAlpha = 0.22;
  if (orientation === 'horizontal') {
    ctx.fillStyle = 'rgba(255,255,255,0.40)';
    ctx.fillRect(0, 0, canvas.width, Math.max(1, Math.round(canvas.height * 0.06)));
    ctx.fillStyle = 'rgba(0,0,0,0.28)';
    ctx.fillRect(0, canvas.height - Math.max(1, Math.round(canvas.height * 0.10)), canvas.width, Math.max(1, Math.round(canvas.height * 0.10)));
  } else {
    ctx.fillStyle = 'rgba(255,255,255,0.40)';
    ctx.fillRect(0, 0, Math.max(1, Math.round(canvas.width * 0.06)), canvas.height);
    ctx.fillStyle = 'rgba(0,0,0,0.28)';
    ctx.fillRect(canvas.width - Math.max(1, Math.round(canvas.width * 0.10)), 0, Math.max(1, Math.round(canvas.width * 0.10)), canvas.height);
  }
  ctx.restore();
}

function paintMouldingRail(ctx, position, x, y, w, h, item, profile) {
  const preview = getPreviewImage(item?.preview_url || '');
  const points = getRailPoints(position, x, y, w, h, profile);

  ctx.save();
  drawPathPoints(ctx, points);
  ctx.clip();

  let paintedFromPreview = false;
  if (preview) {
    const stripSource = isLikelyMouldingStrip(preview, item)
      ? extractMouldingStripRun(preview)
      : (extractCornerStrip(preview, profile) || extractMouldingSlice(preview, profile));
    paintedFromPreview = paintMouldingStripRail(ctx, position, x, y, w, h, stripSource);
  }

  if (paintedFromPreview) {
    ctx.save();
    drawPathPoints(ctx, points);
    ctx.strokeStyle = 'rgba(24, 15, 10, 0.18)';
    ctx.lineWidth = Math.max(0.8, profile.facePx * 0.018);
    ctx.stroke();
    ctx.restore();
    ctx.restore();
    return;
  }

  if (!item?.preview_url) {
    paintMouldingPlaceholderRail(ctx, position, x, y, w, h, 'NO IMAGE');
    ctx.restore();
    return;
  }

  paintMouldingPlaceholderRail(ctx, position, x, y, w, h, 'LOADING');
  ctx.restore();
}

function drawFrameMiters(ctx, outerX, outerY, outerW, outerH, profile, photoScale = 1) {
  const face = profile.facePx;
  const inset = clamp(Math.round(face * 0.12), 2, Math.round(face * 0.4));
  const length = clamp(Math.round(face * 0.85), 8, Math.round(face * 1.3));
  ctx.save();
  ctx.lineWidth = Math.max(1, face * 0.035);
  ctx.strokeStyle = `rgba(0,0,0,${0.28 * photoScale})`;
  ctx.beginPath();
  ctx.moveTo(outerX + inset, outerY + inset);
  ctx.lineTo(outerX + inset + length, outerY + inset + length);
  ctx.moveTo(outerX + outerW - inset, outerY + inset);
  ctx.lineTo(outerX + outerW - inset - length, outerY + inset + length);
  ctx.moveTo(outerX + inset, outerY + outerH - inset);
  ctx.lineTo(outerX + inset + length, outerY + outerH - inset - length);
  ctx.moveTo(outerX + outerW - inset, outerY + outerH - inset);
  ctx.lineTo(outerX + outerW - inset - length, outerY + outerH - inset - length);
  ctx.stroke();
  ctx.strokeStyle = 'rgba(255,255,255,0.18)';
  ctx.beginPath();
  ctx.moveTo(outerX + inset + 1, outerY + inset + 1);
  ctx.lineTo(outerX + inset + length - 1, outerY + inset + length - 1);
  ctx.moveTo(outerX + outerW - inset - 1, outerY + inset + 1);
  ctx.lineTo(outerX + outerW - inset - length + 1, outerY + inset + length - 1);
  ctx.moveTo(outerX + inset + 1, outerY + outerH - inset - 1);
  ctx.lineTo(outerX + inset + length - 1, outerY + outerH - inset - length + 1);
  ctx.moveTo(outerX + outerW - inset - 1, outerY + outerH - inset - 1);
  ctx.lineTo(outerX + outerW - inset - length + 1, outerY + outerH - inset - length + 1);
  ctx.stroke();
  ctx.restore();
}

function drawFrameInnerLip(ctx, matX, matY, matW, matH, profile) {
  const inset = Math.max(2, Math.round(profile.lipPx * 0.18));
  const shadowInset = Math.max(inset + 1, Math.round(profile.lipPx * 0.48));
  const edgeWidth = Math.max(1.5, Math.round(profile.facePx * 0.045));
  const innerShadow = ctx.createLinearGradient(matX, matY, matX, matY + matH);
  innerShadow.addColorStop(0, 'rgba(255,255,255,0.18)');
  innerShadow.addColorStop(0.45, 'rgba(255,255,255,0.04)');
  innerShadow.addColorStop(1, 'rgba(0,0,0,0.18)');

  ctx.save();
  ctx.strokeStyle = 'rgba(255,255,255,0.16)';
  ctx.lineWidth = edgeWidth;
  ctx.shadowColor = 'rgba(0,0,0,0.24)';
  ctx.shadowBlur = Math.max(4, profile.lipPx * 0.55);
  ctx.strokeRect(matX + inset, matY + inset, matW - (inset * 2), matH - (inset * 2));
  ctx.shadowColor = 'transparent';
  ctx.strokeStyle = 'rgba(32, 20, 12, 0.24)';
  ctx.lineWidth = Math.max(1, edgeWidth * 0.62);
  ctx.strokeRect(matX + shadowInset, matY + shadowInset, matW - (shadowInset * 2), matH - (shadowInset * 2));
  ctx.globalAlpha = 0.34;
  ctx.fillStyle = innerShadow;
  ctx.fillRect(matX + inset, matY + inset, matW - (inset * 2), Math.max(1, shadowInset - inset));
  ctx.fillRect(matX + inset, matY + matH - shadowInset, matW - (inset * 2), Math.max(1, shadowInset - inset));
  ctx.fillRect(matX + inset, matY + inset, Math.max(1, shadowInset - inset), matH - (inset * 2));
  ctx.fillRect(matX + matW - shadowInset, matY + inset, Math.max(1, shadowInset - inset), matH - (inset * 2));
  ctx.restore();
}

function paintMatSurface(ctx, x, y, w, h, baseColor, item = null) {
  const preview = getPreviewImage(item?.preview_url || '');
  if (preview) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(x, y, w, h);
    ctx.clip();
    drawImageCover(ctx, preview, x, y, w, h);
    ctx.restore();
    return;
  }
  const matGrad = ctx.createLinearGradient(x, y, x + w, y + h);
  matGrad.addColorStop(0, tintHex(baseColor, 16));
  matGrad.addColorStop(0.3, tintHex(baseColor, 4));
  matGrad.addColorStop(0.5, baseColor);
  matGrad.addColorStop(0.7, tintHex(baseColor, -6));
  matGrad.addColorStop(1, tintHex(baseColor, -14));
  ctx.fillStyle = matGrad;
  ctx.fillRect(x, y, w, h);
  ctx.save();
  ctx.globalAlpha = 0.06;
  ctx.strokeStyle = 'rgba(0,0,0,0.3)';
  ctx.lineWidth = 0.5;
  for (let lineY = y + 6; lineY < y + h; lineY += 10) {
    ctx.beginPath();
    ctx.moveTo(x + 4, lineY);
    ctx.lineTo(x + w - 4, lineY);
    ctx.stroke();
  }
  for (let lineX = x + 6; lineX < x + w; lineX += 10) {
    ctx.beginPath();
    ctx.moveTo(lineX, y + 4);
    ctx.lineTo(lineX, y + h - 4);
    ctx.stroke();
  }
  ctx.restore();
  const edgeShine = ctx.createLinearGradient(x, y, x, y + 6);
  edgeShine.addColorStop(0, 'rgba(255,255,255,0.12)');
  edgeShine.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = edgeShine;
  ctx.fillRect(x, y, w, 6);
}

function insetOpeningForReveal(opening, requestedRevealPx) {
  const safeRevealPx = clamp(
    Number(requestedRevealPx || 0),
    0,
    Math.max(0, Math.min((opening.w - 20) / 2, (opening.h - 20) / 2)),
  );
  return {
    revealPx: safeRevealPx,
    rect: {
      x: opening.x + safeRevealPx,
      y: opening.y + safeRevealPx,
      w: Math.max(20, opening.w - (safeRevealPx * 2)),
      h: Math.max(20, opening.h - (safeRevealPx * 2)),
    },
  };
}

function paintMatRevealRing(ctx, outerOpening, innerOpening, baseColor, item = null) {
  if (
    innerOpening.x <= outerOpening.x
    || innerOpening.y <= outerOpening.y
    || innerOpening.x + innerOpening.w >= outerOpening.x + outerOpening.w
    || innerOpening.y + innerOpening.h >= outerOpening.y + outerOpening.h
  ) {
    return;
  }

  ctx.save();
  ctx.beginPath();
  ctx.rect(outerOpening.x, outerOpening.y, outerOpening.w, outerOpening.h);
  ctx.rect(innerOpening.x, innerOpening.y, innerOpening.w, innerOpening.h);
  ctx.clip('evenodd');
  paintMatSurface(ctx, outerOpening.x, outerOpening.y, outerOpening.w, outerOpening.h, baseColor, item);
  ctx.restore();
}

function paintFrameSurface(ctx, x, y, w, h, item, profile = null) {
  const frameProfile = profile || getMouldingProfile(item, 1);
  const face = frameProfile.facePx || Math.min(w, h) / 4;
  paintMouldingRail(ctx, 'left', x, y, face, h, item, frameProfile);
  paintMouldingRail(ctx, 'right', x + w - face, y, face, h, item, frameProfile);
  paintMouldingRail(ctx, 'top', x, y, w, face, item, frameProfile);
  paintMouldingRail(ctx, 'bottom', x, y + h - face, w, face, item, frameProfile);
}

function drawCutEdge(ctx, x, y, w, h) {
  ctx.save();
  ctx.strokeStyle = 'rgba(255,255,255,0.98)';
  ctx.lineWidth = 3;
  ctx.strokeRect(x, y, w, h);
  ctx.strokeStyle = 'rgba(0,0,0,0.10)';
  ctx.lineWidth = 0.5;
  ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  ctx.strokeStyle = 'rgba(0,0,0,0.18)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(x + 1, y + h);
  ctx.lineTo(x + w, y + h);
  ctx.lineTo(x + w, y + 1);
  ctx.stroke();
  ctx.restore();
}

function normalizeCropJson(raw) {
  if (!raw) return {};
  if (typeof raw === 'object' && !Array.isArray(raw)) return raw;
  if (typeof raw !== 'string') return {};
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function resetCropState() {
  activeArtworkCropJson = {};
}

function normalizeRotationInput() {
  return readRotationInput(true);
}

function readRotationInput(normalize = false) {
  const input = document.getElementById('rotateDeg');
  if (!input) return 0;
  const raw = Number(input.value || '0');
  let rotation = Number.isFinite(raw) ? raw : 0;
  if (normalize) {
    rotation = Math.round(rotation / 90) * 90;
    input.value = String(rotation);
  }
  return rotation;
}

function isUploadRotationReady(rotation) {
  return Number.isFinite(rotation) && Math.abs(rotation % 90) < 0.001;
}

function rotatePreviewImage(source, rotation) {
  const quarterTurns = Math.abs(rotation % 180) === 90;
  const canvas = document.createElement('canvas');
  canvas.width = quarterTurns ? source.height : source.width;
  canvas.height = quarterTurns ? source.width : source.height;
  const ctx = canvas.getContext('2d');
  ctx.translate(canvas.width / 2, canvas.height / 2);
  ctx.rotate((rotation * Math.PI) / 180);
  ctx.drawImage(source, -source.width / 2, -source.height / 2);
  return canvas.toDataURL('image/png');
}

function destroyArtworkCropper() {
  if (artworkCropper) {
    artworkCropper.destroy();
    artworkCropper = null;
  }
}

function getCropperAspectRatio() {
  if (cropState.ratio) return cropState.ratio;
  const width = Number(document.getElementById('imgW')?.value || document.getElementById('qw')?.value || 0);
  const height = Number(document.getElementById('imgH')?.value || document.getElementById('qh')?.value || 0);
  return width > 0 && height > 0 ? width / height : NaN;
}

function isValidCropperData(data) {
  return data
    && Number.isFinite(Number(data.x))
    && Number.isFinite(Number(data.y))
    && Number(data.width) > 0
    && Number(data.height) > 0;
}

function captureCropperMetadata() {
  const ratioPreset = document.getElementById('ratioPreset')?.value || 'free';
  if (!artworkCropper) {
    return activeArtworkCropJson || {};
  }
  const data = artworkCropper.getData(true);
  const imageData = artworkCropper.getImageData();
  return {
    version: 2,
    cropper: {
      x: data.x,
      y: data.y,
      width: data.width,
      height: data.height,
      rotate: data.rotate || 0,
      scaleX: data.scaleX || 1,
      scaleY: data.scaleY || 1,
    },
    ratio_preset: ratioPreset,
    ratio_w: Number(document.getElementById('ratioW')?.value || '0') || null,
    ratio_h: Number(document.getElementById('ratioH')?.value || '0') || null,
    source_width: imageData.naturalWidth || cropState.img?.naturalWidth || cropState.img?.width || null,
    source_height: imageData.naturalHeight || cropState.img?.naturalHeight || cropState.img?.height || null,
  };
}

function applyCropperMetadata(metadata = {}) {
  const meta = normalizeCropJson(metadata);
  activeArtworkCropJson = meta;
  if (!artworkCropper) return;
  if (isValidCropperData(meta.cropper)) {
    artworkCropper.setData(meta.cropper);
  } else {
    artworkCropper.reset();
    artworkCropper.crop();
  }
  activeArtworkCropJson = captureCropperMetadata();
  renderMockup();
}

function syncCropperAspectRatio() {
  if (!artworkCropper) return;
  artworkCropper.setAspectRatio(getCropperAspectRatio());
  activeArtworkCropJson = captureCropperMetadata();
  renderMockup();
}

function initArtworkCropper(src, options = {}) {
  const image = document.getElementById('cropperImage');
  if (!image || !src) return Promise.resolve(null);
  return new Promise((resolve, reject) => {
    destroyArtworkCropper();
    image.style.display = 'block';
    image.onload = () => {
      cropState.img = image;
      artworkCropper = new Cropper(image, {
        viewMode: 1,
        autoCropArea: 1,
        background: false,
        responsive: true,
        checkOrientation: false,
        aspectRatio: getCropperAspectRatio(),
        ready() {
          applyCropperMetadata(options.metadata || {});
          resolve(artworkCropper);
        },
        crop() {
          activeArtworkCropJson = captureCropperMetadata();
          renderMockup();
        },
      });
    };
    image.onerror = () => reject(new Error('Could not load artwork preview.'));
    image.removeAttribute('src');
    image.src = src;
  });
}

function loadLocalPreviewImage(resetCrop = true, options = {}) {
  const input = document.getElementById('imageFile');
  const file = input?.files?.[0];
  if (!file) return Promise.resolve(null);
  const version = ++localPreviewVersion;
  const rotation = options.normalizeRotation ? normalizeRotationInput() : readRotationInput(false);
  if (!isUploadRotationReady(rotation)) return Promise.resolve(null);
  const objectUrl = URL.createObjectURL(file);
  const source = new Image();
  localPreviewPromise = new Promise((resolve, reject) => {
    source.onload = () => {
      URL.revokeObjectURL(objectUrl);
      if (version !== localPreviewVersion) {
        resolve(null);
        return;
      }
      const previewSrc = rotatePreviewImage(source, rotation);
      if (resetCrop) resetCropState();
      setArtworkSizeControls(document.getElementById('imgW').value, document.getElementById('imgH').value);
      initArtworkCropper(previewSrc, { metadata: activeArtworkCropJson })
        .then(resolve)
        .catch(reject);
    };
    source.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error('Could not load artwork file for preview.'));
    };
  });
  source.src = objectUrl;
  return localPreviewPromise;
}

function scheduleLocalPreviewRotation() {
  const input = document.getElementById('imageFile');
  const rotation = readRotationInput(false);
  if (!isUploadRotationReady(rotation)) return;
  if (galleryMode === 'edit') {
    rotateArtworkCropperTo(rotation);
    return;
  }
  if (!input?.files?.[0]) return;
  if (rotatePreviewTimer) clearTimeout(rotatePreviewTimer);
  rotatePreviewTimer = setTimeout(() => {
    loadLocalPreviewImage(true).catch((error) => setNotice(error.message, 'error'));
  }, 120);
}

function rotateArtworkCropperTo(rotation) {
  if (!artworkCropper || !isUploadRotationReady(rotation)) return;
  artworkCropper.rotateTo(rotation);
  activeArtworkCropJson = captureCropperMetadata();
  renderMockup();
}

async function flushLocalPreviewRotation() {
  if (rotatePreviewTimer) {
    clearTimeout(rotatePreviewTimer);
    rotatePreviewTimer = null;
  }
  const input = document.getElementById('imageFile');
  if (galleryMode === 'new' && input?.files?.[0]) {
    return loadLocalPreviewImage(true, { normalizeRotation: true });
  }
  return localPreviewPromise;
}

function applyCropMetadata(crop, redraw = false) {
  activeArtworkCropJson = normalizeCropJson(crop);
  if (redraw) renderMockup();
}

function getCropMetadataFromControls() {
  return captureCropperMetadata();
}

function applyRatioControls(image, crop = {}) {
  const preset = document.getElementById('ratioPreset');
  if (!preset) return;
  const meta = normalizeCropJson(crop);
  const label = image?.ratio_label || meta.ratio_preset || 'free';
  const knownPreset = Array.from(preset.options).some((option) => option.value === label);
  preset.value = knownPreset ? label : 'free';
  if (preset.value === 'custom') {
    const ratioW = Number(meta.ratio_w);
    const ratioH = Number(meta.ratio_h);
    document.getElementById('ratioW').value = Number.isFinite(ratioW) && ratioW > 0 ? ratioW : 4;
    document.getElementById('ratioH').value = Number.isFinite(ratioH) && ratioH > 0 ? ratioH : 5;
  } else if (preset.value === 'free') {
    syncCropRatioFromArtworkSize(false);
    return;
  }
  setRatio(false);
}

function syncCropRatioFromArtworkSize(redraw = true, updateControls = true) {
  const width = Number(document.getElementById('imgW')?.value || document.getElementById('qw')?.value || 0);
  const height = Number(document.getElementById('imgH')?.value || document.getElementById('qh')?.value || 0);
  if (width > 0 && height > 0) {
    if (updateControls) {
      const preset = document.getElementById('ratioPreset');
      if (preset) preset.value = 'custom';
      const ratioW = document.getElementById('ratioW');
      const ratioH = document.getElementById('ratioH');
      if (ratioW) ratioW.value = formatInches(width);
      if (ratioH) ratioH.value = formatInches(height);
    }
    cropState.ratio = width / height;
  }
  if (redraw) renderMockup();
}

function setArtworkSizeControls(width, height, syncRatio = true) {
  document.getElementById('imgW').value = width;
  document.getElementById('imgH').value = height;
  document.getElementById('qw').value = width;
  document.getElementById('qh').value = height;
  if (syncRatio) syncCropRatioFromArtworkSize(false);
}

function loadImageFromUrl(src, resetCrop = false) {
  if (!src) return;
  const img = new Image();
  img.onload = () => {
    cropState.img = img;
    if (resetCrop) resetCropState();
    renderMockup();
  };
  img.src = src;
}

function zoomArtworkCropper(delta) {
  if (!artworkCropper) return;
  artworkCropper.zoom(delta);
}

function resetArtworkCropper() {
  if (!artworkCropper) return;
  artworkCropper.reset();
  syncCropperAspectRatio();
}

function fitArtworkCropper() {
  if (!artworkCropper) return;
  artworkCropper.setData({
    x: 0,
    y: 0,
    width: cropState.img?.naturalWidth || cropState.img?.width || 1,
    height: cropState.img?.naturalHeight || cropState.img?.height || 1,
  });
  activeArtworkCropJson = captureCropperMetadata();
  renderMockup();
}

function updateSelectionSummary() {
  const selectedImage = imagesCache.find((img) => img.id === selectedImageId);
  const moulding = getSelectedMaterial('moulding');
  const matLayers = getSelectedMatLayers();
  const glazingKey = document.getElementById('glazingType')?.value || '';
  const glazing = getServiceOption(glazingKey);
  const topMat = matLayers.find((layer) => layer.slot === 'top')?.item || null;
  const secondMat = matLayers.find((layer) => layer.slot === 'second') || null;
  const thirdMat = matLayers.find((layer) => layer.slot === 'third') || null;
  const width = Number(document.getElementById('qw').value || document.getElementById('imgW').value || 0);
  const height = Number(document.getElementById('qh').value || document.getElementById('imgH').value || 0);
  const { offsetX, offsetY, matBorder } = getEffectiveOpeningOffsets();
  const layout = document.getElementById('openingLayout').value || 'single';
  const balance = Number(document.getElementById('openingBalance').value || 50);
  const totalWidth = width > 0 ? width + (matBorder * 2) : 0;
  const totalHeight = height > 0 ? height + (matBorder * 2) : 0;
  const topWeight = formatInches(clamp(matBorder - offsetY, 0, matBorder * 2));
  const bottomWeight = formatInches(clamp(matBorder + offsetY, 0, matBorder * 2));
  const leftWeight = formatInches(clamp(matBorder + offsetX, 0, matBorder * 2));
  const rightWeight = formatInches(clamp(matBorder - offsetX, 0, matBorder * 2));
  setFieldDisplay('selectionImage', selectedImage ? selectedImage.filename : 'No image');
  setFieldDisplay('selectionMoulding', moulding ? moulding.sku : 'None');
  setFieldDisplay('selectionTopMat', topMat ? topMat.sku : 'None');
  setFieldDisplay('selectionSecondMat', secondMat ? secondMat.item.sku : 'None');
  setFieldDisplay('selectionThirdMat', thirdMat ? thirdMat.item.sku : 'None');
  setFieldDisplay('selectionSecondReveal', formatInches(secondMat?.reveal_in || 0.25));
  setFieldDisplay('selectionThirdReveal', formatInches(thirdMat?.reveal_in || 0.25));
  setFieldDisplay('selectionGlazing', glazing ? glazing.label : 'None');
  updateMatSlotState();
  updateMouldingSlotState();
  document.querySelector('.material-slot[data-slot="glazing"]')?.classList.toggle('has-selection', Boolean(glazing));
  setFieldDisplay('selectionFrameSize', width > 0 && height > 0 ? `${formatInches(width)} x ${formatInches(height)} in` : '-');
  setFieldDisplay('selectionOverallSize', totalWidth > 0 && totalHeight > 0 ? `${formatInches(totalWidth)} x ${formatInches(totalHeight)}` : '-');
  const preset = getActivePreset();
  document.getElementById('designItemName').value = moulding || matLayers.length || glazing
    ? `${moulding ? moulding.sku : preset.label} · ${matLayers.length ? `${matLayers.length} mat${matLayers.length > 1 ? 's' : ''}` : 'no mat'}${glazing ? ' · glazing' : ''}`
    : preset.itemName;
  updatePresetUI();
  updateOptionPricePreviews();
  renderMockup();
}

function updateGalleryDetails(image) {
  document.getElementById('galleryDetailId').textContent = image ? image.id : 'None';
  document.getElementById('galleryDetailFilename').textContent = image ? image.filename : 'No image selected';
  document.getElementById('galleryDetailSize').textContent = image ? `${image.width_in} x ${image.height_in} in` : '-';
  document.getElementById('galleryDetailRatio').textContent = image ? image.ratio_label || 'free' : '-';
  const preview = document.getElementById('galleryPreviewImage');
  if (preview) {
    preview.src = image ? image.url : '';
    preview.style.display = image ? 'block' : 'none';
  }
  syncGalleryEditorState(image);
}

function syncGalleryEditorState(image) {
  const saveButton = document.getElementById('gallerySaveButton');
  const useButton = document.getElementById('galleryUseDesignButton');
  const status = document.getElementById('galleryEditorStatus');
  const rotation = document.getElementById('rotateDeg');
  if (image) {
    galleryMode = 'edit';
    if (saveButton) saveButton.textContent = 'Update Artwork';
    if (useButton) useButton.disabled = false;
    if (status) status.textContent = 'Editing saved artwork metadata, rotation, and crop settings. Original file stays intact.';
    if (rotation) rotation.disabled = false;
  } else {
    galleryMode = 'new';
    if (saveButton) saveButton.textContent = 'Save New Artwork';
    if (useButton) useButton.disabled = true;
    if (status) status.textContent = 'New artwork mode. Choose a file or select saved artwork from the list.';
    if (rotation) rotation.disabled = false;
  }
}

function updateQuoteSummary(data) {
  setFieldDisplay('quoteSubtotal', formatCurrency(data?.subtotal));
  setFieldDisplay('quoteTax', formatCurrency(data?.tax));
  setFieldDisplay('quoteTotal', formatCurrency(data?.total));
  setFieldDisplay('quoteTaxRate', `${(((data?.pricing_rules?.tax_rate ?? pricingSettings?.tax_rate ?? 0.06) * 100)).toFixed(2)}%`);
  updateOptionPricePreviews(data?.line_items || null);
  const root = document.getElementById('quoteLineItems');
  const box = document.getElementById('quoteLineItemsBox');
  root.innerHTML = '';
  const lineItems = data?.line_items || null;
  box?.classList.toggle('empty', !lineItems);
  if (!lineItems) {
    root.innerHTML = '<li>No quote calculated yet.</li>';
    return;
  }
  Object.entries(lineItems).forEach(([label, value]) => {
    const li = document.createElement('li');
    li.textContent = `${label.replace(/_/g, ' ')}: ${formatCurrency(value)}`;
    root.appendChild(li);
  });
}

function getServiceOption(key) {
  return serviceOptionsCache.find((item) => item.key === key) || null;
}

function parseServicePriceInput(value) {
  const cleaned = String(value || '').replace(/[^0-9.]/g, '');
  const parts = cleaned.split('.');
  const normalized = parts.length > 1 ? `${parts[0]}.${parts.slice(1).join('')}` : cleaned;
  const amount = Number(normalized || 0);
  if (!Number.isFinite(amount)) return 0;
  return Math.min(Math.max(amount, 0), 999.99);
}

function formatServicePriceInput(value) {
  return parseServicePriceInput(value).toFixed(2);
}

function parseMarkupInput(value) {
  const amount = Number(String(value || '').replace(/[^0-9.]/g, '') || 1);
  if (!Number.isFinite(amount)) return 1;
  return Math.max(amount, 0);
}

function getPricingVariable(service, countId = null) {
  const width = Number(document.getElementById('qw')?.value || document.getElementById('imgW')?.value || 0);
  const height = Number(document.getElementById('qh')?.value || document.getElementById('imgH')?.value || 0);
  const { matBorder } = getEffectiveOpeningOffsets();
  const outsideW = Math.max(width + (matBorder * 2), 0);
  const outsideH = Math.max(height + (matBorder * 2), 0);
  if (service?.basis === 'square_inches') return outsideW * outsideH;
  if (service?.basis === 'united_inches') return outsideW + outsideH;
  return Number(document.getElementById(countId)?.value || 1);
}

function servicePreviewAmount(service, countId = null) {
  const variable = Math.max(getPricingVariable(service, countId), 0);
  return Number(service?.cost || 0) * Number(service?.markup || 1) * variable;
}

function updateOptionPricePreviews(lineItems = null) {
  const globalDiscount = Number(document.getElementById('globalDiscount')?.value || 0);
  OPTION_SELECTS.forEach(({ key, priceId, countId, selectId }) => {
    const node = document.getElementById(priceId);
    if (!node) return;
    if (lineItems && lineItems[key] !== undefined) {
      node.textContent = formatCurrency(lineItems[key]);
      return;
    }
    const service = getServiceOption(key);
    const selected = document.getElementById(selectId)?.value || '';
    if (!service || !selected) {
      node.textContent = '-';
      return;
    }
    const base = servicePreviewAmount(service, countId);
    const discounted = base * (1 - (globalDiscount / 100));
    node.textContent = formatCurrency(discounted);
  });
  const glazingNode = document.getElementById('selectionGlazing');
  const glazingPriceNode = document.getElementById('priceGlazing');
  const glazing = getServiceOption(document.getElementById('glazingType')?.value || '');
  const glazingAmount = lineItems?.glazing ?? (glazing ? servicePreviewAmount(glazing) : null);
  if (glazingNode) glazingNode.value = glazing ? glazing.label : 'None';
  if (glazingPriceNode) glazingPriceNode.textContent = glazingAmount === null ? '-' : formatCurrency(glazingAmount);
}

function populateServiceSelects() {
  OPTION_SELECTS.forEach(({ key, selectId }) => {
    const select = document.getElementById(selectId);
    if (!select) return;
    const current = select.value;
    const service = getServiceOption(key);
    const emptyLabelMap = {
      backing: 'No backing',
      mounting: 'No subject mounting',
      frame_mounting: 'No frame mounting',
      printing: 'No printing',
      various: 'No various',
      assembly: 'No assembly',
      royalties: 'No royalties',
      custom_1: 'No custom 1',
      custom_2: 'No custom 2',
    };
    select.innerHTML = '';
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = emptyLabelMap[key];
    select.appendChild(empty);
    if (service?.active) {
      const option = document.createElement('option');
      option.value = key;
      option.textContent = service.label;
      select.appendChild(option);
    }
    select.value = service?.active && current === key ? key : '';
  });
  populateGlazingSelect();
}

function populateGlazingSelect() {
  const select = document.getElementById('glazingType');
  if (!select) return;
  const current = select.value;
  select.innerHTML = '<option value="">No glazing</option>';
  serviceOptionsCache
    .filter((service) => GLAZING_SERVICE_KEYS.has(service.key) && service.active)
    .forEach((service) => {
      const option = document.createElement('option');
      option.value = service.key;
      option.textContent = service.label;
      select.appendChild(option);
    });
  select.value = serviceOptionsCache.some((service) => service.key === current && service.active) ? current : '';
}

function updateServiceInputs(services) {
  serviceOptionsCache = services || [];
  const map = Object.fromEntries(serviceOptionsCache.map((row) => [row.key, row]));
  const bind = (key, prefix) => {
    const row = map[key];
    if (!row) return;
    const label = document.getElementById(`${prefix}Label`);
    const cost = document.getElementById(`${prefix}Cost`);
    const markup = document.getElementById(`${prefix}Markup`);
    const basis = document.getElementById(`${prefix}Basis`);
    const active = document.getElementById(`${prefix}Active`);
    if (label) label.value = row.label;
    if (cost) cost.value = formatServicePriceInput(row.cost ?? row.price);
    if (markup) markup.value = parseMarkupInput(row.markup).toFixed(2);
    if (basis) basis.value = row.basis || 'count';
    if (active) active.checked = Boolean(row.active);
  };
  SERVICE_ADMIN_ROWS.forEach(([key, prefix]) => bind(key, prefix));
  populateServiceSelects();
  updateOptionPricePreviews(lastQuote?.line_items || null);
}

function updateSidebarSelection(order) {
  document.getElementById('sidebarSelection').textContent = order
    ? `${order.quote_number} · ${order.customer_name}`
    : 'No order selected';
  document.getElementById('sidebarStatus').textContent = order
    ? `${orderStatusLabel(order.status)} · ${formatCurrency(order.total)}`
    : 'Choose an order to export or advance status.';
}

function renderList(targetId, rows, options = {}) {
  const root = document.getElementById(targetId);
  root.innerHTML = '';
  if (!rows.length) {
    root.innerHTML = '<div class="item"><strong>No records</strong><span>Nothing to show yet.</span></div>';
    return;
  }

  rows.forEach((row) => {
    const div = document.createElement('div');
    div.className = `item${options.isSelected?.(row) ? ' selected' : ''}`;
    Object.entries(options.dataset?.(row) || {}).forEach(([key, value]) => {
      div.dataset[key] = value;
    });
    div.innerHTML = options.render(row);
    div.onclick = () => options.onClick?.(row, div);
    const rowButton = div.querySelector('.job-row');
    if (rowButton) {
      div.classList.add('job-list-item');
      rowButton.onclick = (event) => {
        event.stopPropagation();
        options.onClick?.(row, div, event);
      };
    }
    root.appendChild(div);
  });
}

function pickMaterial(type, listId, item, el) {
  selectedMaterials[type] = item.id;
  invalidateQuote();
  document.querySelectorAll(`#${listId} .item`).forEach((n) => n.classList.remove('selected'));
  el.classList.add('selected');
  updateSelectionSummary();
  scheduleDesignHistorySnapshot();
  setNotice('Material changed. Recalculate quote before saving.', 'success');
}

function fillCatalogEditor(item) {
  selectedCatalogItemId = item?.id || null;
  document.getElementById('catalogEditId').value = item?.id || '';
  document.getElementById('catalogEditSku').value = item?.sku || '';
  document.getElementById('catalogEditName').value = item?.name || '';
  document.getElementById('catalogEditCategory').value = item?.category || '';
  document.getElementById('catalogEditVendor').value = item?.vendor || '';
  document.getElementById('catalogEditCost').value = item?.cost ?? '';
  document.getElementById('catalogEditWidth').value = item?.width_in ?? '';
  document.getElementById('catalogEditHeight').value = item?.height_in ?? '';
  document.getElementById('catalogEditRabbet').value = item?.rabbet_in ?? '';
  document.getElementById('catalogEditActive').value = item?.active === 0 ? '0' : '1';
  const title = document.getElementById('adminEditorTitle');
  const subtitle = document.getElementById('adminEditorSubtitle');
  if (title) title.textContent = item ? `Edit ${item.sku || 'Catalog Item'}` : 'New Catalog Item';
  if (subtitle) subtitle.textContent = item
    ? 'Review the imported values, make the correction, then save.'
    : 'Create a material without rerunning a full catalog import.';
}

function resetCatalogEditor() {
  fillCatalogEditor(null);
  renderAdminCatalogTable();
}

function openCatalogEditor(item = null, trigger = null) {
  adminCatalogEditorReturnFocus = trigger || document.activeElement;
  fillCatalogEditor(item);
  document.getElementById('adminCatalogEditorDrawer')?.classList.add('open');
  document.getElementById('adminEditorBackdrop')?.classList.add('open');
  window.setTimeout(() => document.getElementById('catalogEditSku')?.focus(), 0);
}

function openCatalogEditorById(itemId, trigger = null) {
  const item = catalogCache.find((row) => Number(row.id) === Number(itemId));
  if (!item) {
    setNotice('Catalog item could not be found. Reload the catalog and try again.', 'error');
    return;
  }
  openCatalogEditor(item, trigger);
  renderAdminCatalogTable();
}

function closeCatalogEditor() {
  document.getElementById('adminCatalogEditorDrawer')?.classList.remove('open');
  document.getElementById('adminEditorBackdrop')?.classList.remove('open');
  if (adminCatalogEditorReturnFocus && typeof adminCatalogEditorReturnFocus.focus === 'function') {
    adminCatalogEditorReturnFocus.focus();
  }
  adminCatalogEditorReturnFocus = null;
}

function setAdminView(view, trigger = null) {
  const allowed = new Set(['catalog', 'import', 'pricing', 'services', 'studio', 'accounting', 'backups', 'diagnostics']);
  if (!allowed.has(view)) return;
  document.querySelectorAll('.admin-view-button').forEach((button) => {
    const active = button.dataset.adminView === view;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  const catalogView = document.getElementById('adminCatalogView');
  if (catalogView) catalogView.style.display = view === 'catalog' ? '' : 'none';
  document.querySelectorAll('[data-admin-panel]').forEach((panel) => {
    panel.classList.toggle('active', panel.dataset.adminPanel === view);
  });
  if (view === 'catalog') renderAdminCatalogTable();
  if (view === 'studio') loadStudioProfile();
  trigger?.blur();
}

function applyStudioProfile(profile) {
  const fields = {
    studioBusinessName: 'business_name', studioContactName: 'contact_name', studioPhone: 'phone',
    studioEmail: 'email', studioStreet: 'street', studioCity: 'city', studioState: 'state', studioPostalCode: 'postal_code',
  };
  Object.entries(fields).forEach(([id, key]) => { const node = document.getElementById(id); if (node) node.value = profile[key] || ''; });
  const name = document.getElementById('studioBrandName');
  if (name) name.textContent = profile.business_name || '';
  const contact = document.getElementById('studioBrandContact');
  if (contact) contact.textContent = profile.contact_name || '';
  const channels = document.getElementById('studioBrandChannels');
  if (channels) channels.textContent = [profile.phone, profile.email].filter(Boolean).join(' · ');
  const address = document.getElementById('studioBrandAddress');
  if (address) address.textContent = profile.address || '';
  const brandLogo = document.getElementById('studioBrandLogo');
  if (brandLogo) { brandLogo.hidden = !profile.logo_url; brandLogo.src = profile.logo_url || ''; brandLogo.alt = `${profile.business_name || 'Studio'} logo`; }
  const preview = document.getElementById('studioLogoPreview');
  if (preview) { preview.hidden = !profile.logo_url; preview.src = profile.logo_url || ''; }
}

async function loadStudioProfile() {
  try { applyStudioProfile((await fetchJson('/api/studio-profile')).profile); }
  catch (error) { setNotice(error.message, 'error'); }
}

async function loadEditionStatus() {
  const name = document.getElementById('editionName');
  const catalog = document.getElementById('editionCatalogUsage');
  const orders = document.getElementById('editionOrdersUsage');
  const imports = document.getElementById('editionImportsUsage');
  const formatUsage = (used, limit) => `${used ?? 0} / ${limit === 'unlimited' ? 'unlimited' : limit}`;
  try {
    const data = await fetchJson('/api/edition/status');
    editionStatusCache = data;
    if (name) name.textContent = data.label || data.edition;
    if (catalog) catalog.textContent = formatUsage(data.usage?.active_catalog_items, data.limits?.active_catalog_items);
    if (orders) orders.textContent = formatUsage(data.usage?.saved_orders_quotes, data.limits?.saved_orders_quotes);
    if (imports) imports.textContent = formatUsage(data.usage?.catalog_package_imports, data.limits?.local_catalog_package_imports);
    renderAccountingExportState();
  } catch (error) {
    editionStatusCache = null;
    if (name) name.textContent = 'Edition status unavailable';
    [catalog, orders, imports].forEach((node) => { if (node) node.textContent = '-'; });
    renderAccountingExportState();
    setNotice(error.message, 'error');
  }
}

function renderAccountingExportState() {
  const message = document.getElementById('accountingExportMessage');
  const button = document.getElementById('accountingExportButton');
  const available = editionStatusCache?.features?.accounting_csv_export === true;
  if (button) button.hidden = !available;
  if (!message) return;
  message.textContent = available
    ? 'Generate a local ZIP containing customer, invoice, and invoice-line CSV files for accounting review.'
    : 'Accounting CSV export is available in Workstation Edition. Community data remains unchanged.';
}

async function downloadAccountingExport() {
  const button = document.getElementById('accountingExportButton');
  if (button) button.disabled = true;
  try {
    const response = await fetch('/api/accounting/export.zip');
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || response.statusText || 'Accounting export failed');
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'accounting_csv_export.zip';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setNotice('Accounting CSV bundle generated locally.', 'success');
  } catch (error) {
    setNotice(error.message, 'error');
  } finally {
    if (button) button.disabled = false;
  }
}

async function saveStudioProfile(event) {
  event.preventDefault();
  try {
    const data = await fetchJson('/api/studio-profile', { method: 'POST', body: new FormData(event.currentTarget) });
    applyStudioProfile(data.profile);
    setNotice('Studio profile saved.', 'success');
  } catch (error) { setNotice(error.message, 'error'); }
}

async function uploadStudioLogo() {
  const input = document.getElementById('studioLogoFile');
  if (!input?.files?.[0]) { setNotice('Choose a PNG or WebP logo first.', 'warning'); return; }
  const body = new FormData(); body.append('file', input.files[0]);
  try { const data = await fetchJson('/api/studio-profile/logo', { method: 'POST', body }); applyStudioProfile(data.profile); input.value = ''; setNotice('Studio logo uploaded.', 'success'); }
  catch (error) { setNotice(error.message, 'error'); }
}

async function removeStudioLogo() {
  try { const data = await fetchJson('/api/studio-profile/logo', { method: 'DELETE' }); applyStudioProfile(data.profile); setNotice('Studio logo removed.', 'success'); }
  catch (error) { setNotice(error.message, 'error'); }
}

function setAdminCatalogCategory(category, trigger = null) {
  adminCatalogCategory = category || '';
  resetAdminCatalogLimit();
  document.querySelectorAll('[data-admin-category]').forEach((button) => {
    const active = button.dataset.adminCategory === adminCatalogCategory;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  renderAdminCatalogTable();
  trigger?.focus();
}

function setAdminCatalogSort(key) {
  adminCatalogSortDirection = adminCatalogSortKey === key && adminCatalogSortDirection === 'asc' ? 'desc' : 'asc';
  adminCatalogSortKey = key;
  renderAdminCatalogTable();
}

function resetAdminCatalogLimit() {
  adminCatalogRenderLimit = 300;
}

function loadMoreAdminCatalog() {
  adminCatalogRenderLimit += 300;
  renderAdminCatalogTable();
}

function renderAdminCatalogTable() {
  const root = document.getElementById('adminCatalogTable');
  if (!root) return;
  const helpers = window.AdminCatalogTable;
  if (!helpers) {
    root.innerHTML = '<div class="admin-empty-state">Catalog tools are still loading.</div>';
    return;
  }
  const query = document.getElementById('adminCatalogSearch')?.value || '';
  const filtered = helpers.filterCatalogItems(catalogCache, { category: adminCatalogCategory, query });
  const sortedRows = helpers.sortCatalogItems(filtered, adminCatalogSortKey, adminCatalogSortDirection);
  const rows = sortedRows.slice(0, adminCatalogRenderLimit);
  const count = document.getElementById('adminCatalogResultCount');
  const coverage = document.getElementById('adminCatalogCoverage');
  const loadMore = document.getElementById('adminCatalogLoadMore');
  const previewCount = catalogCache.filter((item) => item.preview_url).length;
  if (count) count.textContent = sortedRows.length > rows.length
    ? `Showing ${rows.length} of ${sortedRows.length} matches · ${catalogCache.length} total`
    : `${sortedRows.length} matches · ${catalogCache.length} total`;
  if (coverage) coverage.textContent = `${previewCount} previews linked`;
  if (loadMore) loadMore.hidden = rows.length >= sortedRows.length;
  document.querySelectorAll('[data-admin-sort]').forEach((button) => {
    const active = button.dataset.adminSort === adminCatalogSortKey;
    button.classList.toggle('active', active);
    button.setAttribute('aria-sort', active ? (adminCatalogSortDirection === 'asc' ? 'ascending' : 'descending') : 'none');
    const indicator = button.querySelector('span');
    if (indicator) indicator.textContent = active ? (adminCatalogSortDirection === 'asc' ? '↑' : '↓') : '';
  });
  if (!rows.length) {
    root.innerHTML = '<div class="admin-empty-state">No catalog items match this view. Clear the search or choose another category.</div>';
    return;
  }
  root.innerHTML = rows.map((item) => {
    const preview = item.preview_url
      ? `<img class="admin-catalog-thumb" src="${escapeHtml(item.preview_url)}" alt="" />`
      : '<span class="admin-catalog-thumb" aria-hidden="true"></span>';
    const dimensions = item.width_in ? `${formatInches(item.width_in)} in` : '-';
    const activeLabel = item.active === 0 ? 'Inactive' : 'Active';
    return `
      <button type="button" role="row" class="admin-catalog-row${Number(selectedCatalogItemId) === Number(item.id) ? ' selected' : ''}" onclick="openCatalogEditorById(${Number(item.id)}, this)">
        ${preview}
        <strong>${escapeHtml(item.sku || '-')}</strong>
        <span title="${escapeHtml(item.name || '')}">${escapeHtml(item.name || '-')}</span>
        <span class="admin-category-pill">${escapeHtml(item.category || '-')}</span>
        <span title="${escapeHtml(item.vendor || '')}">${escapeHtml(item.vendor || '-')}</span>
        <span>${formatCurrency(item.cost)}</span>
        <span>${escapeHtml(dimensions)}</span>
        <span class="admin-active-pill${item.active === 0 ? ' inactive' : ''}">${activeLabel}</span>
      </button>`;
  }).join('');
}

function pickImage(image, el) {
  if (pendingOpeningArtworkId) {
    assignGalleryArtworkToOpening(image).catch((error) => setNotice(error.message, 'error'));
    return;
  }
  selectedImageId = image.id;
  document.querySelectorAll('#imageList .item').forEach((n) => n.classList.remove('selected'));
  el?.classList.add('selected');
  const fileInput = document.getElementById('imageFile');
  if (fileInput) fileInput.value = '';
  const crop = normalizeCropJson(image.crop_json);
  const rotation = document.getElementById('rotateDeg');
  if (rotation) rotation.value = String(Number(crop.cropper?.rotate || 0));
  setArtworkSizeControls(image.width_in, image.height_in);
  applyRatioControls(image, crop);
  applyCropMetadata(crop, false);
  initArtworkCropper(image.url, { metadata: crop });
  updateGalleryDetails(image);
  updateSelectionSummary();
  scheduleDesignHistorySnapshot();
}

async function useSelectedImageInDesign() {
  if (!selectedImageId) {
    setNotice('Select an image first.', 'error');
    return;
  }
  if (galleryMode === 'edit' && artworkCropper) {
    const updated = await updateSelectedImageMetadata({ quiet: true, refreshList: false });
    if (!updated) return;
  }
  document.getElementById('qw').value = document.getElementById('imgW').value;
  document.getElementById('qh').value = document.getElementById('imgH').value;
  syncCropRatioFromArtworkSize(false);
  switchTab('design');
  scrollDesignBuilderIntoView();
  updatePresetUI();
  updateSelectionSummary();
  scheduleDesignHistorySnapshot();
  setNotice('Design workspace loaded with the selected gallery image.', 'success');
}

function newGalleryArtworkMode() {
  selectedImageId = null;
  galleryMode = 'new';
  document.querySelectorAll('#imageList .item').forEach((n) => n.classList.remove('selected'));
  const fileInput = document.getElementById('imageFile');
  if (fileInput) fileInput.value = '';
  const rotation = document.getElementById('rotateDeg');
  if (rotation) rotation.value = '0';
  resetCropState();
  cropState.img = null;
  destroyArtworkCropper();
  const preview = document.getElementById('cropperImage');
  if (preview) {
    preview.removeAttribute('src');
    preview.style.display = 'none';
  }
  updateGalleryDetails(null);
  updateSelectionSummary();
  renderMockup();
}

function setRatio(redraw = true) {
  const value = document.getElementById('ratioPreset').value;
  if (value === 'free') {
    syncCropRatioFromArtworkSize(redraw, false);
    return;
  } else if (value === 'custom') {
    const w = Number(document.getElementById('ratioW').value || '0');
    const h = Number(document.getElementById('ratioH').value || '0');
    cropState.ratio = w > 0 && h > 0 ? w / h : null;
  } else {
    const [w, h] = value.split(':').map(Number);
    cropState.ratio = w / h;
  }
  if (redraw) {
    syncCropperAspectRatio();
    renderMockup();
  }
}

function drawImageCover(ctx, img, x, y, w, h) {
  const scale = Math.max(w / img.width, h / img.height);
  const drawW = img.width * scale;
  const drawH = img.height * scale;
  const offsetX = x + (w - drawW) / 2;
  const offsetY = y + (h - drawH) / 2;
  ctx.drawImage(img, offsetX, offsetY, drawW, drawH);
}

function makeRotatedSourceCanvas(img, rotation) {
  const normalized = ((Math.round(rotation / 90) * 90) % 360 + 360) % 360;
  if (!normalized) return null;
  const imgW = img.naturalWidth || img.width || 0;
  const imgH = img.naturalHeight || img.height || 0;
  if (!imgW || !imgH) return null;
  const quarterTurns = normalized === 90 || normalized === 270;
  const canvas = document.createElement('canvas');
  canvas.width = quarterTurns ? imgH : imgW;
  canvas.height = quarterTurns ? imgW : imgH;
  const rotatedCtx = canvas.getContext('2d');
  rotatedCtx.translate(canvas.width / 2, canvas.height / 2);
  rotatedCtx.rotate((normalized * Math.PI) / 180);
  rotatedCtx.drawImage(img, -imgW / 2, -imgH / 2, imgW, imgH);
  return canvas;
}

function drawArtworkImage(ctx, img, cropJson, rect) {
  const meta = normalizeCropJson(cropJson);
  const crop = meta.cropper;
  const rotatedSource = makeRotatedSourceCanvas(img, Number(crop?.rotate || 0));
  const source = rotatedSource || img;
  const imgW = source.naturalWidth || source.width || 0;
  const imgH = source.naturalHeight || source.height || 0;
  if (!imgW || !imgH || !isValidCropperData(crop)) {
    drawImageCover(ctx, source, rect.x, rect.y, rect.w, rect.h);
    return;
  }
  const sx = clamp(Number(crop.x), 0, Math.max(0, imgW - 1));
  const sy = clamp(Number(crop.y), 0, Math.max(0, imgH - 1));
  const sw = clamp(Number(crop.width), 1, imgW - sx);
  const sh = clamp(Number(crop.height), 1, imgH - sy);
  ctx.drawImage(source, sx, sy, sw, sh, rect.x, rect.y, rect.w, rect.h);
}

function renderMockup() {
  const canvas = document.getElementById('mockupCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const artW = Number(document.getElementById('qw')?.value || document.getElementById('imgW')?.value || 8);
  const artH = Number(document.getElementById('qh')?.value || document.getElementById('imgH')?.value || 10);
  const hasImage = !!cropState.img;
  const showMockupGuides = window.WorkspaceUI?.shouldShowMockupGuides(hasImage) ?? !hasImage;
  const { offsetX: openingOffsetX, offsetY: openingOffsetY, matBorder } = getEffectiveOpeningOffsets();
  const openingLayout = document.getElementById('openingLayout')?.value || 'single';
  const openingSpacing = Number(document.getElementById('openingSpacing')?.value || 1.5);
  const openingBalance = Number(document.getElementById('openingBalance')?.value || 50);
  const moulding = getSelectedMaterial('moulding');
  const glazing = getServiceOption(document.getElementById('glazingType')?.value || '');
  const matLayers = getSelectedMatLayers();
  const mouldingWidth = Math.max(Number(moulding?.width_in || 0) || 1.5, 0.75);

  const outerWIn = artW + (matBorder * 2) + (mouldingWidth * 2);
  const outerHIn = artH + (matBorder * 2) + (mouldingWidth * 2);
  const scale = Math.min((canvas.width - 120) / outerWIn, (canvas.height - 120) / outerHIn);
  const frameProfile = getMouldingProfile(moulding, scale);
  const secondRevealPx = Number(document.getElementById('secondMatReveal')?.value || 0.25) * scale;
  const thirdRevealPx = Number(document.getElementById('thirdMatReveal')?.value || 0.25) * scale;
  const visibleRevealLayers = matLayers.slice(1);
  const getLayerRevealPx = (layer) => (layer.slot === 'second' ? secondRevealPx : thirdRevealPx) || 0;
  const totalRevealPx = visibleRevealLayers.reduce((total, layer) => total + getLayerRevealPx(layer), 0);

  const outerW = outerWIn * scale;
  const outerH = outerHIn * scale;
  const framePx = frameProfile.facePx;
  const outerX = (canvas.width - outerW) / 2;
  const outerY = (canvas.height - outerH) / 2;

  if (hasImage) {
    const wallGrad = ctx.createRadialGradient(canvas.width * 0.32, canvas.height * 0.18, 60, canvas.width * 0.5, canvas.height * 0.48, canvas.width * 0.7);
    wallGrad.addColorStop(0, '#f4efe7');
    wallGrad.addColorStop(1, '#ddd3c4');
    ctx.fillStyle = wallGrad;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = 'rgba(255,255,255,0.18)';
    for (let i = 0; i < canvas.height; i += 22) {
      ctx.fillRect(0, i, canvas.width, 1);
    }

    ctx.shadowColor = 'rgba(23, 32, 51, 0.18)';
    ctx.shadowBlur = 36;
    ctx.shadowOffsetY = 22;
    ctx.fillStyle = '#5d4630';
    ctx.fillRect(outerX, outerY, outerW, outerH);
    ctx.shadowColor = 'transparent';
  } else {
    ctx.fillStyle = '#f4f6f8';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#eef2f6';
    ctx.fillRect(outerX, outerY, outerW, outerH);
    ctx.strokeStyle = 'rgba(32, 71, 79, 0.18)';
    ctx.lineWidth = 2;
    ctx.strokeRect(outerX, outerY, outerW, outerH);
  }

  const mouldingPreview = moulding ? getPreviewImage(moulding?.preview_url || '') : null;
  const matX = outerX + framePx;
  const matY = outerY + framePx;
  const matW = outerW - (framePx * 2);
  const matH = outerH - (framePx * 2);
  const artPxW = artW * scale;
  const artPxH = artH * scale;
  if (matLayers.length) {
    paintMatSurface(ctx, matX, matY, matW, matH, inferMatColor(matLayers[0]?.item, 0), matLayers[0]?.item || null);
  } else {
    ctx.fillStyle = '#f7f8fa';
    ctx.fillRect(matX, matY, matW, matH);
    ctx.strokeStyle = 'rgba(32, 71, 79, 0.22)';
    ctx.lineWidth = 2;
    ctx.strokeRect(matX, matY, matW, matH);
  }

  const openings = [];
  const finalOpenings = [];
  mockupInteraction.type = null;
  mockupInteraction.scale = scale;
  mockupInteraction.handle = null;
  mockupInteraction.positionBox = null;
  if (openingLayout === 'diptych') {
    const spacingPx = openingSpacing * scale;
    const totalOpeningWidth = Math.max(60, artPxW - spacingPx);
    const leftShare = Math.min(0.8, Math.max(0.2, openingBalance / 100));
    const baseLeftOpeningWidth = totalOpeningWidth * leftShare;
    const baseRightOpeningWidth = totalOpeningWidth - baseLeftOpeningWidth;
    const leftOpeningWidth = Math.min(matW, baseLeftOpeningWidth + (totalRevealPx * 2));
    const rightOpeningWidth = Math.min(matW, baseRightOpeningWidth + (totalRevealPx * 2));
    const openingHeight = Math.min(matH, Math.max(40, artPxH + (totalRevealPx * 2)));
    const groupWidth = leftOpeningWidth + rightOpeningWidth + spacingPx;
    const defaultMarginX = Math.max(0, (matW - groupWidth) / 2);
    const defaultMarginY = Math.max(0, (matH - openingHeight) / 2);
    const offsetXPx = Math.max(-defaultMarginX, Math.min(defaultMarginX, openingOffsetX * scale));
    const offsetYPx = Math.max(-defaultMarginY, Math.min(defaultMarginY, openingOffsetY * scale));
    const startX = matX + defaultMarginX + offsetXPx;
    const startY = matY + defaultMarginY - offsetYPx;
    openings.push({
      x: startX,
      y: startY,
      w: leftOpeningWidth,
      h: openingHeight,
    });
    openings.push({
      x: startX + leftOpeningWidth + spacingPx,
      y: startY,
      w: rightOpeningWidth,
      h: openingHeight,
    });
    const dividerX = startX + leftOpeningWidth + (spacingPx / 2);
    mockupInteraction.type = 'spacing';
    mockupInteraction.handle = {
      x: dividerX - 10,
      y: startY,
      w: 20,
      h: openingHeight,
    };
  } else if (openingLayout === 'multi') {
    customOpenings.forEach(op => {
      const opCenterX = matX + matW / 2 + op.x * scale;
      const opCenterY = matY + matH / 2 - op.y * scale;
      const opW = (op.w * scale) + (totalRevealPx * 2);
      const opH = (op.h * scale) + (totalRevealPx * 2);
      openings.push({
        x: opCenterX - opW / 2,
        y: opCenterY - opH / 2,
        w: opW,
        h: opH,
        id: op.id,
      });
    });
  } else {
    const openingWidth = Math.min(matW, Math.max(40, artPxW + (totalRevealPx * 2)));
    const openingHeight = Math.min(matH, Math.max(40, artPxH + (totalRevealPx * 2)));
    const defaultMarginX = Math.max(0, (matW - openingWidth) / 2);
    const defaultMarginY = Math.max(0, (matH - openingHeight) / 2);
    const offsetXPx = Math.max(-defaultMarginX, Math.min(defaultMarginX, openingOffsetX * scale));
    const offsetYPx = Math.max(-defaultMarginY, Math.min(defaultMarginY, openingOffsetY * scale));
    openings.push({
      x: matX + defaultMarginX + offsetXPx,
      y: matY + defaultMarginY - offsetYPx,
      w: openingWidth,
      h: openingHeight,
    });
  }

  const groupBounds = openings.reduce((bounds, opening) => ({
    x: Math.min(bounds.x, opening.x),
    y: Math.min(bounds.y, opening.y),
    w: Math.max(bounds.x + bounds.w, opening.x + opening.w) - Math.min(bounds.x, opening.x),
    h: Math.max(bounds.y + bounds.h, opening.y + opening.h) - Math.min(bounds.y, opening.y),
  }), { x: openings[0].x, y: openings[0].y, w: openings[0].w, h: openings[0].h });
  mockupInteraction.positionBox = groupBounds;
  renderedOpenings = openings.map(op => ({ ...op }));

  openings.forEach((opening, index) => {
    let currentOpening = { ...opening };
    visibleRevealLayers.forEach((layer, layerIndex) => {
      const { rect: nextOpening } = insetOpeningForReveal(currentOpening, getLayerRevealPx(layer));
      paintMatRevealRing(ctx, currentOpening, nextOpening, inferMatColor(layer.item, layerIndex + 1), layer.item);
      drawCutEdge(ctx, currentOpening.x, currentOpening.y, currentOpening.w, currentOpening.h);
      currentOpening = nextOpening;
    });
    finalOpenings.push(currentOpening);

    ctx.save();
    ctx.beginPath();
    ctx.rect(currentOpening.x, currentOpening.y, currentOpening.w, currentOpening.h);
    ctx.clip();
    const batchSelectionActive = openingLayout === 'multi' && selectedOpeningIds.size > 0;
    const openingIsBatchSelected = !batchSelectionActive || selectedOpeningIds.has(opening.id);
    // Check for per-opening artwork (multi layout)
    let perOpeningImg = null;
    if (openingLayout === 'multi' && opening.id) {
      const matchingOp = customOpenings.find(o => o.id === opening.id);
      if (matchingOp && matchingOp.artworkImg) {
        perOpeningImg = matchingOp.artworkImg;
      }
    }
    
    if (perOpeningImg) {
      ctx.shadowColor = 'rgba(0,0,0,0.16)';
      ctx.shadowBlur = 16;
      ctx.shadowOffsetY = 8;
      // Cover-fit the per-opening image
      const imgRatio = perOpeningImg.naturalWidth / perOpeningImg.naturalHeight;
      const boxRatio = currentOpening.w / currentOpening.h;
      let sx = 0, sy = 0, sw = perOpeningImg.naturalWidth, sh = perOpeningImg.naturalHeight;
      if (imgRatio > boxRatio) {
        sw = perOpeningImg.naturalHeight * boxRatio;
        sx = (perOpeningImg.naturalWidth - sw) / 2;
      } else {
        sh = perOpeningImg.naturalWidth / boxRatio;
        sy = (perOpeningImg.naturalHeight - sh) / 2;
      }
      ctx.drawImage(perOpeningImg, sx, sy, sw, sh, currentOpening.x, currentOpening.y, currentOpening.w, currentOpening.h);
      ctx.shadowColor = 'transparent';
    } else if (hasImage) {
      ctx.shadowColor = 'rgba(0,0,0,0.16)';
      ctx.shadowBlur = 16;
      ctx.shadowOffsetY = 8;
      drawArtworkImage(ctx, cropState.img, activeArtworkCropJson, currentOpening);
      ctx.shadowColor = 'transparent';
    } else {
      ctx.fillStyle = '#f3f5f9';
      ctx.fillRect(currentOpening.x, currentOpening.y, currentOpening.w, currentOpening.h);
      ctx.strokeStyle = 'rgba(32, 71, 79, 0.25)';
      ctx.setLineDash([6, 6]);
      ctx.lineWidth = 2;
      ctx.strokeRect(currentOpening.x + 8, currentOpening.y + 8, currentOpening.w - 16, currentOpening.h - 16);
      ctx.setLineDash([]);
      ctx.fillStyle = '#4c5a73';
      ctx.font = '14px Georgia';
      ctx.fillText(`Opening ${index + 1}`, currentOpening.x + 20, currentOpening.y + 30);
      ctx.fillStyle = '#7a879d';
      ctx.font = '12px Georgia';
      let opWLabel = artW;
      let opHLabel = artH;
      if (openingLayout === 'multi') {
        const matchingOp = customOpenings.find(o => o.id === opening.id);
        if (matchingOp) {
          opWLabel = matchingOp.w;
          opHLabel = matchingOp.h;
        }
      }
      ctx.fillText(`${formatInches(opWLabel)} x ${formatInches(opHLabel)} in`, currentOpening.x + 20, currentOpening.y + 50);
    }
    if (batchSelectionActive) {
      ctx.fillStyle = openingIsBatchSelected ? 'rgba(0, 180, 167, 0.10)' : 'rgba(17, 17, 17, 0.18)';
      ctx.fillRect(currentOpening.x, currentOpening.y, currentOpening.w, currentOpening.h);
    }
    ctx.restore();
    if (matLayers.length) {
      drawCutEdge(ctx, currentOpening.x, currentOpening.y, currentOpening.w, currentOpening.h);
    }
    if (openingLayout === 'multi' && selectedOpeningIds.has(opening.id)) {
      ctx.save();
      ctx.strokeStyle = '#c00000';
      ctx.lineWidth = 3;
      ctx.setLineDash([]);
      ctx.strokeRect(opening.x, opening.y, opening.w, opening.h);
      ctx.fillStyle = '#c00000';
      ctx.fillRect(opening.x + 6, opening.y + 6, 28, 24);
      ctx.strokeStyle = '#111111';
      ctx.lineWidth = 1.25;
      ctx.strokeRect(opening.x + 6, opening.y + 6, 28, 24);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 16px Georgia';
      ctx.fillText(String(index + 1), opening.x + 15, opening.y + 23);
      ctx.restore();
    } else if (openingLayout === 'multi' && selectedOpeningIds.size) {
      ctx.save();
      ctx.fillStyle = 'rgba(17, 17, 17, 0.22)';
      ctx.fillRect(opening.x, opening.y, opening.w, opening.h);
      ctx.restore();
    }

    if (openingLayout === 'multi' && opening.id === selectedOpeningId) {
      ctx.save();
      // Draw 8 interactive white handles with dark borders
      const left = opening.x;
      const right = opening.x + opening.w;
      const top = opening.y;
      const bottom = opening.y + opening.h;
      const cx = opening.x + opening.w / 2;
      const cy = opening.y + opening.h / 2;
      
      const handles = [
        { x: left, y: top },
        { x: cx, y: top },
        { x: right, y: top },
        { x: right, y: cy },
        { x: right, y: bottom },
        { x: cx, y: bottom },
        { x: left, y: bottom },
        { x: left, y: cy }
      ];
      
      ctx.fillStyle = '#ffffff';
      ctx.strokeStyle = '#111111';
      ctx.lineWidth = 1.5;
      
      handles.forEach(h => {
        ctx.fillRect(h.x - 8, h.y - 8, 16, 16);
        ctx.strokeRect(h.x - 8, h.y - 8, 16, 16);
      });
      
      ctx.restore();
    }
  });

  if (glazing && hasImage) {
    const first = finalOpenings[0];
    const last = finalOpenings[finalOpenings.length - 1];
    const glare = ctx.createLinearGradient(first.x, first.y, last.x + last.w, last.y + last.h);
    glare.addColorStop(0, 'rgba(255,255,255,0.24)');
    glare.addColorStop(0.45, 'rgba(255,255,255,0.04)');
    glare.addColorStop(1, 'rgba(255,255,255,0.16)');
    ctx.fillStyle = glare;
    finalOpenings.forEach((opening) => {
      ctx.fillRect(opening.x, opening.y, opening.w, opening.h);
    });
  }

  if (moulding) {
    paintFrameSurface(ctx, outerX, outerY, outerW, outerH, moulding, frameProfile);
    if (!mouldingPreview) {
      drawFrameMiters(ctx, outerX, outerY, outerW, outerH, frameProfile, 1);
    }
    drawFrameInnerLip(ctx, matX, matY, matW, matH, frameProfile);
  }

  if (showMockupGuides && mockupInteraction.positionBox) {
    const box = mockupInteraction.positionBox;
    ctx.setLineDash([8, 6]);
    ctx.strokeStyle = 'rgba(32, 71, 79, 0.48)';
    ctx.lineWidth = 2;
    ctx.strokeRect(box.x, box.y, box.w, box.h);
    ctx.setLineDash([]);
    ctx.fillStyle = '#20474f';
    ctx.beginPath();
    ctx.arc(box.x + (box.w / 2), box.y + (box.h / 2), 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(box.x + (box.w / 2) - 12, box.y + (box.h / 2));
    ctx.lineTo(box.x + (box.w / 2) + 12, box.y + (box.h / 2));
    ctx.moveTo(box.x + (box.w / 2), box.y + (box.h / 2) - 12);
    ctx.lineTo(box.x + (box.w / 2), box.y + (box.h / 2) + 12);
    ctx.stroke();
  }

  if (showMockupGuides && mockupInteraction.handle) {
    const handle = mockupInteraction.handle;
    ctx.fillStyle = 'rgba(32, 71, 79, 0.18)';
    ctx.fillRect(handle.x, handle.y, handle.w, handle.h);
    ctx.strokeStyle = '#20474f';
    ctx.lineWidth = 2;
    ctx.strokeRect(handle.x, handle.y, handle.w, handle.h);
  }

  ctx.fillStyle = '#172033';
  ctx.font = '14px Georgia';
  const layoutLabel = openingLayout === 'multi' ? `Custom Multi-Opening (${customOpenings.length} windows)` : (openingLayout === 'diptych' ? '2 openings' : 'single opening');
  if (cropState.img) {
    ctx.fillText(`Total size: ${formatInches(artW + (matBorder * 2))} x ${formatInches(artH + (matBorder * 2))} in`, 24, canvas.height - 46);
    ctx.fillText(`Mats: ${matLayers.length || 0} · Layout: ${layoutLabel} · Pos X ${openingOffsetX.toFixed(2)} in · Pos Y ${openingOffsetY.toFixed(2)} in`, 24, canvas.height - 24);
  } else {
    const frameWidth = mouldingWidth.toFixed(2);
    ctx.fillText('No artwork loaded — working in measurement view', 24, canvas.height - 66);
    ctx.fillText(`Opening: ${formatInches(artW)} x ${formatInches(artH)} in · Mat border ${matBorder.toFixed(2)} in · Frame ${frameWidth} in`, 24, canvas.height - 44);
    ctx.fillText(`Layout: ${layoutLabel} · Offset X ${openingOffsetX.toFixed(2)} in · Offset Y ${openingOffsetY.toFixed(2)} in`, 24, canvas.height - 24);
  }
}

function bindMockupDesigner() {
  const canvas = document.getElementById('mockupCanvas');
  let dragging = false;
  let dragType = null;
  let startX = 0;
  let startY = 0;
  let startW = 0;
  let startH = 0;
  let startXOffset = 0;
  let startYOffset = 0;
  
  canvas.addEventListener('mousedown', (event) => {
    const rect = canvas.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * canvas.width;
    const y = ((event.clientY - rect.top) / rect.height) * canvas.height;
    const openingLayout = document.getElementById('openingLayout')?.value || 'single';
    
    // 1. Check for clicking interactive handles on the selected opening in multi-layout
    if (openingLayout === 'multi' && selectedOpeningId) {
      const activeOp = renderedOpenings.find(op => op.id === selectedOpeningId);
      if (activeOp) {
        const left = activeOp.x;
        const right = activeOp.x + activeOp.w;
        const top = activeOp.y;
        const bottom = activeOp.y + activeOp.h;
        const cx = activeOp.x + activeOp.w / 2;
        const cy = activeOp.y + activeOp.h / 2;
        const handles = [
          { name: 'nw', x: left, y: top },
          { name: 'n', x: cx, y: top },
          { name: 'ne', x: right, y: top },
          { name: 'e', x: right, y: cy },
          { name: 'se', x: right, y: bottom },
          { name: 's', x: cx, y: bottom },
          { name: 'sw', x: left, y: bottom },
          { name: 'w', x: left, y: cy }
        ];
        const clickedHandle = handles.find(h => Math.abs(x - h.x) <= 24 && Math.abs(y - h.y) <= 24);
        if (clickedHandle) {
          const op = customOpenings.find(o => o.id === selectedOpeningId);
          if (op) {
            dragging = true;
            dragType = 'multi-resize';
            activeResizeHandle = clickedHandle.name;
            startX = event.clientX;
            startY = event.clientY;
            startW = op.w;
            startH = op.h;
            startXOffset = op.x;
            startYOffset = op.y;
            return;
          }
        }
      }
    }
    
    // 2. Check for drag-moving an opening in multi-layout
    if (openingLayout === 'multi') {
      const clicked = [...renderedOpenings].reverse().find(op => {
        return x >= op.x && x <= op.x + op.w && y >= op.y && y <= op.y + op.h;
      });
      if (clicked) {
        selectedOpeningId = clicked.id;
        const op = customOpenings.find(o => o.id === selectedOpeningId);
        if (op) {
          dragging = true;
          dragType = 'multi-drag';
          startX = event.clientX;
          startY = event.clientY;
          startXOffset = op.x;
          startYOffset = op.y;
          syncMultiOpeningsList();
          renderMockup();
          return;
        }
      }
    }
    
    // 3. Spacing / Position handles
    const handle = mockupInteraction.handle;
    if (handle && x >= handle.x && x <= handle.x + handle.w && y >= handle.y && y <= handle.y + handle.h) {
      dragging = true;
      dragType = mockupInteraction.type;
      startX = event.clientX;
      startY = event.clientY;
      return;
    }
    const positionBox = mockupInteraction.positionBox;
    if (positionBox && x >= positionBox.x && x <= positionBox.x + positionBox.w && y >= positionBox.y && y <= positionBox.y + positionBox.h) {
      dragging = true;
      dragType = 'position';
      startX = event.clientX;
      startY = event.clientY;
    }
  });
  
  window.addEventListener('mouseup', () => {
    if (dragging && (dragType === 'multi-drag' || dragType === 'multi-resize')) {
      calcQuote();
    }
    dragging = false;
    dragType = null;
    activeResizeHandle = null;
  });
  
  window.addEventListener('mousemove', (event) => {
    const rect = canvas.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * canvas.width;
    const y = ((event.clientY - rect.top) / rect.height) * canvas.height;
    const openingLayout = document.getElementById('openingLayout')?.value || 'single';
    
    // Non-dragging cursor feedback
    if (!dragging) {
      if (openingLayout === 'multi' && selectedOpeningId) {
        const activeOp = renderedOpenings.find(op => op.id === selectedOpeningId);
        if (activeOp) {
          const left = activeOp.x;
          const right = activeOp.x + activeOp.w;
          const top = activeOp.y;
          const bottom = activeOp.y + activeOp.h;
          const cx = activeOp.x + activeOp.w / 2;
          const cy = activeOp.y + activeOp.h / 2;
          const handles = [
            { name: 'nw', x: left, y: top, cursor: 'nwse-resize' },
            { name: 'n', x: cx, y: top, cursor: 'ns-resize' },
            { name: 'ne', x: right, y: top, cursor: 'nesw-resize' },
            { name: 'e', x: right, y: cy, cursor: 'ew-resize' },
            { name: 'se', x: right, y: bottom, cursor: 'nwse-resize' },
            { name: 's', x: cx, y: bottom, cursor: 'ns-resize' },
            { name: 'sw', x: left, y: bottom, cursor: 'nesw-resize' },
            { name: 'w', x: left, y: cy, cursor: 'ew-resize' }
          ];
          const hoveredHandle = handles.find(h => Math.abs(x - h.x) <= 24 && Math.abs(y - h.y) <= 24);
          if (hoveredHandle) {
            canvas.style.cursor = hoveredHandle.cursor;
            return;
          }
        }
      }
      
      if (openingLayout === 'multi') {
        const hoveredOp = [...renderedOpenings].reverse().find(op => {
          return x >= op.x && x <= op.x + op.w && y >= op.y && y <= op.y + op.h;
        });
        if (hoveredOp) {
          canvas.style.cursor = 'move';
          return;
        }
      }
      
      canvas.style.cursor = 'default';
      return;
    }
    
    // Drag resizing in multi layout
    if (dragType === 'multi-resize') {
      const deltaInX = (event.clientX - startX) / Math.max(mockupInteraction.scale, 1);
      const deltaInY = (event.clientY - startY) / Math.max(mockupInteraction.scale, 1);
      
      const op = customOpenings.find(o => o.id === selectedOpeningId);
      if (op) {
        let newW = startW;
        let newH = startH;
        let newX = startXOffset;
        let newY = startYOffset;
        
        if (activeResizeHandle.includes('e')) {
          newW = Math.max(1.0, startW + deltaInX);
          newX = startXOffset + (newW - startW) / 2;
        }
        if (activeResizeHandle.includes('w')) {
          newW = Math.max(1.0, startW - deltaInX);
          newX = startXOffset - (newW - startW) / 2;
        }
        if (activeResizeHandle.includes('s')) {
          newH = Math.max(1.0, startH + deltaInY);
          newY = startYOffset - (newH - startH) / 2;
        }
        if (activeResizeHandle.includes('n')) {
          newH = Math.max(1.0, startH - deltaInY);
          newY = startYOffset + (newH - startH) / 2;
        }
        
        // Define temporary object to test bounds
        const tempOp = { w: newW, h: newH, x: newX, y: newY };
        const artW = Number(document.getElementById('qw')?.value || document.getElementById('imgW')?.value || 8);
        const artH = Number(document.getElementById('qh')?.value || document.getElementById('imgH')?.value || 10);
        const { matBorder } = getEffectiveOpeningOffsets();
        const matWIn = artW + (matBorder * 2);
        const matHIn = artH + (matBorder * 2);
        
        clampOpeningToBounds(tempOp, matWIn, matHIn, 1.0);
        
        // Apply changes
        op.w = Number(tempOp.w.toFixed(2));
        op.h = Number(tempOp.h.toFixed(2));
        op.x = Number(tempOp.x.toFixed(2));
        op.y = Number(tempOp.y.toFixed(2));
        
        syncMultiOpeningsList();
        updateMultiOpeningBoundingBox();
      }
      
      renderMockup();
      return;
    }
    
    // Drag moving in multi layout
    if (dragType === 'multi-drag') {
      const deltaInX = (event.clientX - startX) / Math.max(mockupInteraction.scale, 1);
      const deltaInY = (event.clientY - startY) / Math.max(mockupInteraction.scale, 1);
      
      const matchingOp = customOpenings.find(o => o.id === selectedOpeningId);
      if (matchingOp) {
        const tempOp = {
          w: matchingOp.w,
          h: matchingOp.h,
          x: startXOffset + deltaInX,
          y: startYOffset - deltaInY
        };
        
        // Apply clamping boundary!
        const artW = Number(document.getElementById('qw')?.value || document.getElementById('imgW')?.value || 8);
        const artH = Number(document.getElementById('qh')?.value || document.getElementById('imgH')?.value || 10);
        const { matBorder } = getEffectiveOpeningOffsets();
        const matWIn = artW + (matBorder * 2);
        const matHIn = artH + (matBorder * 2);
        
        clampOpeningToBounds(tempOp, matWIn, matHIn, 1.0);
        
        matchingOp.x = Number(tempOp.x.toFixed(2));
        matchingOp.y = Number(tempOp.y.toFixed(2));
        
        syncMultiOpeningsList();
        updateMultiOpeningBoundingBox();
      }
      
      renderMockup();
      return;
    }
    
    // Spacing
    if (dragType === 'spacing') {
      const deltaIn = (event.clientX - startX) / Math.max(mockupInteraction.scale, 1);
      const spacingInput = document.getElementById('openingSpacing');
      const current = Number(spacingInput.value || '1.5');
      spacingInput.value = Math.max(0.25, current + deltaIn).toFixed(2);
      startX = event.clientX;
      updateSelectionSummary();
      renderMockup();
      return;
    }
    
    // Position drag
    if (dragType === 'position') {
      const deltaInX = (event.clientX - startX) / Math.max(mockupInteraction.scale, 1);
      const deltaInY = (event.clientY - startY) / Math.max(mockupInteraction.scale, 1);
      const { matBorder } = getEffectiveOpeningOffsets();
      const offsetXInput = document.getElementById('openingOffsetX');
      const offsetYInput = document.getElementById('openingOffsetY');
      const currentX = Number(offsetXInput.value || '0');
      const currentY = Number(offsetYInput.value || '0');
      offsetXInput.value = clamp(currentX + deltaInX, -matBorder, matBorder).toFixed(2);
      offsetYInput.value = clamp(currentY - deltaInY, -matBorder, matBorder).toFixed(2);
      startX = event.clientX;
      startY = event.clientY;
      syncOpeningPositionInputs();
      updateSelectionSummary();
      renderMockup();
    }
  });
}

function debouncedDesignSearch() {
  window.clearTimeout(designSearchTimer);
  designSearchTimer = window.setTimeout(() => {
    searchCatalog();
  }, 120);
}

function scoreCatalogItem(item, query) {
  if (!query) return 0;
  const q = query.toLowerCase();
  const sku = catalogText(item, 'sku').toLowerCase();
  const name = catalogText(item, 'name').toLowerCase();
  if (sku === q) return 0;
  if (name === q) return 1;
  if (sku.startsWith(q)) return 2;
  if (name.startsWith(q)) return 3;
  if (sku.includes(q)) return 4;
  if (name.includes(q)) return 5;
  return 6;
}

function filterCatalogItems(items, query) {
  const q = (query || '').trim().toLowerCase();
  if (!q) {
    return [...items].sort((a, b) => {
      const aMoulding = catalogCategory(a).includes('mould');
      const bMoulding = catalogCategory(b).includes('mould');
      if (aMoulding && bMoulding) return compareCatalogBrowseOrder(a, b);
      return 0;
    });
  }
  return items
    .filter((item) => catalogText(item, 'sku').toLowerCase().includes(q)
      || catalogText(item, 'name').toLowerCase().includes(q)
      || catalogText(item, 'vendor').toLowerCase().includes(q))
    .sort((a, b) => {
      const scoreDiff = scoreCatalogItem(a, q) - scoreCatalogItem(b, q);
      if (scoreDiff) return scoreDiff;
      const aMoulding = catalogCategory(a).includes('mould');
      const bMoulding = catalogCategory(b).includes('mould');
      if (aMoulding && bMoulding) return compareCatalogBrowseOrder(a, b);
      return 0;
    });
}

async function importLocalCatalogPackage(source) {
  try {
    const fd = new FormData();
    fd.append('source', source);
    const data = await fetchJson('/api/catalog/import/package', { method: 'POST', body: fd });
    show(data);
    await searchCatalog(true);
    const previewText = Number.isFinite(Number(data.preview_count)) ? `, ${data.preview_count} previews linked` : '';
    const summary = `Last ${source} import: ${data.inserted} inserted, ${data.updated} updated, ${data.skipped} skipped${previewText}`;
    setNotice(summary, 'success');
    document.getElementById('catalogStats').textContent = summary;
    window.localStorage.setItem('studio-last-import', summary);
    window.localStorage.setItem('lastImportSummary', summary);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function importCatalog() {
  const fileInput = document.getElementById('catalogFile');
  if (!fileInput?.files?.length) {
    setNotice('Please select a CSV file first', 'error');
    return;
  }
  try {
    const fd = new FormData();
    fd.append('file', fileInput.files[0]);
    const data = await fetchJson('/api/catalog/import', { method: 'POST', body: fd });
    show(data);
    await searchCatalog(true);
    const summary = `Last CSV import: ${data.inserted} inserted, ${data.updated} updated, ${data.skipped} skipped`;
    setNotice(summary, 'success');
    document.getElementById('catalogStats').textContent = summary;
    window.localStorage.setItem('studio-last-import', summary);
    window.localStorage.setItem('lastImportSummary', summary);
    fileInput.value = '';
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function loadPricingSettings() {
  try {
    const data = await fetchJson('/api/settings');
    updatePricingInputs(data.pricing);
    show(data);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function savePricingSettings() {
  try {
    const fd = new FormData();
    fd.append('tax_rate', document.getElementById('settingTaxRate').value || '0');
    fd.append('markup_moulding', document.getElementById('settingMarkupMoulding').value || '0');
    fd.append('markup_mat', document.getElementById('settingMarkupMat').value || '0');
    fd.append('markup_glazing', document.getElementById('settingMarkupGlazing').value || '0');
    const data = await fetchJson('/api/settings', { method: 'POST', body: fd });
    updatePricingInputs(data.pricing);
    show(data);
    setNotice('Pricing rules saved.', 'success');
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function loadServiceOptions() {
  try {
    const data = await fetchJson('/api/services');
    updateServiceInputs(data.services);
    show(data);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function saveServiceOptions() {
  try {
    const fd = new FormData();
    SERVICE_ADMIN_ROWS.forEach(([key, prefix]) => {
      fd.append(`${key}_label`, document.getElementById(`${prefix}Label`).value || '');
      fd.append(`${key}_cost`, formatServicePriceInput(document.getElementById(`${prefix}Cost`).value));
      fd.append(`${key}_markup`, parseMarkupInput(document.getElementById(`${prefix}Markup`).value).toFixed(2));
      fd.append(`${key}_basis`, document.getElementById(`${prefix}Basis`).value || 'count');
      fd.append(`${key}_active`, document.getElementById(`${prefix}Active`).checked ? '1' : '0');
    });
    const data = await fetchJson('/api/services', { method: 'POST', body: fd });
    updateServiceInputs(data.services);
    show(data);
    setNotice('Manual pricing saved.', 'success');
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

function renderCatalogList(target, rows, type) {
  const root = document.getElementById(target);
  if (!root) return;
  if (!rows.length) {
    root.innerHTML = '<div class="material-results-empty">No match</div>';
    return;
  }
  const swatchColor = (item) => {
    if (type.includes('Mat')) return inferMatColor(item, type === 'topMat' ? 0 : type === 'secondMat' ? 1 : 2);
    if (type === 'moulding') return '#7a5939';
    return '#b9dfe7';
  };
  renderList(target, rows, {
    isSelected: (row) => selectedMaterials[type] === row.id,
    render: (item) => {
      const thumb = item.preview_url
        ? `<img src="${escapeHtml(item.preview_url)}" alt="" style="width:30px;height:30px;object-fit:cover;border-radius:8px;border:1px solid rgba(0,0,0,0.08);margin-right:8px;vertical-align:middle;background:#fff;" />`
        : `<span style="display:inline-block;width:10px;height:10px;border-radius:999px;background:${swatchColor(item)};margin-right:8px;border:1px solid rgba(0,0,0,0.12);vertical-align:middle;"></span>`;
      const faceLabel = type === 'moulding' ? 'face' : 'board';
      const photoLabel = type === 'moulding' && !item.preview_url ? 'No photo · ' : '';
      return `<strong>${thumb}${escapeHtml(item.sku)}</strong><span>${escapeHtml(item.name)}</span><small>${photoLabel}${item.vendor ? `${escapeHtml(item.vendor)} · ` : ''}${item.width_in ? `${formatInches(item.width_in)} in ${faceLabel} · ` : ''}cost ${formatCurrency(item.cost)}</small>`;
    },
    onClick: (item, div) => {
      pickMaterial(type, target, item, div);
    },
  });
}

function renderAdminCatalogList(target, rows) {
  if (!document.getElementById(target)) return;
  renderList(target, rows, {
    render: (item) => `<strong>${escapeHtml(item.sku)}</strong><span>${escapeHtml(item.name)}</span><small>${item.vendor ? `${escapeHtml(item.vendor)} · ` : ''}${escapeHtml(item.category)} · cost ${formatCurrency(item.cost)}</small>`,
    onClick: (item) => fillCatalogEditor(item),
  });
}

function updateCatalogStats() {
  const statsEl = document.getElementById('catalogStats');
  if (!statsEl) return;
  const counts = {};
  let previewCount = 0;
  catalogCache.forEach((item) => {
    const category = catalogCategory(item);
    const cat = category.includes('mould') ? 'Moulding'
      : category.includes('mat') ? 'Mat'
        : category.includes('glaz') ? 'Glazing'
          : 'Other';
    counts[cat] = (counts[cat] || 0) + 1;
    if (item.preview_url) {
      previewCount += 1;
    }
  });
  const parts = Object.entries(counts).map(([k, v]) => `${v} ${k}`);
  statsEl.textContent = parts.length ? `Catalog: ${parts.join(' · ')} · Preview coverage ${previewCount}/${catalogCache.length}` : '';
}

function renderOrderRow(order) {
  const next = orderNextAction(order);
  return `
    <button type="button" role="row" class="job-row${selectedOrderId === order.id ? ' selected' : ''}" data-order-id="${order.id}" aria-selected="${selectedOrderId === order.id}" onclick="selectOrder(${order.id}, this)">
      <strong>${escapeHtml(order.quote_number || `Q${String(order.id).padStart(5, '0')}`)}</strong>
      <span>${escapeHtml(order.customer_name || 'No customer')}</span>
      <span class="hide-mobile">${escapeHtml(order.customer_contact || '-')}</span>
      <span class="hide-mobile">${formatCurrency(order.total)}</span>
      <span class="hide-mobile">${formatCurrency(order.balance ?? order.total)}</span>
      <span class="hide-mobile">${escapeHtml(orderRowDate(order.created_at))}</span>
      <span class="job-status-pill">${escapeHtml(orderStatusLabel(order.status))}</span>
      <span class="job-action-pill">${escapeHtml(next.label)}</span>
    </button>
  `;
}

function getVisibleOrders() {
  const query = document.getElementById('orderSearch')?.value || '';
  const filtered = window.OrderTable.filterOrders(ordersCache, { stage: orderStage, query });
  return window.OrderTable.sortOrders(filtered, orderSortKey, orderSortDirection);
}

function renderOrdersTable() {
  const root = document.getElementById('ordersList');
  if (!root || !window.OrderTable) return;
  visibleOrdersCache = getVisibleOrders();
  root.innerHTML = visibleOrdersCache.length
    ? visibleOrdersCache.map((order) => renderOrderRow(order)).join('')
    : '<div class="orders-empty-state">No jobs match this filter.</div>';
  const summary = document.getElementById('ordersResultSummary');
  if (summary) summary.textContent = `Showing ${visibleOrdersCache.length} of ${ordersCache.length} jobs`;
  updateOrderSortHeaders();
  if (selectedOrderId && !visibleOrdersCache.some((order) => order.id === selectedOrderId)) {
    closeOrderInspector({ restoreFocus: false, clearSelection: true });
  }
}

function setOrderStage(stage) {
  orderStage = stage;
  document.querySelectorAll('[data-order-stage]').forEach((button) => {
    const active = button.dataset.orderStage === stage;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  renderOrdersTable();
}

function setOrderSort(key) {
  if (orderSortKey === key) {
    orderSortDirection = orderSortDirection === 'asc' ? 'desc' : 'asc';
  } else {
    orderSortKey = key;
    orderSortDirection = ['customer_name', 'customer_contact', 'status'].includes(key) ? 'asc' : 'desc';
  }
  renderOrdersTable();
}

function updateOrderSortHeaders() {
  document.querySelectorAll('[data-order-sort]').forEach((button) => {
    const active = button.dataset.orderSort === orderSortKey;
    button.setAttribute('aria-sort', active ? (orderSortDirection === 'asc' ? 'ascending' : 'descending') : 'none');
    const indicator = button.querySelector('span');
    if (indicator) indicator.textContent = active ? (orderSortDirection === 'asc' ? '▲' : '▼') : '↕';
  });
}

function orderStatusLabel(status) {
  return {
    quote: 'Quote',
    work_order: 'Work Order',
    invoice: 'Invoice',
  }[status] || status || 'Unknown';
}

function orderNextAction(order) {
  if (!order) return { label: 'Choose Job', status: '', tone: 'muted' };
  if (order.status === 'quote') return { label: 'Approve', status: 'work_order', tone: 'primary' };
  if (order.status === 'work_order') return { label: 'Mark Done', status: 'invoice', tone: 'primary' };
  if (order.status === 'invoice') return { label: 'View', status: '', tone: 'muted' };
  return { label: 'View', status: '', tone: 'muted' };
}

function orderRowDate(value) {
  if (!value) return '-';
  const parsed = new Date(String(value).replace(' ', 'T'));
  if (Number.isNaN(parsed.getTime())) return String(value);
  return parsed.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function setQuoteEditMode(order) {
  editingOrderId = order?.id || null;
  editingOrderNumber = order?.quote_number || '';
  const saveButton = document.getElementById('quoteSaveButton');
  if (saveButton) {
    saveButton.textContent = editingOrderId ? 'Update Saved Quote' : 'Save Quote';
    saveButton.title = editingOrderId
      ? 'Update this existing saved quote with the current Design values.'
      : 'Save the current quote into the Orders / Quotes workspace.';
  }
  const notice = document.getElementById('quoteEditNotice');
  if (notice) {
    notice.hidden = !editingOrderId;
    notice.textContent = editingOrderId ? `Editing ${editingOrderNumber}. Recalculate after changes, then update the saved quote.` : '';
  }
}

function clearQuoteEditMode() {
  setQuoteEditMode(null);
}

function renderCustomerRow(customer) {
  return `
    <div class="record-grid customers">
      <strong>${escapeHtml(customer.name)}</strong>
      <span>${escapeHtml(customer.contact || 'No contact yet')}</span>
      <span class="record-pill">${escapeHtml(String(customer.updated_at || '').slice(0, 10))}</span>
    </div>
  `;
}

function renderCustomerOrderRow(order) {
  return `
    <div class="record-grid orders">
      <strong>${escapeHtml(order.quote_number)}</strong>
      <span>${escapeHtml(order.status)}</span>
      <span class="record-pill">${escapeHtml(String(order.created_at || '').slice(0, 10))}</span>
      <span class="record-total">${formatCurrency(order.total)}</span>
    </div>
  `;
}

async function searchCatalog(forceRefresh = false) {
  try {
    await ensureCatalogCache(forceRefresh);
    const adminSearch = document.getElementById('adminCatalogSearch')?.value || '';
    const designSearch = document.getElementById('searchQ')?.value || document.getElementById('catalogDrawerSearch')?.value || '';

    const designItems = filterCatalogItems(catalogCache, designSearch);
    const adminItems = filterCatalogItems(catalogCache, adminSearch);
    const mouldings = designItems.filter((i) => catalogCategory(i).includes('mould'));
    const mats = designItems.filter((i) => catalogCategory(i).includes('mat'));
    const glazing = designItems.filter((i) => catalogCategory(i).includes('glaz'));
    const adminMouldings = adminItems.filter((i) => catalogCategory(i).includes('mould'));
    const adminMats = adminItems.filter((i) => catalogCategory(i).includes('mat'));
    const adminGlazing = adminItems.filter((i) => catalogCategory(i).includes('glaz'));
    renderCatalogList('glazingList', glazing.slice(0, 24), 'glazing');
    renderAdminCatalogList('adminMouldingList', adminMouldings.slice(0, 60));
    renderAdminCatalogList('adminMatList', adminMats.slice(0, 60));
    renderAdminCatalogList('adminGlazingList', adminGlazing.slice(0, 60));
    const status = document.getElementById('designSearchStatus');
    if (status) {
      status.textContent = `${mouldings.length} mouldings · ${mats.length} mats · ${glazing.length} glazing${designSearch ? ` for "${designSearch}"` : ''}`;
    }
    updateCatalogStats();
    renderAdminCatalogTable();
    if (document.getElementById('catalogDrawer')?.classList.contains('visible')) {
      renderCatalogDrawer();
    }
    populateServiceSelects();
    updateOptionPricePreviews(lastQuote?.line_items || null);
    show({ items: catalogCache, design_items: designItems, admin_items: adminItems });
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function saveCatalogItem() {
  try {
    const itemId = document.getElementById('catalogEditId').value || '';
    const fd = new FormData();
    fd.append('sku', document.getElementById('catalogEditSku').value || '');
    fd.append('name', document.getElementById('catalogEditName').value || '');
    fd.append('category', document.getElementById('catalogEditCategory').value || '');
    fd.append('vendor', document.getElementById('catalogEditVendor').value || '');
    fd.append('cost', document.getElementById('catalogEditCost').value || '0');
    fd.append('width_in', document.getElementById('catalogEditWidth').value || '0');
    fd.append('height_in', document.getElementById('catalogEditHeight').value || '0');
    fd.append('rabbet_in', document.getElementById('catalogEditRabbet').value || '0');
    fd.append('active', document.getElementById('catalogEditActive').value || '1');
    const url = itemId ? `/api/catalog/items/${itemId}` : '/api/catalog/items';
    const data = await fetchJson(url, { method: 'POST', body: fd });
    show(data);
    setNotice(itemId ? 'Catalog item updated.' : 'Catalog item created.', 'success');
    selectedCatalogItemId = Number(data.item_id || itemId) || null;
    await searchCatalog(true);
    const savedItem = catalogCache.find((item) => Number(item.id) === Number(selectedCatalogItemId));
    if (savedItem) fillCatalogEditor(savedItem);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

function loadCatalogTextureFile() {
  const input = document.getElementById('catalogTextureFile');
  if (!input || !input.files || !input.files[0]) return;
  const file = input.files[0];
  const img = new Image();
  img.onload = () => {
    adminTextureState.img = img;
    adminTextureState.bandHeight = Number(document.getElementById('catalogTextureBand')?.value || 35);
    adminTextureState.bandCenter = Number(document.getElementById('catalogTextureCenter')?.value || 50);
    renderCatalogTextureCrop();
  };
  img.src = URL.createObjectURL(file);
}

function updateCatalogTextureCrop() {
  adminTextureState.bandHeight = Number(document.getElementById('catalogTextureBand')?.value || 35);
  adminTextureState.bandCenter = Number(document.getElementById('catalogTextureCenter')?.value || 50);
  renderCatalogTextureCrop();
}

function renderCatalogTextureCrop() {
  const canvas = document.getElementById('catalogTextureCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!adminTextureState.img) {
    ctx.fillStyle = '#5f6b86';
    ctx.font = '12px Georgia';
    ctx.fillText('Load a texture photo to crop a strip.', 12, 24);
    return;
  }
  const img = adminTextureState.img;
  const scale = Math.min(canvas.width / img.width, canvas.height / img.height);
  const drawW = img.width * scale;
  const drawH = img.height * scale;
  const offsetX = (canvas.width - drawW) / 2;
  const offsetY = (canvas.height - drawH) / 2;
  ctx.drawImage(img, offsetX, offsetY, drawW, drawH);

  const bandHeight = clamp(adminTextureState.bandHeight, 10, 90) / 100;
  const bandCenter = clamp(adminTextureState.bandCenter, 10, 90) / 100;
  const bandH = drawH * bandHeight;
  const bandY = offsetY + (drawH * bandCenter) - (bandH / 2);

  ctx.fillStyle = 'rgba(16, 26, 40, 0.35)';
  ctx.fillRect(offsetX, offsetY, drawW, Math.max(0, bandY - offsetY));
  ctx.fillRect(offsetX, bandY + bandH, drawW, Math.max(0, offsetY + drawH - (bandY + bandH)));
  ctx.strokeStyle = 'rgba(32, 71, 79, 0.85)';
  ctx.lineWidth = 2;
  ctx.strokeRect(offsetX, bandY, drawW, bandH);
}

function getCatalogTextureBlob() {
  const img = adminTextureState.img;
  if (!img) return null;
  const bandHeight = clamp(adminTextureState.bandHeight, 10, 90) / 100;
  const bandCenter = clamp(adminTextureState.bandCenter, 10, 90) / 100;
  const cropH = Math.max(1, Math.round(img.height * bandHeight));
  const centerY = Math.round(img.height * bandCenter);
  const cropY = clamp(centerY - Math.round(cropH / 2), 0, Math.max(0, img.height - cropH));
  const cropCanvas = document.createElement('canvas');
  cropCanvas.width = img.width;
  cropCanvas.height = cropH;
  const cctx = cropCanvas.getContext('2d');
  cctx.drawImage(img, 0, cropY, img.width, cropH, 0, 0, img.width, cropH);
  return cropCanvas;
}

async function uploadCatalogTexture() {
  try {
    const itemId = document.getElementById('catalogEditId').value || '';
    if (!itemId) {
      setNotice('Save the item first, then upload a texture.', 'error');
      return;
    }
    const input = document.getElementById('catalogTextureFile');
    if (!input.files || !input.files[0]) {
      setNotice('Choose a texture photo first.', 'error');
      return;
    }
    const cropCanvas = getCatalogTextureBlob();
    if (!cropCanvas) {
      setNotice('Load a texture photo and crop the strip first.', 'error');
      return;
    }
    const fd = new FormData();
    const blob = await new Promise((resolve) => cropCanvas.toBlob(resolve, 'image/jpeg', 0.92));
    fd.append('file', blob, 'moulding_texture.jpg');
    const data = await fetchJson(`/api/catalog/items/${itemId}/texture`, { method: 'POST', body: fd });
    setNotice('Texture uploaded. Refresh the design tab to see the change.', 'success');
    show(data);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function listBackups() {
  try {
    const data = await fetchJson('/api/backups');
    renderList('backupList', data.backups, {
      render: (backup) => {
        const sizeMb = (Number(backup.size_bytes || 0) / 1048576).toFixed(1);
        const dateStr = new Date(backup.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
        const url = `/api/backups/${encodeURIComponent(backup.filename)}`;
        return `<strong>${escapeHtml(backup.filename)}</strong><span>${escapeHtml(dateStr)}</span><small>${sizeMb} MB</small><button type="button" class="secondary mini-button" style="width:auto;margin-top:6px;" onclick="event.stopPropagation(); window.open('${url}', '_blank')">Download</button>`;
      },
      onClick: (backup) => window.open(`/api/backups/${encodeURIComponent(backup.filename)}`, '_blank'),
    });
    show(data);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function createBackup() {
  try {
    const data = await fetchJson('/api/backups', { method: 'POST' });
    show(data);
    setNotice(`Backup created: ${data.filename}`, 'success');
    await listBackups();
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function uploadImage() {
  try {
    const file = document.getElementById('imageFile').files[0];
    if (!file) {
      setNotice('Choose an artwork file first.', 'error');
      return null;
    }
    await flushLocalPreviewRotation();
    const fd = new FormData();
    fd.append('file', file);
    fd.append('width_in', document.getElementById('imgW').value || '0');
    fd.append('height_in', document.getElementById('imgH').value || '0');
    fd.append('ratio_label', document.getElementById('ratioPreset').value || 'free');
    fd.append('rotation_deg', String(normalizeRotationInput()));
    fd.append('crop_json', JSON.stringify(getCropMetadataFromControls()));

    const data = await fetchJson('/api/images/upload', { method: 'POST', body: fd });
    show(data);
    selectedImageId = data.id;
    await listImages();
    const saved = imagesCache.find((img) => img.id === data.id) || data;
    pickImage(saved, document.querySelector(`#imageList .item[data-image-id="${data.id}"]`));
    setNotice('Artwork saved to gallery.', 'success');
    return saved;
  } catch (error) {
    setNotice(error.message, 'error');
    return null;
  }
}

async function updateSelectedImageMetadata(options = {}) {
  const { quiet = false, refreshList = true } = options;
  if (!selectedImageId) {
    setNotice('Select saved artwork before updating.', 'error');
    return null;
  }
  try {
    const fd = new FormData();
    fd.append('width_in', document.getElementById('imgW').value || '0');
    fd.append('height_in', document.getElementById('imgH').value || '0');
    fd.append('ratio_label', document.getElementById('ratioPreset').value || 'free');
    fd.append('crop_json', JSON.stringify(getCropMetadataFromControls()));
    const data = await fetchJson(`/api/images/${selectedImageId}`, { method: 'PATCH', body: fd });
    const index = imagesCache.findIndex((img) => img.id === selectedImageId);
    if (index >= 0) imagesCache[index] = data;
    activeArtworkCropJson = normalizeCropJson(data.crop_json);
    if (refreshList) {
      await listImages();
      const updated = imagesCache.find((img) => img.id === data.id) || data;
      pickImage(updated, document.querySelector(`#imageList .item[data-image-id="${data.id}"]`));
    } else {
      updateGalleryDetails(data);
      updateSelectionSummary();
      renderMockup();
    }
    show(data);
    if (!quiet) setNotice('Artwork metadata updated.', 'success');
    return data;
  } catch (error) {
    setNotice(error.message, 'error');
    return null;
  }
}

async function saveGalleryArtwork() {
  const file = document.getElementById('imageFile')?.files?.[0] || null;
  if (file || galleryMode === 'new') {
    await uploadImage();
    return;
  }
  await updateSelectedImageMetadata();
}

async function listImages() {
  try {
    const data = await fetchJson('/api/images');
    imagesCache = data.images;

    renderList('imageList', data.images, {
      isSelected: (img) => selectedImageId === img.id,
      dataset: (img) => ({ imageId: img.id }),
      render: (img) => `<img class="gallery-thumb" src="${escapeHtml(img.url)}" alt="" loading="lazy" /><div><strong>#${Number(img.id || 0)} ${escapeHtml(img.filename)}</strong><span>${formatInches(img.width_in)} x ${formatInches(img.height_in)} in</span><small>${escapeHtml(img.ratio_label || 'free')} · ${escapeHtml(img.created_at)}</small></div>`,
      onClick: (img, div) => pickImage(img, div),
    });

    const selectedImage = imagesCache.find((img) => img.id === selectedImageId);
    if (!selectedImage && selectedImageId) selectedImageId = null;
    updateGalleryDetails(selectedImage || null);
    updateSelectionSummary();
    renderOpeningArtworkPicker();
    show(data);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function calcQuote() {
  try {
    const fd = new FormData();
    fd.append('width_in', document.getElementById('qw').value || '0');
    fd.append('height_in', document.getElementById('qh').value || '0');
    fd.append('labor_flat', document.getElementById('labor').value || '0');
    fd.append('mat_border_in', document.getElementById('matBorder').value || '2');
    fd.append('image_id', selectedImageId || '');
    if (selectedMaterials.moulding) fd.append('moulding_id', selectedMaterials.moulding);
    if (selectedMaterials.topMat) {
      fd.append('top_mat_id', selectedMaterials.topMat);
      fd.append('mat_id', selectedMaterials.topMat);
    }
    if (document.getElementById('useSecondMat')?.checked && selectedMaterials.secondMat) {
      fd.append('second_mat_id', selectedMaterials.secondMat);
      fd.append('second_mat_reveal_in', document.getElementById('secondMatReveal').value || '0.25');
    }
    if (document.getElementById('useThirdMat')?.checked && selectedMaterials.thirdMat) {
      fd.append('third_mat_id', selectedMaterials.thirdMat);
      fd.append('third_mat_reveal_in', document.getElementById('thirdMatReveal').value || '0.25');
    }
    const glazingKey = document.getElementById('glazingType')?.value || '';
    if (glazingKey) fd.append('glazing_key', glazingKey);
    fd.append('global_discount_pct', document.getElementById('globalDiscount').value || '0');
    OPTION_SELECTS.forEach(({ key, selectId, countId }) => {
      const value = document.getElementById(selectId)?.value || '';
      if (value) fd.append(`${key}_key`, value);
      fd.append(`${key}_count`, document.getElementById(countId)?.value || '1');
      fd.append(`${key}_discount_pct`, '0');
    });
    fd.append('other_label', document.getElementById('otherLineLabel').value || '');
    fd.append('other_amount', document.getElementById('otherLineAmount').value || '0');
    fd.append('other_discount_pct', document.getElementById('otherLineDiscount').value || '0');
    fd.append('other2_label', document.getElementById('otherLine2Label').value || '');
    fd.append('other2_amount', document.getElementById('otherLine2Amount').value || '0');
    fd.append('other2_discount_pct', document.getElementById('otherLine2Discount').value || '0');

    lastQuote = await fetchJson('/api/quotes/calculate', { method: 'POST', body: fd });
    updateQuoteSummary(lastQuote);
    renderMockup();
    show(lastQuote);
    setNotice('Quote calculated.', 'success');
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function createOrder() {
  if (!lastQuote) {
    setNotice('Calculate quote first.', 'error');
    return;
  }
  try {
    const customerName = document.getElementById('customerName').value || '';
    const customerContact = document.getElementById('customerContact').value || '';
    const identityError = validateCustomerIdentity(customerName, customerContact);
    if (identityError) {
      setNotice(identityError, 'error');
      return;
    }
    const mockupImageDataUrl = getMockupSnapshotDataUrl();
    const fd = new FormData();
    fd.append('customer_name', customerName.trim());
    fd.append('customer_contact', customerContact.trim());
    const payload = buildOrderPayload(mockupImageDataUrl);
    fd.append('payload_json', JSON.stringify(payload));
    fd.append('subtotal', String(payload.subtotal));
    fd.append('tax', String(payload.tax));
    fd.append('total', String(payload.total));
    let data;
    if (editingOrderId) {
      fd.append('note', 'Saved quote contents updated from Design');
      data = await fetchJson(`/api/orders/${editingOrderId}`, { method: 'POST', body: fd });
      show(data);
      setNotice(`${editingOrderNumber || 'Quote'} updated.`, 'success');
      const updatedOrderId = editingOrderId;
      clearQuoteEditMode();
      await Promise.all([listOrders(), listCustomers()]);
      switchTab('orders');
      await selectOrder(updatedOrderId);
      return;
    }
    data = await fetchJson('/api/orders', { method: 'POST', body: fd });
    show(data);
    setNotice(`Quote ${data.quote_number} saved.`, 'success');
    await Promise.all([listOrders(), listCustomers()]);
    switchTab('orders');
    await selectOrder(data.order_id);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

function buildOrderPayload(mockupImageDataUrl = getMockupSnapshotDataUrl()) {
  return {
    ...lastQuote,
    design_state: {
      item_name: document.getElementById('designItemName').value || document.getElementById('activePresetLabel')?.textContent || 'Custom Framing',
      opening_layout: document.getElementById('openingLayout').value || 'single',
      opening_spacing: Number(document.getElementById('openingSpacing').value || '1.5'),
      opening_offset_x: Number(document.getElementById('openingOffsetX').value || '0'),
      opening_offset_y: Number(document.getElementById('openingOffsetY').value || '0'),
      opening_balance: Number(document.getElementById('openingBalance').value || '50'),
      second_mat_reveal_in: Number(document.getElementById('secondMatReveal').value || '0.25'),
      third_mat_reveal_in: Number(document.getElementById('thirdMatReveal').value || '0.25'),
      mockup_image_data_url: mockupImageDataUrl,
    },
    option_state: {
      global_discount_pct: Number(document.getElementById('globalDiscount').value || '0'),
      backing_key: document.getElementById('optionBacking').value || '',
      mounting_key: document.getElementById('optionMounting').value || '',
      frame_mounting_key: document.getElementById('optionFrameMounting').value || '',
      printing_key: document.getElementById('optionPrinting').value || '',
      various_key: document.getElementById('optionVarious').value || '',
      assembly_key: document.getElementById('optionAssembly').value || '',
      royalties_key: document.getElementById('optionRoyalties').value || '',
      custom_1_key: document.getElementById('optionCustom1').value || '',
      custom_2_key: document.getElementById('optionCustom2').value || '',
      other_label: document.getElementById('otherLineLabel').value || '',
      other_amount: Number(document.getElementById('otherLineAmount').value || '0'),
      other_discount_pct: Number(document.getElementById('otherLineDiscount').value || '0'),
      other2_label: document.getElementById('otherLine2Label').value || '',
      other2_amount: Number(document.getElementById('otherLine2Amount').value || '0'),
      other2_discount_pct: Number(document.getElementById('otherLine2Discount').value || '0'),
    },
  };
}

function getMockupSnapshotDataUrl() {
  const mockupCanvas = document.getElementById('mockupCanvas');
  if (!mockupCanvas) return '';
  const snapshot = document.createElement('canvas');
  snapshot.width = 720;
  snapshot.height = 560;
  const ctx = snapshot.getContext('2d');
  const cropX = mockupCanvas.width * 0.08;
  const cropY = mockupCanvas.height * 0.02;
  const cropW = mockupCanvas.width * 0.84;
  const cropH = mockupCanvas.height * 0.98;
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, snapshot.width, snapshot.height);
  ctx.drawImage(mockupCanvas, cropX, cropY, cropW, cropH, 0, 0, snapshot.width, snapshot.height);
  return snapshot.toDataURL('image/jpeg', 0.88);
}

function updateOrderCounts() {
  const counts = { quote: 0, work_order: 0, invoice: 0 };
  let revenue = 0;
  ordersCache.forEach((order) => {
    counts[order.status] = (counts[order.status] || 0) + 1;
    if (order.status === 'work_order' || order.status === 'invoice') {
      revenue += Number(order.total || 0);
    }
  });
  document.getElementById('summaryQuoteCount').textContent = counts.quote || 0;
  document.getElementById('summaryWorkOrderCount').textContent = counts.work_order || 0;
  document.getElementById('summaryInvoiceCount').textContent = counts.invoice || 0;
  const allCount = document.getElementById('summaryAllCount');
  if (allCount) allCount.textContent = ordersCache.length;
  const revElem = document.getElementById('summaryRevenueCount');
  if (revElem) {
    revElem.textContent = formatCurrency(revenue);
  }
}

function configureOrderLifecycleControls(order) {
  const select = document.getElementById('orderStatus');
  const hint = document.getElementById('orderLifecycleHint');
  if (!select) return;
  select.innerHTML = '';
  if (!order) {
    select.innerHTML = '<option value="">Select an order</option>';
    if (hint) hint.textContent = 'Select an order to see the next required action.';
    return;
  }

  const addOption = (value, label) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  };

  if (order.status === 'quote') {
    addOption('work_order', 'Approve quote -> work order');
    if (hint) hint.textContent = order.approved_at
      ? 'Quote approval is already recorded.'
      : 'Requires customer approval before the work order is created.';
    return;
  }
  if (order.status === 'work_order') {
    addOption('invoice', 'Mark done -> invoice');
    if (hint) hint.textContent = order.completed_at
      ? 'Completion is already recorded.'
      : 'Requires marking production done before invoice.';
    return;
  }
  if (order.status === 'invoice') {
    addOption('work_order', 'Return to work order');
    addOption('invoice', 'Keep as invoice');
    if (hint) hint.textContent = 'Returning to work order clears the done marker so production changes are tracked.';
    return;
  }
  addOption(order.status, order.status);
  if (hint) hint.textContent = 'No lifecycle action available.';
}

function renderOrderDetail(data) {
  const { order, history } = data;
  selectedOrderDetail = order;
  const selected = order.payload?.selected || {};
  const lineItems = order.payload?.line_items || {};
  const designState = order.payload?.design_state || {};
  document.getElementById('orderDetailTitle').textContent = order.quote_number;
  document.getElementById('orderCustomer').textContent = order.customer_name;
  document.getElementById('orderContact').textContent = order.customer_contact || '-';
  document.getElementById('orderStatusLabel').textContent = orderStatusLabel(order.status);
  document.getElementById('orderTotal').textContent = formatCurrency(order.total);
  document.getElementById('orderCreated').textContent = order.created_at;
  document.getElementById('orderEditCustomerName').value = order.customer_name;
  document.getElementById('orderEditCustomerContact').value = order.customer_contact || '';
  document.getElementById('orderEditCustomerEmail').value = order.customer_email || '';
  document.getElementById('orderSelectedImage').textContent = selected.image_id ? `Image #${selected.image_id}` : '-';
  document.getElementById('orderSelectedLayout').textContent = designState.opening_layout === 'diptych'
    ? `2 openings · ${designState.opening_spacing || 1.5} in spacing · ${designState.opening_balance || 50}% balance`
    : 'single opening';
  document.getElementById('orderSelectedOffsetX').textContent = `Pos X ${Number(designState.opening_offset_x || 0).toFixed(2)} in · Pos Y ${Number(designState.opening_offset_y || 0).toFixed(2)} in`;
  document.getElementById('orderSelectedMoulding').textContent = selected.moulding ? `${selected.moulding.sku} · ${selected.moulding.name}` : '-';
  const matSummary = (selected.mats || []).length
    ? selected.mats.map((layer) => getMatLayerDisplay(layer)).join(' | ')
    : selected.mat ? `${selected.mat.sku} · ${selected.mat.name}` : '-';
  document.getElementById('orderSelectedMat').textContent = matSummary;
  document.getElementById('orderSelectedGlazing').textContent = selected.glazing ? `${selected.glazing.name || selected.glazing.sku}` : '-';

  renderList('orderHistory', history, {
    render: (entry) => `<strong>${escapeHtml(entry.status)}</strong><span>${escapeHtml(entry.note || 'Status change')}</span><small>${escapeHtml(entry.created_at)}</small>`,
  });
  const lineItemRoot = document.getElementById('orderLineItems');
  lineItemRoot.innerHTML = '';
  if (!Object.keys(lineItems).length) {
    lineItemRoot.innerHTML = '<li>No line items stored.</li>';
  } else {
    Object.entries(lineItems).forEach(([label, value]) => {
      const li = document.createElement('li');
      li.textContent = `${label.replace(/_/g, ' ')}: ${formatCurrency(value)}`;
      lineItemRoot.appendChild(li);
    });
  }

  configureOrderLifecycleControls(order);
  const primary = document.getElementById('orderPrimaryAction');
  if (primary) {
    const next = orderNextAction(order);
    primary.textContent = next.label;
    primary.disabled = !next.status;
  }
  updateSidebarSelection(order);
}

async function saveOrderEdits() {
  if (!selectedOrderId) {
    setNotice('Select an order first.', 'error');
    return;
  }
  try {
    const customerName = document.getElementById('orderEditCustomerName').value || '';
    const customerContact = document.getElementById('orderEditCustomerContact').value || '';
    const customerEmail = document.getElementById('orderEditCustomerEmail').value || '';
    const identityError = validateCustomerIdentity(customerName, customerContact);
    if (identityError) {
      setNotice(identityError, 'error');
      return;
    }
    const fd = new FormData();
    fd.append('customer_name', customerName.trim());
    fd.append('customer_contact', customerContact.trim());
    fd.append('customer_email', customerEmail.trim());
    fd.append('note', 'Order detail edited from workspace');
    const data = await fetchJson(`/api/orders/${selectedOrderId}`, { method: 'POST', body: fd });
    show(data);
    setNotice('Order detail updated.', 'success');
    await Promise.all([listOrders(), listCustomers()]);
    await selectOrder(selectedOrderId);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

function openOrderInspector(trigger = null) {
  const inspector = document.getElementById('orderInspector');
  const backdrop = document.getElementById('orderInspectorBackdrop');
  if (!inspector || !backdrop) return;
  orderInspectorReturnFocus = trigger?.isConnected
    ? trigger
    : document.querySelector(`[data-order-id="${selectedOrderId}"]`);
  backdrop.hidden = false;
  inspector.classList.add('open');
  inspector.setAttribute('aria-hidden', 'false');
  document.body.classList.add('order-inspector-open');
  inspector.focus({ preventScroll: true });
}

function closeOrderInspector({ restoreFocus = true, clearSelection = false } = {}) {
  const inspector = document.getElementById('orderInspector');
  const backdrop = document.getElementById('orderInspectorBackdrop');
  if (!inspector || !backdrop) return;
  inspector.classList.remove('open');
  inspector.setAttribute('aria-hidden', 'true');
  backdrop.hidden = true;
  document.body.classList.remove('order-inspector-open');
  if (clearSelection) {
    selectedOrderId = null;
    selectedOrderDetail = null;
    handoffCache = null;
    updateSidebarSelection(null);
    configureOrderLifecycleControls(null);
    renderOrdersTable();
  }
  if (restoreFocus && orderInspectorReturnFocus?.isConnected) orderInspectorReturnFocus.focus();
  orderInspectorReturnFocus = null;
}

function showOrderInspectorTab(tab) {
  document.querySelectorAll('[data-inspector-tab]').forEach((button) => {
    const active = button.dataset.inspectorTab === tab;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
  });
  document.querySelectorAll('[data-inspector-pane]').forEach((pane) => {
    pane.classList.toggle('active', pane.dataset.inspectorPane === tab);
  });
  if (tab === 'handoff' && selectedOrderId && !handoffCache) loadOrderHandoff();
}

async function selectOrder(orderId, trigger = null) {
  selectedOrderId = orderId;
  clearOrderDocumentPreview();
  const attachmentNote = document.getElementById('handoffAttachmentNote');
  if (attachmentNote) attachmentNote.hidden = true;
  renderOrdersTable();

  try {
    const data = await fetchJson(`/api/orders/${orderId}`);
    renderOrderDetail(data);
    handoffCache = null;
    await loadOrderHandoff(false);
    showOrderInspectorTab('overview');
    openOrderInspector(trigger);
    show(data);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function listOrders(forceRefresh = false) {
  try {
    const data = await fetchJson('/api/orders');
    ordersCache = data.orders;
    updateOrderCounts();
    renderOrdersTable();
    if (forceRefresh) setNotice('Orders refreshed.', 'success');
    show(data);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

function debouncedOrderSearch() {
  window.clearTimeout(orderSearchTimer);
  orderSearchTimer = window.setTimeout(() => {
    renderOrdersTable();
  }, 180);
}

async function runPrimaryOrderAction(orderId = selectedOrderId) {
  const order = orderId === selectedOrderId
    ? selectedOrderDetail
    : ordersCache.find((entry) => entry.id === orderId);
  const next = orderNextAction(order);
  if (!orderId || !next.status) {
    if (orderId) await selectOrder(orderId);
    return;
  }
  if (orderId !== selectedOrderId) {
    await selectOrder(orderId);
  }
  const select = document.getElementById('orderStatus');
  if (select) select.value = next.status;
  await setStatus();
}

async function editSelectedOrderQuote() {
  if (!selectedOrderId) {
    setNotice('Select an order first.', 'error');
    return;
  }
  try {
    const data = selectedOrderDetail?.id === selectedOrderId
      ? { order: selectedOrderDetail }
      : await fetchJson(`/api/orders/${selectedOrderId}`);
    await loadOrderIntoDesign(data.order);
    switchTab('design');
    scrollDesignBuilderIntoView();
    setNotice(`${data.order.quote_number} loaded for editing. Recalculate after changes, then update the saved quote.`, 'success');
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function loadOrderIntoDesign(order) {
  const payload = order.payload || {};
  const selected = payload.selected || {};
  const designState = payload.design_state || {};
  const optionState = payload.option_state || {};
  await ensureCatalogCache();

  setQuoteEditMode(order);
  lastQuote = payload;
  document.getElementById('customerName').value = order.customer_name || '';
  document.getElementById('customerContact').value = order.customer_contact || '';
  document.getElementById('qw').value = selected.subject_width_in || payload.width_in || 8;
  document.getElementById('qh').value = selected.subject_height_in || payload.height_in || 10;
  document.getElementById('imgW').value = selected.subject_width_in || payload.width_in || 8;
  document.getElementById('imgH').value = selected.subject_height_in || payload.height_in || 10;
  document.getElementById('matBorder').value = selected.mat_border_in ?? 2;
  document.getElementById('labor').value = Number(payload.line_items?.labor || 0).toFixed(2);
  document.getElementById('designItemName').value = designState.item_name || 'Custom Framing';
  document.getElementById('openingLayout').value = designState.opening_layout || 'single';
  document.getElementById('openingSpacing').value = designState.opening_spacing ?? 1.5;
  document.getElementById('openingOffsetX').value = designState.opening_offset_x ?? 0;
  document.getElementById('openingOffsetY').value = designState.opening_offset_y ?? 0;
  document.getElementById('openingBalance').value = designState.opening_balance ?? 50;
  document.getElementById('secondMatReveal').value = designState.second_mat_reveal_in ?? 0.25;
  document.getElementById('thirdMatReveal').value = designState.third_mat_reveal_in ?? 0.25;

  const matLayers = selected.mats || [];
  const topLayer = matLayers.find((layer) => layer.slot === 'top');
  const secondLayer = matLayers.find((layer) => layer.slot === 'second');
  const thirdLayer = matLayers.find((layer) => layer.slot === 'third');
  selectedMaterials.moulding = selected.moulding?.id || null;
  selectedMaterials.topMat = topLayer?.item?.id || selected.mat?.id || null;
  selectedMaterials.secondMat = secondLayer?.item?.id || null;
  selectedMaterials.thirdMat = thirdLayer?.item?.id || null;
  selectedMaterials.glazing = null;
  document.getElementById('useSecondMat').checked = Boolean(selectedMaterials.secondMat);
  document.getElementById('useThirdMat').checked = Boolean(selectedMaterials.thirdMat);

  selectedImageId = selected.image_id || null;
  if (selectedImageId) {
    const image = imagesCache.find((entry) => entry.id === selectedImageId);
    if (image) {
      updateGalleryDetails(image);
      loadImageFromUrl(image.url, false);
    }
  }

  document.getElementById('globalDiscount').value = optionState.global_discount_pct ?? selected.global_discount_pct ?? 0;
  OPTION_SELECTS.forEach(({ key, selectId, countId }) => {
    const addon = selected.addons?.[key] || {};
    document.getElementById(selectId).value = optionState[`${key}_key`] || addon.service?.key || '';
    document.getElementById(countId).value = addon.count ?? 1;
  });
  document.getElementById('glazingType').value = selected.glazing?.key || optionState.glazing_key || '';
  document.getElementById('otherLineLabel').value = optionState.other_label || selected.addons?.custom?.[0]?.label || '';
  document.getElementById('otherLineAmount').value = optionState.other_amount ?? selected.addons?.custom?.[0]?.amount ?? 0;
  document.getElementById('otherLineDiscount').value = optionState.other_discount_pct ?? selected.addons?.custom?.[0]?.discount_pct ?? 0;
  document.getElementById('otherLine2Label').value = optionState.other2_label || selected.addons?.custom?.[1]?.label || '';
  document.getElementById('otherLine2Amount').value = optionState.other2_amount ?? selected.addons?.custom?.[1]?.amount ?? 0;
  document.getElementById('otherLine2Discount').value = optionState.other2_discount_pct ?? selected.addons?.custom?.[1]?.discount_pct ?? 0;

  populateCustomerSelect();
  syncMatLayerUI();
  syncOpeningPositionInputs();
  updatePresetUI();
  updateSelectionSummary();
  updateOptionPricePreviews(payload.line_items || null);
  updateQuoteSummary(payload);
  renderMockup();
  commitDesignHistorySnapshot();
}

async function setStatus() {
  if (!selectedOrderId) {
    setNotice('Select an order first.', 'error');
    return;
  }
  try {
    const status = document.getElementById('orderStatus').value;
    const fd = new FormData();
    fd.append('status', status);
    if (selectedOrderDetail?.status === 'quote' && status === 'work_order') {
      fd.append('customer_approved', '1');
      fd.append('note', 'Customer approved quote; work order created');
    } else if (selectedOrderDetail?.status === 'work_order' && status === 'invoice') {
      fd.append('work_completed', '1');
      fd.append('note', 'Work order marked done; invoice created');
    } else if (selectedOrderDetail?.status === 'invoice' && status === 'work_order') {
      fd.append('note', 'Invoice returned to work order for production changes');
    } else {
      fd.append('note', 'Updated from workspace panel');
    }
    const data = await fetchJson(`/api/orders/${selectedOrderId}/status`, { method: 'POST', body: fd });
    show(data);
    setNotice(`Order moved to ${orderStatusLabel(status)}.`, 'success');
    await listOrders();
    await selectOrder(selectedOrderId);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

function exportOrder(format, documentType = '') {
  if (!selectedOrderId) {
    setNotice('Select an order first.', 'error');
    return;
  }
  const params = new URLSearchParams({ format });
  if (documentType) {
    params.set('document', documentType);
  }
  window.open(`/api/orders/${selectedOrderId}/export?${params.toString()}`, '_blank');
}

function buildOrderExportUrl(format, documentType = '', disposition = 'attachment') {
  if (!selectedOrderId) return '';
  const params = new URLSearchParams({ format, disposition });
  if (documentType) params.set('document', documentType);
  return `/api/orders/${selectedOrderId}/export?${params.toString()}`;
}

function clearOrderDocumentPreview() {
  previewedOrderDocument = null;
  const root = document.getElementById('orderDocumentPreview');
  const pdf = document.getElementById('documentPdfPreview');
  const image = document.getElementById('documentImagePreview');
  const loading = document.getElementById('documentPreviewLoading');
  if (root) root.hidden = true;
  if (pdf) {
    pdf.hidden = true;
    pdf.removeAttribute('src');
  }
  if (image) {
    image.hidden = true;
    image.removeAttribute('src');
  }
  if (loading) loading.hidden = false;
}

function previewOrderDocument(format, documentType, label) {
  if (!selectedOrderId) {
    setNotice('Select an order first.', 'error');
    return;
  }
  const inlineUrl = buildOrderExportUrl(format, documentType, 'inline');
  const downloadUrl = buildOrderExportUrl(format, documentType, 'attachment');
  previewedOrderDocument = { format, documentType, label, inlineUrl, downloadUrl };

  const root = document.getElementById('orderDocumentPreview');
  const title = document.getElementById('documentPreviewTitle');
  const download = document.getElementById('documentDownloadLink');
  const open = document.getElementById('documentOpenLink');
  const loading = document.getElementById('documentPreviewLoading');
  const pdf = document.getElementById('documentPdfPreview');
  const image = document.getElementById('documentImagePreview');
  root.hidden = false;
  title.textContent = `${selectedOrderDetail?.quote_number || 'Selected job'} · ${label}`;
  download.href = downloadUrl;
  open.href = inlineUrl;
  loading.hidden = false;
  pdf.hidden = true;
  image.hidden = true;

  if (format === 'pdf') {
    pdf.onload = () => { loading.hidden = true; };
    pdf.src = inlineUrl;
    pdf.hidden = false;
  } else {
    image.onload = () => { loading.hidden = true; };
    image.onerror = () => {
      loading.hidden = false;
      loading.textContent = 'Could not render this preview.';
    };
    image.src = inlineUrl;
    image.hidden = false;
  }
  root.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function sendPreviewedDocument() {
  if (!previewedOrderDocument) {
    setNotice('Choose a document to preview first.', 'error');
    return;
  }
  showOrderInspectorTab('handoff');
  if (!handoffCache) await loadOrderHandoff(false);
  const note = document.getElementById('handoffAttachmentNote');
  if (note) {
    note.hidden = false;
    note.textContent = `Selected attachment: ${previewedOrderDocument.label}. Download it from Files, then attach it to the email or message manually.`;
  }
  setNotice(`${previewedOrderDocument.label} selected for handoff.`, 'success');
}

async function refreshOrderHistory() {
  if (!selectedOrderId) return;
  try {
    const data = await fetchJson(`/api/orders/${selectedOrderId}`);
    renderList('orderHistory', data.history, {
      render: (entry) => `<strong>${escapeHtml(entry.status)}</strong><span>${escapeHtml(entry.note || 'Status change')}</span><small>${escapeHtml(entry.created_at)}</small>`,
    });
  } catch (e) {
    console.error(e);
  }
}

function syncHandoffDraftFromFields() {
  if (!handoffCache) return;
  handoffCache.customer_email = document.getElementById('handoffEmail')?.value.trim() || '';
  handoffCache.customer_phone = document.getElementById('handoffPhone')?.value.trim() || '';
  handoffCache.email_subject = document.getElementById('handoffSubject')?.value || '';
  handoffCache.email_body = document.getElementById('handoffEmailBody')?.value || '';
  handoffCache.sms_body = document.getElementById('handoffSmsBody')?.value || '';
  updateHandoffActionState();
}

function renderOrderHandoffDraft() {
  if (!handoffCache) return;
  document.getElementById('handoffEmail').value = handoffCache.customer_email || '';
  document.getElementById('handoffPhone').value = handoffCache.customer_phone || handoffCache.customer_contact || '';
  document.getElementById('handoffSubject').value = handoffCache.email_subject || '';
  document.getElementById('handoffEmailBody').value = handoffCache.email_body || '';
  document.getElementById('handoffSmsBody').value = handoffCache.sms_body || '';
  updateHandoffActionState();
}

function updateHandoffActionState() {
  const email = document.getElementById('handoffEmail')?.value.trim() || '';
  const phone = document.getElementById('handoffPhone')?.value.trim() || '';
  const emailDraftButton = document.getElementById('emailDraftButton');
  const copyEmailButton = document.getElementById('copyEmailButton');
  const copySmsButton = document.getElementById('copySmsButton');
  if (emailDraftButton) emailDraftButton.disabled = !email.includes('@');
  if (copyEmailButton) copyEmailButton.disabled = !handoffCache;
  if (copySmsButton) copySmsButton.disabled = !handoffCache || !phone;
}

async function loadOrderHandoff(showNotice = true) {
  if (!selectedOrderId) {
    setNotice('Select an order first.', 'error');
    return;
  }
  try {
    const data = await fetchJson(`/api/orders/${selectedOrderId}/handoff`);
    handoffCache = { ...data, original: { ...data } };
    renderOrderHandoffDraft();
    show(data);
    if (showNotice) setNotice('Handoff draft reset to the saved order details.', 'success');
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

function resetOrderHandoff() {
  if (!handoffCache?.original) {
    loadOrderHandoff();
    return;
  }
  const original = handoffCache.original;
  handoffCache = { ...original, original };
  renderOrderHandoffDraft();
  setNotice('Handoff draft reset.', 'success');
}

async function copyText(text) {
  if (navigator.clipboard?.writeText && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand('copy');
  textarea.remove();
  if (!copied) throw new Error('Clipboard copy was blocked');
}

async function recordOrderNote(note) {
  const fd = new FormData();
  fd.append('note', note);
  await fetchJson(`/api/orders/${selectedOrderId}/notes`, { method: 'POST', body: fd });
  await refreshOrderHistory();
}

function openEmailDraft() {
  if (!handoffCache) {
    setNotice('Open a job before preparing handoff.', 'error');
    return;
  }
  syncHandoffDraftFromFields();
  if (!handoffCache.customer_email.includes('@')) {
    setNotice('Enter the customer email address first.', 'error');
    return;
  }
  const to = encodeURIComponent(handoffCache.customer_email);
  const subject = encodeURIComponent(handoffCache.email_subject);
  const body = encodeURIComponent(handoffCache.email_body);
  window.location.href = `mailto:${to}?subject=${subject}&body=${body}`;
  recordOrderNote(`Email draft opened for ${handoffCache.customer_email}`).catch((error) => setNotice(error.message, 'error'));
}

async function copyEmailText() {
  if (!handoffCache) return;
  syncHandoffDraftFromFields();
  const text = `To: ${handoffCache.customer_email || '(enter recipient)'}\nSubject: ${handoffCache.email_subject}\n\n${handoffCache.email_body}`;
  try {
    await copyText(text);
    await recordOrderNote('Email handoff text copied');
    setNotice('Email draft copied.', 'success');
  } catch (error) {
    setNotice(`Could not copy email draft: ${error.message}`, 'error');
  }
}

async function copySmsText() {
  if (!handoffCache) {
    setNotice('Open a job before preparing handoff.', 'error');
    return;
  }
  syncHandoffDraftFromFields();
  try {
    await copyText(handoffCache.sms_body);
    await recordOrderNote(`SMS handoff text copied for ${handoffCache.customer_phone || 'manual contact'}`);
    setNotice('SMS text copied.', 'success');
  } catch (error) {
    setNotice(`Could not copy SMS text: ${error.message}`, 'error');
  }
}

function loadLocalPreview() {
  const input = document.getElementById('imageFile');
  const rotation = document.getElementById('rotateDeg');
  input.onchange = () => {
    const file = input.files[0];
    if (!file) return;
    selectedImageId = null;
    galleryMode = 'new';
    document.querySelectorAll('#imageList .item').forEach((n) => n.classList.remove('selected'));
    updateGalleryDetails(null);
    loadLocalPreviewImage(true).catch((error) => setNotice(error.message, 'error'));
  };
  rotation?.addEventListener('input', scheduleLocalPreviewRotation);
  rotation?.addEventListener('change', () => {
    const rotationValue = normalizeRotationInput();
    if (galleryMode === 'edit') {
      rotateArtworkCropperTo(rotationValue);
    } else if (input.files[0]) {
      loadLocalPreviewImage(true, { normalizeRotation: false }).catch((error) => setNotice(error.message, 'error'));
    }
  });
}

function bindDesignInputs() {
  const dimensionIds = new Set(['qw', 'qh', 'imgW', 'imgH']);
  ['qw', 'qh', 'matBorder', 'imgW', 'imgH', 'openingSpacing', 'openingLayout', 'openingOffsetX', 'openingOffsetY', 'openingBalance', 'secondMatReveal', 'thirdMatReveal'].forEach((id) => {
    document.getElementById(id).addEventListener('input', () => {
      if (id === 'qw') document.getElementById('imgW').value = document.getElementById('qw').value;
      if (id === 'qh') document.getElementById('imgH').value = document.getElementById('qh').value;
      if (id === 'imgW') document.getElementById('qw').value = document.getElementById('imgW').value;
      if (id === 'imgH') document.getElementById('qh').value = document.getElementById('imgH').value;
      if (['qw', 'qh', 'imgW', 'imgH', 'matBorder'].includes(id)) {
        invalidateQuote();
      }
      if (dimensionIds.has(id)) {
        syncCropRatioFromArtworkSize(false);
        syncCropperAspectRatio();
      }
      syncOpeningPositionInputs(id);
      updateSelectionSummary();
      renderMockup();
      scheduleDesignHistorySnapshot();
    });
  });
  [
    ...OPTION_SELECTS.flatMap(({ selectId, countId }) => [selectId, countId]),
    'glazingType',
    'otherLineLabel', 'otherLineAmount', 'otherLineDiscount',
    'otherLine2Label', 'otherLine2Amount', 'otherLine2Discount', 'globalDiscount',
  ].forEach((id) => {
    const node = document.getElementById(id);
    if (!node) return;
    node.addEventListener('input', () => {
      lastQuote = null;
      updateQuoteSummary(null);
    });
    node.addEventListener('change', () => {
      lastQuote = null;
      updateQuoteSummary(null);
      updateOptionPricePreviews();
    });
  });
  document.querySelectorAll('.admin-service-price').forEach((node) => {
    node.addEventListener('blur', () => {
      node.value = formatServicePriceInput(node.value);
    });
  });
  document.querySelectorAll('.admin-service-markup').forEach((node) => {
    node.addEventListener('blur', () => {
      node.value = parseMarkupInput(node.value).toFixed(2);
    });
  });
}

function populateCustomerSelect() {
  const customer = customersCache.find((entry) => entry.id === selectedCustomerId);
  const status = document.getElementById('designCustomerStatus');
  if (status) {
    status.textContent = customer
      ? `Selected: ${customer.name}${customer.contact ? ` · ${customer.contact}` : ''}`
      : 'No saved customer selected.';
  }
}

function selectDesignCustomer(customerId) {
  const customer = customersCache.find((entry) => entry.id === Number(customerId));
  if (!customer) return;
  selectedCustomerId = customer.id;
  inlineCustomerPreviousId = null;
  document.getElementById('customerName').value = customer.name;
  document.getElementById('customerContact').value = customer.contact || '';
  document.getElementById('designCustomerSearch').value = '';
  document.getElementById('inlineCustomerEmail').value = customer.customer_email || '';
  document.getElementById('inlineCustomerCreate').hidden = true;
  document.getElementById('designCustomerResults').hidden = true;
  populateCustomerSelect();
  scheduleDesignHistorySnapshot();
}

function renderDesignCustomerMatches() {
  const query = document.getElementById('designCustomerSearch')?.value || '';
  const results = document.getElementById('designCustomerResults');
  if (!results) return;
  const matches = window.CustomerUI?.filterCustomerMatches(customersCache, query, 6) || [];
  if (!query.trim()) {
    results.hidden = true;
    results.innerHTML = '';
    return;
  }
  results.innerHTML = matches.length
    ? matches.map((customer) => `
      <button type="button" class="secondary customer-picker-result" role="option" onclick="selectDesignCustomer(${Number(customer.id)})">
        <span><strong>${escapeHtml(customer.name)}</strong><br><small>${escapeHtml(customer.customer_email || 'No email')}</small></span>
        <small>${escapeHtml(customer.contact || '')}</small>
      </button>`).join('')
    : '<div class="customer-picker-status">No matching customer. Use New customer to add them here.</div>';
  results.hidden = false;
}

function beginInlineCustomer() {
  inlineCustomerPreviousId = selectedCustomerId;
  selectedCustomerId = null;
  document.getElementById('customerName').value = '';
  document.getElementById('customerContact').value = '';
  document.getElementById('inlineCustomerEmail').value = '';
  document.getElementById('designCustomerSearch').value = '';
  document.getElementById('designCustomerResults').hidden = true;
  document.getElementById('inlineCustomerCreate').hidden = false;
  populateCustomerSelect();
  document.getElementById('customerName').focus();
}

function cancelInlineCustomer() {
  document.getElementById('inlineCustomerCreate').hidden = true;
  if (inlineCustomerPreviousId) {
    const previousId = inlineCustomerPreviousId;
    inlineCustomerPreviousId = null;
    selectDesignCustomer(previousId);
    return;
  }
  populateCustomerSelect();
}

async function saveInlineCustomer() {
  const name = document.getElementById('customerName').value || '';
  const contact = document.getElementById('customerContact').value || '';
  const customerEmail = document.getElementById('inlineCustomerEmail').value || '';
  const identityError = validateCustomerIdentity(name, contact);
  if (identityError) {
    setNotice(identityError, 'error');
    return;
  }
  try {
    const fd = new FormData();
    fd.append('name', name.trim());
    fd.append('contact', contact.trim());
    fd.append('customer_email', customerEmail.trim());
    const data = await fetchJson('/api/customers', { method: 'POST', body: fd });
    const customer = {
      id: Number(data.customer_id),
      name: name.trim(),
      contact: contact.trim(),
      customer_email: customerEmail.trim(),
    };
    customersCache = [customer, ...customersCache.filter((entry) => entry.id !== customer.id)];
    selectDesignCustomer(customer.id);
    setNotice(`Customer ${customer.name} saved and selected.`, 'success');
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function createCustomer() {
  try {
    const name = document.getElementById('newCustomerName').value || '';
    const contact = document.getElementById('newCustomerContact').value || '';
    const identityError = validateCustomerIdentity(name, contact);
    if (identityError) {
      setNotice(identityError, 'error');
      return;
    }
    const fd = new FormData();
    fd.append('name', name.trim());
    fd.append('contact', contact.trim());
    fd.append('notes', document.getElementById('newCustomerNotes').value || '');
    const data = await fetchJson('/api/customers', { method: 'POST', body: fd });
    show(data);
    document.getElementById('newCustomerName').value = '';
    document.getElementById('newCustomerContact').value = '';
    document.getElementById('newCustomerNotes').value = '';
    setNotice('Customer saved.', 'success');
    await listCustomers();
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

function renderCustomerDetail(data) {
  const customer = data.customer;
  document.getElementById('customerDetailTitle').textContent = customer.name;
  document.getElementById('customerDetailContact').textContent = customer.contact || '-';
  document.getElementById('customerDetailNotes').textContent = customer.notes || '-';
  document.getElementById('customerDetailUpdated').textContent = customer.updated_at;
  document.getElementById('editCustomerName').value = customer.name;
  document.getElementById('editCustomerContact').value = customer.contact || '';
  document.getElementById('editCustomerNotes').value = customer.notes || '';
  renderList('customerOrders', data.orders, {
    render: (order) => renderCustomerOrderRow(order),
    onClick: (order) => {
      switchTab('orders');
      listOrders().then(() => selectOrder(order.id));
    },
  });
}

function startQuoteForSelectedCustomer() {
  const customer = customersCache.find((entry) => entry.id === selectedCustomerId);
  if (!customer) {
    setNotice('Select a customer first.', 'error');
    return;
  }
  selectDesignCustomer(customer.id);
  switchTab('design');
  scheduleDesignHistorySnapshot();
  setNotice(`Started quote for ${customer.name}.`, 'success');
}

async function selectCustomer(customerId) {
  selectedCustomerId = customerId;
  populateCustomerSelect();
  renderList('customerList', customersCache, {
    isSelected: (customer) => selectedCustomerId === customer.id,
    render: (customer) => renderCustomerRow(customer),
    onClick: (row) => selectCustomer(row.id),
  });

  try {
    const data = await fetchJson(`/api/customers/${customerId}`);
    renderCustomerDetail(data);
    document.getElementById('customerName').value = data.customer.name;
    document.getElementById('customerContact').value = data.customer.contact || '';
    scheduleDesignHistorySnapshot();
    show(data);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function saveCustomerEdits() {
  if (!selectedCustomerId) {
    setNotice('Select a customer first.', 'error');
    return;
  }
  try {
    const name = document.getElementById('editCustomerName').value || '';
    const contact = document.getElementById('editCustomerContact').value || '';
    const identityError = validateCustomerIdentity(name, contact);
    if (identityError) {
      setNotice(identityError, 'error');
      return;
    }
    const fd = new FormData();
    fd.append('name', name.trim());
    fd.append('contact', contact.trim());
    fd.append('notes', document.getElementById('editCustomerNotes').value || '');
    const data = await fetchJson(`/api/customers/${selectedCustomerId}`, { method: 'POST', body: fd });
    show(data);
    setNotice('Customer updated.', 'success');
    await Promise.all([listCustomers(), listOrders()]);
    await selectCustomer(selectedCustomerId);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

async function listCustomers() {
  try {
    const q = encodeURIComponent(document.getElementById('customerSearch')?.value || '');
    const data = await fetchJson(`/api/customers?q=${q}`);
    customersCache = data.customers;
    populateCustomerSelect();

    renderList('customerList', data.customers, {
      isSelected: (customer) => selectedCustomerId === customer.id,
      render: (customer) => renderCustomerRow(customer),
      onClick: (customer) => selectCustomer(customer.id),
    });

    if (selectedCustomerId && customersCache.some((customer) => customer.id === selectedCustomerId)) {
      await selectCustomer(selectedCustomerId);
    }

    show(data);
  } catch (error) {
    setNotice(error.message, 'error');
  }
}

function debouncedCustomerSearch() {
  window.clearTimeout(customerSearchTimer);
  customerSearchTimer = window.setTimeout(() => {
    listCustomers();
  }, 180);
}

window.addEventListener('DOMContentLoaded', async () => {
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && document.getElementById('orderInspector')?.classList.contains('open')) {
      closeOrderInspector();
    }
    if (event.key === 'Escape' && document.getElementById('adminCatalogEditorDrawer')?.classList.contains('open')) {
      closeCatalogEditor();
    }
  });
  applyTheme(window.localStorage.getItem('framershaven-theme') || 'classic', false);
  loadLocalPreview();
  bindMockupDesigner();
  bindDesignInputs();
  clearNotice();
  syncMatLayerUI();
  updateMatSlotState();
  syncOpeningPositionInputs();
  setRatio();
  updatePresetUI();
  updateSelectionSummary();
  updateGalleryDetails(null);
  updateQuoteSummary(null);
  renderMockup();
  await Promise.all([listImages(), listOrders(), listCustomers(), searchCatalog(true), loadPricingSettings(), loadServiceOptions(), listBackups()]);
  const lastImport = window.localStorage.getItem('studio-last-import');
  if (lastImport) {
    const stats = document.getElementById('catalogStats');
    if (stats) stats.textContent = lastImport;
  }
  commitDesignHistorySnapshot();
});

// --- Custom Multi-opening Feature ---
let customOpenings = [
  { id: 1, w: 8, h: 10, x: 0, y: 0, artworkUrl: null, artworkImg: null, artworkImageId: null, artworkLabel: null }
];
let selectedOpeningId = 1;
let selectedOpeningIds = new Set();
let activeResizeHandle = null;
const DESIGN_HISTORY_LIMIT = 50;
const DESIGN_HISTORY_FIELD_IDS = [
  'qw',
  'qh',
  'imgW',
  'imgH',
  'matBorder',
  'openingLayout',
  'openingSpacing',
  'openingBalance',
  'openingOffsetX',
  'openingOffsetY',
  'useSecondMat',
  'useThirdMat',
  'secondMatReveal',
  'thirdMatReveal',
  'glazingType',
  'customerSelect',
  'customerName',
  'customerContact',
  'labor',
  'globalDiscount',
  'ratioPreset',
  'ratioW',
  'ratioH',
  'rotateDeg',
  'optionBacking',
  'countBacking',
  'optionMounting',
  'countMounting',
  'optionFrameMounting',
  'countFrameMounting',
  'optionPrinting',
  'countPrinting',
  'optionVarious',
  'countVarious',
  'optionAssembly',
  'countAssembly',
  'optionRoyalties',
  'countRoyalties',
  'optionCustom1',
  'countCustom1',
  'optionCustom2',
  'countCustom2',
  'otherLineLabel',
  'otherLineAmount',
  'otherLineDiscount',
  'otherLine2Label',
  'otherLine2Amount',
  'otherLine2Discount',
];
let designHistory = [];
let designHistoryIndex = -1;
let designHistoryTimer = null;
let designHistorySuspended = false;

function normalizeOpeningSelection() {
  const validIds = new Set(customOpenings.map((opening) => opening.id));
  selectedOpeningIds = new Set([...selectedOpeningIds].filter((id) => validIds.has(id)));
}

function getBatchSelectedOpenings() {
  normalizeOpeningSelection();
  if (selectedOpeningIds.size) {
    return customOpenings.filter((opening) => selectedOpeningIds.has(opening.id));
  }
  return customOpenings.slice();
}

function updateOpeningSelectionSummary() {
  const summary = document.getElementById('openingSelectionSummary');
  if (!summary) return;
  const count = selectedOpeningIds.size;
  if (!count) {
    summary.textContent = `No windows selected. Batch actions apply to all ${customOpenings.length} windows.`;
    return;
  }
  summary.textContent = `${count} window${count === 1 ? '' : 's'} selected for batch actions.`;
}

function getDesignFieldValue(id) {
  const node = document.getElementById(id);
  if (!node) return null;
  if (node.type === 'checkbox') return Boolean(node.checked);
  return node.value;
}

function setDesignFieldValue(id, value) {
  const node = document.getElementById(id);
  if (!node || value === null || value === undefined) return;
  if (node.type === 'checkbox') {
    node.checked = Boolean(value);
  } else {
    node.value = String(value);
  }
}

function captureDesignSnapshot() {
  const fields = {};
  DESIGN_HISTORY_FIELD_IDS.forEach((id) => {
    fields[id] = getDesignFieldValue(id);
  });
  return {
    fields,
    selectedMaterials: { ...selectedMaterials },
    activeDesignPreset,
    designLauncherExpanded,
    selectedCustomerId,
    selectedImageId,
    selectedOpeningId,
    selectedOpeningIds: [...selectedOpeningIds],
    customOpenings: customOpenings.map((opening) => ({ ...opening })),
  };
}

function designSnapshotKey(snapshot) {
  return JSON.stringify(snapshot);
}

function syncDesignHistoryButtons() {
  const undo = document.getElementById('designUndoButton');
  const redo = document.getElementById('designRedoButton');
  if (undo) undo.disabled = designHistoryIndex <= 0;
  if (redo) redo.disabled = designHistoryIndex < 0 || designHistoryIndex >= designHistory.length - 1;
}

function commitDesignHistorySnapshot() {
  if (designHistorySuspended) return;
  const snapshot = captureDesignSnapshot();
  const key = designSnapshotKey(snapshot);
  const current = designHistory[designHistoryIndex];
  if (current && current.key === key) {
    syncDesignHistoryButtons();
    return;
  }
  if (designHistoryIndex < designHistory.length - 1) {
    designHistory = designHistory.slice(0, designHistoryIndex + 1);
  }
  designHistory.push({ key, snapshot });
  if (designHistory.length > DESIGN_HISTORY_LIMIT) {
    designHistory.shift();
  } else {
    designHistoryIndex += 1;
  }
  designHistoryIndex = designHistory.length - 1;
  syncDesignHistoryButtons();
}

function scheduleDesignHistorySnapshot() {
  if (designHistorySuspended) return;
  if (designHistoryTimer) window.clearTimeout(designHistoryTimer);
  designHistoryTimer = window.setTimeout(() => {
    designHistoryTimer = null;
    commitDesignHistorySnapshot();
  }, 120);
}

async function restoreDesignSnapshot(snapshot) {
  if (!snapshot) return;
  designHistorySuspended = true;
  try {
    activeDesignPreset = snapshot.activeDesignPreset || activeDesignPreset;
    designLauncherExpanded = Boolean(snapshot.designLauncherExpanded);
    selectedCustomerId = snapshot.selectedCustomerId || null;
    selectedImageId = snapshot.selectedImageId || null;
    selectedMaterials = { ...selectedMaterials, ...(snapshot.selectedMaterials || {}) };
    selectedOpeningId = snapshot.selectedOpeningId || selectedOpeningId;
    selectedOpeningIds = new Set(snapshot.selectedOpeningIds || []);
    customOpenings = (snapshot.customOpenings || customOpenings).map((opening) => ({ ...opening }));
    if (!selectedOpeningIds.size) {
      selectedOpeningIds = new Set();
    }
    Object.entries(snapshot.fields || {}).forEach(([id, value]) => {
      setDesignFieldValue(id, value);
    });
    populateCustomerSelect();
    syncMatLayerUI();
    syncOpeningPositionInputs();
    syncOpeningSelectionGrid();
    updatePresetUI();
    updateSelectionSummary();
    updateQuoteSummary(null);
    if (selectedImageId) {
      const image = imagesCache.find((entry) => entry.id === selectedImageId);
      if (image) {
        selectedImageId = image.id;
        updateGalleryDetails(image);
        loadImageFromUrl(image.url, false);
      } else {
        newGalleryArtworkMode();
      }
    } else {
      newGalleryArtworkMode();
    }
    selectedOpeningId = customOpenings.some((opening) => opening.id === selectedOpeningId)
      ? selectedOpeningId
      : (customOpenings[0]?.id || 1);
    renderMockup();
  } finally {
    designHistorySuspended = false;
    syncDesignHistoryButtons();
  }
}

async function undoDesignChange() {
  if (designHistoryIndex <= 0) {
    setNotice('Nothing left to undo.', 'warning');
    return;
  }
  designHistoryIndex -= 1;
  const entry = designHistory[designHistoryIndex];
  await restoreDesignSnapshot(entry?.snapshot);
}

async function redoDesignChange() {
  if (designHistoryIndex < 0 || designHistoryIndex >= designHistory.length - 1) {
    setNotice('Nothing left to redo.', 'warning');
    return;
  }
  designHistoryIndex += 1;
  const entry = designHistory[designHistoryIndex];
  await restoreDesignSnapshot(entry?.snapshot);
}

function syncOpeningSelectionGrid() {
  const grid = document.getElementById('openingSelectionGrid');
  if (!grid) return;
  normalizeOpeningSelection();
  grid.innerHTML = '';
  customOpenings.forEach((opening, index) => {
    const button = document.createElement('button');
    const active = selectedOpeningIds.has(opening.id);
    button.type = 'button';
    button.className = `ghost mini-button${active ? ' active' : ''}`;
    button.innerHTML = `<span class="tile-label">${index + 1}</span>`;
    button.title = `${active ? 'Remove' : 'Add'} window #${index + 1} from batch actions.`;
    button.onclick = () => {
      setOpeningSelection(opening.id, !selectedOpeningIds.has(opening.id));
    };
    grid.appendChild(button);
  });
  updateOpeningSelectionSummary();
}

function clearOpeningSelection() {
  selectedOpeningIds = new Set();
  syncOpeningSelectionGrid();
  renderMockup();
}

function selectAllOpenings() {
  selectedOpeningIds = new Set(customOpenings.map((opening) => opening.id));
  syncOpeningSelectionGrid();
  renderMockup();
}

function setOpeningSelection(openingId, checked) {
  if (checked) {
    selectedOpeningIds.add(openingId);
  } else {
    selectedOpeningIds.delete(openingId);
  }
  syncOpeningSelectionGrid();
  renderMockup();
}

function clampOpeningToBounds(op, matWIn, matHIn, minMatBorder = 1.0) {
  const limitX = Math.max(0.5, (matWIn / 2) - minMatBorder);
  const limitY = Math.max(0.5, (matHIn / 2) - minMatBorder);
  
  // Clamp width and height to be at least 1.0 inch, and at most the safe size
  op.w = Math.max(1.0, Math.min(limitX * 2, op.w));
  op.h = Math.max(1.0, Math.min(limitY * 2, op.h));
  
  // Clamp position so the edges stay inside
  const halfW = op.w / 2;
  const halfH = op.h / 2;
  
  op.x = Math.max(-limitX + halfW, Math.min(limitX - halfW, op.x));
  op.y = Math.max(-limitY + halfH, Math.min(limitY - halfH, op.y));
}

function onOpeningLayoutChange(value) {
  const standardCtrls = document.getElementById('standardOpeningControls');
  const multiCtrls = document.getElementById('multiOpeningControls');
  if (value === 'multi') {
    if (standardCtrls) standardCtrls.style.display = 'none';
    if (multiCtrls) multiCtrls.style.display = 'block';
    
    if (!customOpenings || customOpenings.length === 0) {
      const initW = Number(document.getElementById('qw')?.value || document.getElementById('imgW')?.value || 8);
      const initH = Number(document.getElementById('qh')?.value || document.getElementById('imgH')?.value || 10);
      customOpenings = [
        { id: 1, w: initW, h: initH, x: 0, y: 0, artworkUrl: null, artworkImg: null, artworkImageId: null, artworkLabel: null }
      ];
      selectedOpeningId = 1;
    }
    syncMultiOpeningsList();
    updateMultiOpeningBoundingBox();
  } else {
    if (standardCtrls) standardCtrls.style.display = 'block';
    if (multiCtrls) multiCtrls.style.display = 'none';
  }
  
  calcQuote();
  renderMockup();
  scheduleDesignHistorySnapshot();
}

function updateMultiOpeningBoundingBox() {
  if (document.getElementById('openingLayout')?.value !== 'multi') return;
  if (!customOpenings || !customOpenings.length) return;
  
  // Read the user-defined mat area — do NOT overwrite qw/qh
  const artW = Number(document.getElementById('qw')?.value || document.getElementById('imgW')?.value || 8);
  const artH = Number(document.getElementById('qh')?.value || document.getElementById('imgH')?.value || 10);
  const { matBorder } = getEffectiveOpeningOffsets();
  const matWIn = artW + (matBorder * 2);
  const matHIn = artH + (matBorder * 2);
  
  // Clamp every opening to stay inside the fixed mat area
  customOpenings.forEach(op => {
    clampOpeningToBounds(op, matWIn, matHIn, 0.5);
  });
}

function syncMultiOpeningsList() {
  const listContainer = document.getElementById('multiOpeningsList');
  if (!listContainer) return;
  
  listContainer.innerHTML = '';
  customOpenings.forEach((op, index) => {
    const row = document.createElement('div');
    row.className = `opening-row${op.id === selectedOpeningId ? ' selected' : ''}`;
    row.onclick = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
      selectedOpeningId = op.id;
      syncMultiOpeningsList();
      renderMockup();
    };
    
    const hasImg = !!op.artworkUrl;
    row.innerHTML = `
      <div class="opening-row-num">#${index + 1}</div>
      <div class="opening-row-size">
        <input type="number" step="0.25" value="${op.w}" onchange="updateCustomOpeningField(${op.id}, 'w', this.value)" title="Width (inches)" />
        <span class="size-sep">×</span>
        <input type="number" step="0.25" value="${op.h}" onchange="updateCustomOpeningField(${op.id}, 'h', this.value)" title="Height (inches)" />
        <span style="font-size:9px;color:var(--muted);margin-left:2px;">in</span>
      </div>
      <button type="button" class="ghost mini-button" onclick="openOpeningArtworkPicker(${op.id})" style="padding: 2px 5px; font-size: 10px;" title="${hasImg ? 'Replace image from the app gallery' : 'Choose an image from the app gallery'}">${hasImg ? 'Gallery' : 'Gallery'}</button>
      ${hasImg ? `<button type="button" class="ghost mini-button" onclick="clearArtworkFromOpening(${op.id})" style="padding: 2px 4px; font-size: 9px; color: var(--muted);" title="Clear image">✕</button>` : ''}
      <button type="button" class="ghost mini-button" onclick="deleteCustomOpening(${op.id})" style="padding: 2px 4px; color: var(--danger, #ff4d4f); font-size: 10px; margin-left: 2px;" title="Delete opening">🗑</button>
    `;
    listContainer.appendChild(row);
  });
  syncOpeningSelectionGrid();
}

function addCustomOpening() {
  if (customOpenings.length >= 10) {
    setNotice('Maximum of 10 openings reached.', 'warning');
    return;
  }
  
  const nextId = customOpenings.length > 0 ? Math.max(...customOpenings.map(o => o.id)) + 1 : 1;
  
  customOpenings.push({
    id: nextId,
    w: 5,
    h: 7,
    x: 0,
    y: 0,
    artworkUrl: null,
    artworkImg: null,
    artworkImageId: null,
    artworkLabel: null
  });
  
  selectedOpeningId = nextId;
  syncMultiOpeningsList();
  updateMultiOpeningBoundingBox();
  calcQuote();
  renderMockup();
  scheduleDesignHistorySnapshot();
  setNotice('Custom opening added.', 'success');
}

function deleteCustomOpening(id) {
  if (customOpenings.length <= 1) {
    setNotice('You must keep at least one opening.', 'warning');
    return;
  }
  
  customOpenings = customOpenings.filter(o => o.id !== id);
  if (pendingOpeningArtworkId === id) {
    pendingOpeningArtworkId = null;
  }
  if (selectedOpeningId === id) {
    selectedOpeningId = customOpenings[0].id;
  }
  
  syncMultiOpeningsList();
  updateMultiOpeningBoundingBox();
  calcQuote();
  renderMockup();
  scheduleDesignHistorySnapshot();
  setNotice('Opening deleted.', 'success');
}

function updateCustomOpeningField(id, field, value) {
  const matchingOp = customOpenings.find(o => o.id === id);
  if (!matchingOp) return;
  
  const numVal = Number(value || '0');
  if (field === 'w' || field === 'h') {
    matchingOp[field] = Math.max(0.5, numVal);
  } else {
    matchingOp[field] = numVal;
  }
  
  // Apply clamping boundaries when fields are typed!
  const artW = Number(document.getElementById('qw')?.value || document.getElementById('imgW')?.value || 8);
  const artH = Number(document.getElementById('qh')?.value || document.getElementById('imgH')?.value || 10);
  const { matBorder } = getEffectiveOpeningOffsets();
  const matWIn = artW + (matBorder * 2);
  const matHIn = artH + (matBorder * 2);
  clampOpeningToBounds(matchingOp, matWIn, matHIn, 1.0);
  
  updateMultiOpeningBoundingBox();
  calcQuote();
  renderMockup();
  scheduleDesignHistorySnapshot();
}

// Helper: get the usable opening area (qw × qh) in inches
function getOpeningAreaInches() {
  const artW = Number(document.getElementById('qw')?.value || document.getElementById('imgW')?.value || 8);
  const artH = Number(document.getElementById('qh')?.value || document.getElementById('imgH')?.value || 10);
  return { areaW: artW, areaH: artH };
}

function alignCustomOpenings(alignType) {
  const targets = getBatchSelectedOpenings();
  if (targets.length < 2) {
    setNotice('Select at least two windows to align, or clear the selector to use all windows.', 'warning');
    return;
  }
  
  const { areaW, areaH } = getOpeningAreaInches();
  const halfW = areaW / 2;
  const halfH = areaH / 2;
  
  if (alignType === 'left') {
    targets.forEach(op => {
      op.x = Number((-halfW + op.w / 2).toFixed(2));
    });
  } 
  else if (alignType === 'right') {
    targets.forEach(op => {
      op.x = Number((halfW - op.w / 2).toFixed(2));
    });
  } 
  else if (alignType === 'center-h') {
    targets.forEach(op => {
      op.x = 0;
    });
  } 
  else if (alignType === 'top') {
    targets.forEach(op => {
      op.y = Number((halfH - op.h / 2).toFixed(2));
    });
  } 
  else if (alignType === 'bottom') {
    targets.forEach(op => {
      op.y = Number((-halfH + op.h / 2).toFixed(2));
    });
  } 
  else if (alignType === 'center-v') {
    targets.forEach(op => {
      op.y = 0;
    });
  }
  
  // Clamp aligned openings safely
  const { matBorder } = getEffectiveOpeningOffsets();
  const matWIn = areaW + (matBorder * 2);
  const matHIn = areaH + (matBorder * 2);
  targets.forEach(op => clampOpeningToBounds(op, matWIn, matHIn, 0.5));
  
  syncMultiOpeningsList();
  updateMultiOpeningBoundingBox();
  calcQuote();
  renderMockup();
  scheduleDesignHistorySnapshot();
  setNotice('Aligned openings.', 'success');
}

function distributeCustomOpenings(distType) {
  const targets = getBatchSelectedOpenings();
  if (targets.length < 2) {
    setNotice('Select at least two windows to distribute, or clear the selector to use all windows.', 'warning');
    return;
  }
  
  const { areaW, areaH } = getOpeningAreaInches();
  const halfW = areaW / 2;
  const halfH = areaH / 2;
  
  if (distType === 'h') {
    const sorted = [...targets].sort((a, b) => a.x - b.x);
    const totalObjW = sorted.reduce((s, o) => s + o.w, 0);
    const gap = Math.max(0.25, (areaW - totalObjW) / (sorted.length + 1));
    let cursor = -halfW + gap;
    sorted.forEach(op => {
      op.x = Number((cursor + op.w / 2).toFixed(2));
      cursor += op.w + gap;
    });
  } 
  else if (distType === 'v') {
    const sorted = [...targets].sort((a, b) => b.y - a.y);
    const totalObjH = sorted.reduce((s, o) => s + o.h, 0);
    const gap = Math.max(0.25, (areaH - totalObjH) / (sorted.length + 1));
    let cursor = halfH - gap;
    sorted.forEach(op => {
      op.y = Number((cursor - op.h / 2).toFixed(2));
      cursor -= op.h + gap;
    });
  }
  
  // Clamp distributed openings safely
  const { matBorder } = getEffectiveOpeningOffsets();
  const matWIn = areaW + (matBorder * 2);
  const matHIn = areaH + (matBorder * 2);
  targets.forEach(op => clampOpeningToBounds(op, matWIn, matHIn, 0.5));
  
  syncMultiOpeningsList();
  updateMultiOpeningBoundingBox();
  calcQuote();
  renderMockup();
  scheduleDesignHistorySnapshot();
  setNotice('Distributed openings.', 'success');
}

// --- Multi-Window Template Presets ---

function applyMultiTemplate(templateName) {
  const { areaW, areaH } = getOpeningAreaInches();
  const gap = 0.5; // spacing between windows
  
  let newOpenings = [];
  
  if (templateName === '2-side') {
    // 2 side-by-side
    const winW = (areaW - gap) / 2;
    const winH = areaH;
    newOpenings = [
      { id: 1, w: r(winW), h: r(winH), x: r(-(winW + gap) / 2), y: 0 },
      { id: 2, w: r(winW), h: r(winH), x: r((winW + gap) / 2), y: 0 },
    ];
  }
  else if (templateName === '2-stack') {
    // 2 stacked vertically
    const winW = areaW;
    const winH = (areaH - gap) / 2;
    newOpenings = [
      { id: 1, w: r(winW), h: r(winH), x: 0, y: r((winH + gap) / 2) },
      { id: 2, w: r(winW), h: r(winH), x: 0, y: r(-(winH + gap) / 2) },
    ];
  }
  else if (templateName === '1-over-2') {
    // 1 panorama on top, 2 equal below (pyramid)
    const topH = areaH * 0.45;
    const botH = areaH - topH - gap;
    const botW = (areaW - gap) / 2;
    newOpenings = [
      { id: 1, w: r(areaW), h: r(topH), x: 0, y: r((areaH / 2) - topH / 2) },
      { id: 2, w: r(botW), h: r(botH), x: r(-(botW + gap) / 2), y: r(-(areaH / 2) + botH / 2) },
      { id: 3, w: r(botW), h: r(botH), x: r((botW + gap) / 2), y: r(-(areaH / 2) + botH / 2) },
    ];
  }
  else if (templateName === '1-over-3') {
    // 1 panorama on top, 3 equal below
    const topH = areaH * 0.4;
    const botH = areaH - topH - gap;
    const botW = (areaW - gap * 2) / 3;
    newOpenings = [
      { id: 1, w: r(areaW), h: r(topH), x: 0, y: r((areaH / 2) - topH / 2) },
      { id: 2, w: r(botW), h: r(botH), x: r(-(botW + gap)), y: r(-(areaH / 2) + botH / 2) },
      { id: 3, w: r(botW), h: r(botH), x: 0, y: r(-(areaH / 2) + botH / 2) },
      { id: 4, w: r(botW), h: r(botH), x: r(botW + gap), y: r(-(areaH / 2) + botH / 2) },
    ];
  }
  else if (templateName === '2x2-grid') {
    // 2×2 grid
    const winW = (areaW - gap) / 2;
    const winH = (areaH - gap) / 2;
    newOpenings = [
      { id: 1, w: r(winW), h: r(winH), x: r(-(winW + gap) / 2), y: r((winH + gap) / 2) },
      { id: 2, w: r(winW), h: r(winH), x: r((winW + gap) / 2), y: r((winH + gap) / 2) },
      { id: 3, w: r(winW), h: r(winH), x: r(-(winW + gap) / 2), y: r(-(winH + gap) / 2) },
      { id: 4, w: r(winW), h: r(winH), x: r((winW + gap) / 2), y: r(-(winH + gap) / 2) },
    ];
  }
  else if (templateName === 'pano-over-4') {
    // 1 panorama on top, 4 equal squares below
    const topH = Math.min(areaH * 0.35, 4);
    const botH = areaH - topH - gap;
    const botW = (areaW - gap * 3) / 4;
    newOpenings = [
      { id: 1, w: r(areaW), h: r(topH), x: 0, y: r((areaH / 2) - topH / 2) },
      { id: 2, w: r(botW), h: r(botH), x: r(-1.5 * (botW + gap)), y: r(-(areaH / 2) + botH / 2) },
      { id: 3, w: r(botW), h: r(botH), x: r(-0.5 * (botW + gap)), y: r(-(areaH / 2) + botH / 2) },
      { id: 4, w: r(botW), h: r(botH), x: r(0.5 * (botW + gap)), y: r(-(areaH / 2) + botH / 2) },
      { id: 5, w: r(botW), h: r(botH), x: r(1.5 * (botW + gap)), y: r(-(areaH / 2) + botH / 2) },
    ];
  }
  else if (templateName === '3-row') {
    // 3 in a row
    const winW = (areaW - gap * 2) / 3;
    const winH = areaH;
    newOpenings = [
      { id: 1, w: r(winW), h: r(winH), x: r(-(winW + gap)), y: 0 },
      { id: 2, w: r(winW), h: r(winH), x: 0, y: 0 },
      { id: 3, w: r(winW), h: r(winH), x: r(winW + gap), y: 0 },
    ];
  }
  
  // Add gallery artwork fields
  newOpenings.forEach((op) => {
    op.artworkUrl = null;
    op.artworkImg = null;
    op.artworkImageId = null;
    op.artworkLabel = null;
  });
  
  // Set layout to multi if not already
  const layoutSelect = document.getElementById('openingLayout');
  if (layoutSelect && layoutSelect.value !== 'multi') {
    layoutSelect.value = 'multi';
    onOpeningLayoutChange('multi');
  }
  
  customOpenings = newOpenings;
  selectedOpeningId = 1;
  
  // Clamp to safe bounds
  const { matBorder } = getEffectiveOpeningOffsets();
  const matWIn = areaW + (matBorder * 2);
  const matHIn = areaH + (matBorder * 2);
  customOpenings.forEach(op => clampOpeningToBounds(op, matWIn, matHIn, 0.25));
  
  syncMultiOpeningsList();
  calcQuote();
  renderMockup();
  scheduleDesignHistorySnapshot();
  setNotice(`Applied ${templateName} template (${newOpenings.length} windows).`, 'success');
}

function r(n) { return Number(n.toFixed(2)); }

function clearArtworkFromOpening(openingId) {
  const op = customOpenings.find(o => o.id === openingId);
  if (op) {
    op.artworkUrl = null;
    op.artworkImg = null;
    op.artworkImageId = null;
    op.artworkLabel = null;
    syncMultiOpeningsList();
    renderMockup();
    scheduleDesignHistorySnapshot();
    setNotice('Image cleared.', 'success');
  }
}
