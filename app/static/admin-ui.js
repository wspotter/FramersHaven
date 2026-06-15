const SORT_KEYS = new Set(['sku', 'name', 'category', 'vendor', 'cost', 'width_in', 'active']);

function normalize(value) {
  return String(value ?? '').trim().toLowerCase();
}

export function filterCatalogItems(items, { category = '', query = '' } = {}) {
  const needle = normalize(query);
  return items.filter((item) => {
    if (category && normalize(item.category) !== normalize(category)) return false;
    if (!needle) return true;
    return [item.sku, item.name, item.vendor, item.category]
      .some((value) => normalize(value).includes(needle));
  });
}

export function sortCatalogItems(items, key = 'sku', direction = 'asc') {
  if (!SORT_KEYS.has(key)) throw new Error(`Unsupported catalog sort key: ${key}`);
  if (!['asc', 'desc'].includes(direction)) throw new Error(`Unsupported catalog sort direction: ${direction}`);
  const multiplier = direction === 'asc' ? 1 : -1;
  return [...items].sort((left, right) => {
    const numeric = ['cost', 'width_in', 'active'].includes(key);
    const leftValue = numeric ? Number(left[key] || 0) : normalize(left[key]);
    const rightValue = numeric ? Number(right[key] || 0) : normalize(right[key]);
    if (leftValue < rightValue) return -1 * multiplier;
    if (leftValue > rightValue) return 1 * multiplier;
    return Number(left.id || 0) - Number(right.id || 0);
  });
}

if (typeof window !== 'undefined') {
  window.AdminCatalogTable = { filterCatalogItems, sortCatalogItems };
}
