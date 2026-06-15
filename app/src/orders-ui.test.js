import test from 'node:test';
import assert from 'node:assert/strict';

import { filterOrders, sortOrders } from '../static/orders-ui.js';

const orders = [
  { id: 2, quote_number: 'Q00002', customer_name: 'Beta', customer_contact: '606-222-0000', status: 'work_order', total: 40, balance: 40, created_at: '2026-06-02 10:00:00' },
  { id: 3, quote_number: 'Q00003', customer_name: 'Alpha', customer_contact: '606-333-0000', status: 'invoice', total: 20, balance: 0, created_at: '2026-06-03 10:00:00' },
  { id: 1, quote_number: 'Q00001', customer_name: 'Alpha', customer_contact: '606-111-0000', status: 'quote', total: 20, balance: 20, created_at: '2026-06-01 10:00:00' },
];

test('filters orders by stage and search text', () => {
  assert.deepEqual(filterOrders(orders, { stage: 'work_order', query: '' }).map((row) => row.id), [2]);
  assert.deepEqual(filterOrders(orders, { stage: '', query: 'Q00003' }).map((row) => row.id), [3]);
  assert.deepEqual(filterOrders(orders, { stage: '', query: '606-111' }).map((row) => row.id), [1]);
});

test('sorts orders in both directions with a stable id tie breaker', () => {
  assert.deepEqual(sortOrders(orders, 'customer_name', 'asc').map((row) => row.id), [3, 1, 2]);
  assert.deepEqual(sortOrders(orders, 'customer_name', 'desc').map((row) => row.id), [2, 3, 1]);
  assert.deepEqual(sortOrders(orders, 'total', 'asc').map((row) => row.id), [3, 1, 2]);
  assert.deepEqual(sortOrders(orders, 'created_at', 'desc').map((row) => row.id), [3, 2, 1]);
});

test('rejects unsupported sort keys and directions', () => {
  assert.throws(() => sortOrders(orders, 'payload_json', 'asc'), /Unsupported order sort key/);
  assert.throws(() => sortOrders(orders, 'total', 'sideways'), /Unsupported order sort direction/);
});
