import test from 'node:test';
import assert from 'node:assert/strict';

import { filterCatalogItems, sortCatalogItems } from '../static/admin-ui.js';

const items = [
  { id: 1, sku: 'DEMO-FR-3029', name: 'Mahogany Flat Profile', category: 'moulding', vendor: 'Sample Catalog', cost: 2.54, active: 1 },
  { id: 2, sku: 'DEMO-MAT-793', name: 'Light Silver White Core', category: 'mat', vendor: 'Sample Catalog', cost: 8.63, active: 1 },
  { id: 3, sku: 'DEMO-GLZ-4060', name: '40x60', category: 'glazing', vendor: 'Sample Catalog', cost: 2, active: 0 },
];

test('filters catalog items by category and operator search text', () => {
  assert.deepEqual(filterCatalogItems(items, { category: 'mat' }).map((row) => row.id), [2]);
  assert.deepEqual(filterCatalogItems(items, { query: 'mahogany' }).map((row) => row.id), [1]);
  assert.deepEqual(filterCatalogItems(items, { query: 'sample' }).map((row) => row.id), [1, 2, 3]);
  assert.deepEqual(filterCatalogItems(items, { query: 'glazing' }).map((row) => row.id), [3]);
});

test('sorts catalog columns in both directions with an id tie breaker', () => {
  assert.deepEqual(sortCatalogItems(items, 'sku', 'asc').map((row) => row.id), [1, 3, 2]);
  assert.deepEqual(sortCatalogItems(items, 'cost', 'desc').map((row) => row.id), [2, 1, 3]);
  assert.deepEqual(sortCatalogItems(items, 'active', 'asc').map((row) => row.id), [3, 1, 2]);
});

test('rejects unsupported catalog sort keys and directions', () => {
  assert.throws(() => sortCatalogItems(items, 'metadata_json', 'asc'), /Unsupported catalog sort key/);
  assert.throws(() => sortCatalogItems(items, 'sku', 'sideways'), /Unsupported catalog sort direction/);
});
