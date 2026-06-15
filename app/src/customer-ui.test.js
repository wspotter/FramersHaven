import test from 'node:test';
import assert from 'node:assert/strict';

import { filterCustomerMatches } from '../static/customer-ui.js';

const customers = [
  { id: 1, name: 'Alice Morgan', contact: '555-014-2026', customer_email: 'alice@example.test' },
  { id: 2, name: 'John Frame', contact: '555-010-0199', customer_email: 'john@example.com' },
  { id: 3, name: 'Potter Gallery', contact: '502-555-0100', customer_email: 'gallery@example.com' },
  { id: 4, name: 'Browser Smoke Test', contact: '555-010-0198', customer_email: '' },
];

test('finds customers by name, phone, or email and ranks prefix matches first', () => {
  assert.deepEqual(filterCustomerMatches(customers, 'gallery').map((row) => row.id), [3]);
  assert.deepEqual(filterCustomerMatches(customers, '5550142026').map((row) => row.id), [1]);
  assert.deepEqual(filterCustomerMatches(customers, 'john@example').map((row) => row.id), [2]);
  assert.deepEqual(filterCustomerMatches(customers, 'Browser Smoke').map((row) => row.id), [4]);
});

test('returns no suggestions for an empty query and respects the result limit', () => {
  assert.deepEqual(filterCustomerMatches(customers, ''), []);
  assert.deepEqual(filterCustomerMatches(customers, 'o', 2).map((row) => row.id), [2, 3]);
});
