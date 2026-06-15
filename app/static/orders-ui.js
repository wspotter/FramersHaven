const SORT_KEYS = new Set([
  'quote_number',
  'customer_name',
  'customer_contact',
  'total',
  'balance',
  'created_at',
  'status',
  'next_action',
]);

function normalize(value) {
  return String(value ?? '').trim().toLowerCase();
}

export function filterOrders(orders, { stage = '', query = '' } = {}) {
  const needle = normalize(query);
  return orders.filter((order) => {
    if (stage && order.status !== stage) return false;
    if (!needle) return true;
    return [order.quote_number, order.customer_name, order.customer_contact]
      .some((value) => normalize(value).includes(needle));
  });
}

export function sortOrders(orders, key = 'created_at', direction = 'desc') {
  if (!SORT_KEYS.has(key)) throw new Error(`Unsupported order sort key: ${key}`);
  if (!['asc', 'desc'].includes(direction)) throw new Error(`Unsupported order sort direction: ${direction}`);
  const multiplier = direction === 'asc' ? 1 : -1;
  return [...orders].sort((left, right) => {
    const leftValue = ['total', 'balance'].includes(key) ? Number(left[key] || 0) : normalize(left[key]);
    const rightValue = ['total', 'balance'].includes(key) ? Number(right[key] || 0) : normalize(right[key]);
    if (leftValue < rightValue) return -1 * multiplier;
    if (leftValue > rightValue) return 1 * multiplier;
    return Number(right.id || 0) - Number(left.id || 0);
  });
}

if (typeof window !== 'undefined') {
  window.OrderTable = { filterOrders, sortOrders };
}
