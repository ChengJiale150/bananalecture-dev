import test from 'node:test';
import assert from 'node:assert/strict';
import { consumePreviewRefresh, markPreviewRefresh } from '@/features/preview/utils/refresh-signal';

class SessionStorageMock {
  private store = new Map<string, string>();

  getItem(key: string) {
    return this.store.get(key) ?? null;
  }

  setItem(key: string, value: string) {
    this.store.set(key, value);
  }

  removeItem(key: string) {
    this.store.delete(key);
  }
}

test('preview refresh signal is consumed only once per project', () => {
  const originalWindow = globalThis.window;
  const sessionStorage = new SessionStorageMock();
  globalThis.window = { sessionStorage } as unknown as typeof window;

  try {
    markPreviewRefresh('project-1');

    assert.equal(consumePreviewRefresh('project-1'), true);
    assert.equal(consumePreviewRefresh('project-1'), false);
    assert.equal(consumePreviewRefresh('project-2'), false);
  } finally {
    globalThis.window = originalWindow;
  }
});
