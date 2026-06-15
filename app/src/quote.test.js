import test from 'node:test';
import assert from 'node:assert/strict';
import { calculateQuote } from './quote.js';

test('calculates totals with fixed 6% tax', () => {
  const result = calculateQuote({
    widthIn: 8,
    heightIn: 10,
    mouldingCostPerFt: 6,
    matCostPerSqFt: 4,
    matBorderIn: 2,
    labor: 15
  });

  assert.equal(result.taxRate, 0.06);
  assert.equal(result.subtotal > 0, true);
  assert.equal(result.total, Math.round((result.subtotal + result.tax) * 100) / 100);
});
