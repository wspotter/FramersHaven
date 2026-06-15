function normalizeCustomerText(value) {
  return String(value || '').trim().toLowerCase();
}

function compactCustomerText(value) {
  return normalizeCustomerText(value).replace(/[()\s-]/g, '');
}

function customerMatchScore(customer, query) {
  const compactQuery = compactCustomerText(query);
  const fields = [customer.name, customer.contact, customer.customer_email]
    .map(normalizeCustomerText);
  const positions = fields.flatMap((field) => [
    field.indexOf(query),
    compactCustomerText(field).indexOf(compactQuery),
  ])
    .filter((position) => position >= 0);
  return positions.length ? Math.min(...positions) : Number.POSITIVE_INFINITY;
}

export function filterCustomerMatches(customers, query, limit = 6) {
  const cleanQuery = normalizeCustomerText(query);
  if (!cleanQuery) return [];
  return [...(customers || [])]
    .map((customer) => ({
      customer,
      score: customerMatchScore(customer, cleanQuery),
    }))
    .filter(({ score }) => Number.isFinite(score))
    .sort((left, right) => left.score - right.score
      || normalizeCustomerText(left.customer.name).localeCompare(normalizeCustomerText(right.customer.name))
      || Number(left.customer.id || 0) - Number(right.customer.id || 0))
    .slice(0, Math.max(0, Number(limit) || 0))
    .map(({ customer }) => customer);
}

if (typeof window !== 'undefined') {
  window.CustomerUI = { filterCustomerMatches };
}
