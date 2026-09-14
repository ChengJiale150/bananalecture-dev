import test from 'node:test';
import assert from 'node:assert/strict';
import { getChatErrorText, getComposerState } from '@/features/chat/chat-status';

test('getComposerState keeps the composer usable after a failed request', () => {
  const failed = getComposerState('error', true);

  assert.equal(failed.isFailed, true);
  assert.equal(failed.canType, true);
  assert.equal(failed.canSend, true);
  assert.equal(failed.showStop, false);
});

test('getComposerState requires text to send and offers stop while a request is active', () => {
  assert.deepEqual(getComposerState('ready', false), {
    canType: true,
    canSend: false,
    showStop: false,
    isFailed: false,
  });
  assert.deepEqual(getComposerState('ready', true), {
    canType: true,
    canSend: true,
    showStop: false,
    isFailed: false,
  });
  assert.deepEqual(getComposerState('submitted', true), {
    canType: true,
    canSend: false,
    showStop: true,
    isFailed: false,
  });
  assert.deepEqual(getComposerState('streaming', true), {
    canType: false,
    canSend: false,
    showStop: true,
    isFailed: false,
  });
});

test('getChatErrorText extracts the message from a JSON error body', () => {
  const error = new Error('{"error":"upstream failed"}');

  assert.equal(getChatErrorText(error), 'upstream failed');
  assert.equal(getChatErrorText(new Error('{"message":"model timeout"}')), 'model timeout');
  assert.equal(getChatErrorText(new Error('{"detail":"bad request"}')), 'bad request');
});

test('getChatErrorText falls back for empty, missing and HTML payloads', () => {
  const fallback = '对话请求失败，请检查网络或稍后重试。';

  assert.equal(getChatErrorText(undefined), fallback);
  assert.equal(getChatErrorText(null), fallback);
  assert.equal(getChatErrorText(new Error('   ')), fallback);
  assert.equal(
    getChatErrorText(new Error('<!DOCTYPE html><html><body>500</body></html>')),
    fallback
  );
  assert.equal(getChatErrorText(new Error('{"unexpected":true}')), '{"unexpected":true}');
});

test('getChatErrorText keeps plain text and truncates very long payloads', () => {
  assert.equal(getChatErrorText(new Error('network down')), 'network down');

  const long = getChatErrorText(new Error('x'.repeat(500)));
  assert.equal(long.length, 201);
  assert.ok(long.endsWith('…'));
});
