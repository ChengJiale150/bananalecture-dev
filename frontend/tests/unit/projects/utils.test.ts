import test from 'node:test';
import assert from 'node:assert/strict';
import {
  clampPage,
  getPageParamFromSlideIndex,
  getSlideIndexFromPageParam,
  getVisiblePaginationPages,
  normalizePageValue,
  safeParseProjectMessages,
  stringifyProjectMessages,
} from '@/features/projects/utils';

test('safeParseProjectMessages returns an array for valid JSON arrays', () => {
  assert.deepEqual(safeParseProjectMessages('[{"role":"user"}]'), [{ role: 'user' }]);
});

test('safeParseProjectMessages falls back to an empty array for invalid payloads', () => {
  assert.deepEqual(safeParseProjectMessages('{"role":"user"}'), []);
  assert.deepEqual(safeParseProjectMessages('not-json'), []);
  assert.deepEqual(safeParseProjectMessages(null), []);
});

test('stringifyProjectMessages serializes message arrays', () => {
  assert.equal(
    stringifyProjectMessages([{ role: 'assistant', content: 'hello' }]),
    '[{"role":"assistant","content":"hello"}]'
  );
});

test('pagination helpers normalize and clamp values', () => {
  assert.equal(normalizePageValue('3'), 3);
  assert.equal(normalizePageValue('0', 2), 2);
  assert.equal(clampPage(7, 5), 5);
  assert.equal(clampPage(0, 5), 1);
});

test('preview page helpers convert between URL page and slide index', () => {
  assert.equal(getSlideIndexFromPageParam('3', 5), 2);
  assert.equal(getSlideIndexFromPageParam('99', 5), 4);
  assert.equal(getSlideIndexFromPageParam(null, 0), 0);
  assert.equal(getPageParamFromSlideIndex(0), 1);
  assert.equal(getPageParamFromSlideIndex(4), 5);
});

test('getVisiblePaginationPages keeps the current page and boundaries visible', () => {
  assert.deepEqual(getVisiblePaginationPages(5, 10, 1), [1, 4, 5, 6, 10]);
});
