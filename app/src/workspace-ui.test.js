import test from 'node:test';
import assert from 'node:assert/strict';

import { shouldShowDesignSidebar, shouldShowMockupGuides } from '../static/workspace-ui.js';

test('shows the material sidebar only in the Design workspace', () => {
  assert.equal(shouldShowDesignSidebar('design'), true);
  assert.equal(shouldShowDesignSidebar('gallery'), false);
  assert.equal(shouldShowDesignSidebar('orders'), false);
  assert.equal(shouldShowDesignSidebar('customers'), false);
  assert.equal(shouldShowDesignSidebar('admin'), false);
});

test('shows opening guides only when the mockup has no rendered artwork', () => {
  assert.equal(shouldShowMockupGuides(false), true);
  assert.equal(shouldShowMockupGuides(true), false);
});
