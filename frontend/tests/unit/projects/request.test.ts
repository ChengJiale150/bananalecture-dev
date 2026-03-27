import test from 'node:test';
import assert from 'node:assert/strict';

import { createBananaLectureRequester } from '@/shared/api/banana/request';

test('request uses a relative same-origin path when baseUrl is relative', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  const requester = createBananaLectureRequester({
    fetch: (async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ input, init });
      return new Response(JSON.stringify({ code: 200, message: 'success', data: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }) as typeof fetch,
  });

  await requester.requestJson('/admin/projects', {
    method: 'GET',
    query: { page: 2, page_size: 10 },
  });

  assert.equal(calls.length, 1);
  assert.equal(calls[0].input, '/api/v1/admin/projects?page=2&page_size=10');
});

test('buildFileUrl preserves relative proxied media paths', () => {
  const requester = createBananaLectureRequester();

  const result = requester.buildFileUrl('/projects/project-1/video/file');

  assert.equal(result, '/api/v1/projects/project-1/video/file');
});

test('absolute baseUrl still builds absolute upstream URLs', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  const requester = createBananaLectureRequester({
    baseUrl: 'http://localhost:8000/api/v1',
    fetch: (async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ input, init });
      return new Response(JSON.stringify({ code: 200, message: 'success', data: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }) as typeof fetch,
  });

  await requester.requestJson('/tasks/task-1', { method: 'GET' });

  assert.equal(calls.length, 1);
  assert.equal(String(calls[0].input), 'http://localhost:8000/api/v1/tasks/task-1');
  assert.equal(requester.buildFileUrl('/projects/project-1/video/file'), 'http://localhost:8000/api/v1/projects/project-1/video/file');
});
