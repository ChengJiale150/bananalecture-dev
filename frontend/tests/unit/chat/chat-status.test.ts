import test from 'node:test';
import assert from 'node:assert/strict';
import {
  getChatErrorText,
  getComposerState,
  shouldShowPendingAssistant,
} from '@/features/chat/chat-status';

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

test('shouldShowPendingAssistant fills the gap before the first stream chunk', () => {
  const userTurn = [{ role: 'user' }];

  // Right after sendMessage(): the request is in flight, the assistant bubble is not there yet.
  assert.equal(shouldShowPendingAssistant('submitted', userTurn), true);
  // The SDK pushed the assistant message when the stream started — the real bubble takes over.
  assert.equal(
    shouldShowPendingAssistant('streaming', [{ role: 'user' }, { role: 'assistant' }]),
    false
  );
  // `regenerate`/resume can stream while the transcript still ends on the user message.
  assert.equal(shouldShowPendingAssistant('streaming', userTurn), true);
});

test('shouldShowPendingAssistant never renders outside an active request', () => {
  assert.equal(shouldShowPendingAssistant('ready', [{ role: 'user' }]), false);
  assert.equal(
    shouldShowPendingAssistant('ready', [{ role: 'user' }, { role: 'assistant' }]),
    false
  );
  // A failed or aborted request is surfaced by the error card, not by a spinner bubble.
  assert.equal(shouldShowPendingAssistant('error', [{ role: 'user' }]), false);
  assert.equal(shouldShowPendingAssistant('submitted', []), true);
});
