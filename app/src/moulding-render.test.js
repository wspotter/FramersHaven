import test from 'node:test';
import assert from 'node:assert/strict';

import '../static/moulding-render.js';

const { getStripCropRect, getTileOverlap } = globalThis.MouldingRender;

test('crops the raw cut end from long moulding reference photos', () => {
  const crop = getStripCropRect(1229, 220, { prepared: false });

  assert.ok(crop.x > 0);
  assert.ok(crop.x + crop.width <= Math.round(1229 * 0.8));
  assert.ok(crop.width >= Math.round(1229 * 0.65));
  assert.equal(crop.height, 220);
});

test('preserves operator-prepared strips and moderate reference photos', () => {
  assert.deepEqual(
    getStripCropRect(1229, 220, { prepared: true }),
    { x: 0, y: 0, width: 1229, height: 220 },
  );
  assert.deepEqual(
    getStripCropRect(584, 220, { prepared: false }),
    { x: 0, y: 0, width: 584, height: 220 },
  );
});

test('uses a small bounded overlap to feather repeated strip tiles', () => {
  assert.equal(getTileOverlap(80, 340), 6);
  assert.equal(getTileOverlap(20, 30), 2);
  assert.equal(getTileOverlap(240, 1000), 10);
});
