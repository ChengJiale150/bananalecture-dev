import test from 'node:test';
import assert from 'node:assert/strict';

test('listProjects requests paginated data and maps pagination fields', async () => {
  const createdAt = '2026-03-26T10:00:00Z';
  const updatedAt = '2026-03-26T10:05:00Z';
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });

    return new Response(
      JSON.stringify({
        code: 200,
        message: 'success',
        data: {
          items: [
            {
              id: 'project-1',
              name: 'Project 1',
              created_at: createdAt,
              updated_at: updatedAt,
            },
          ],
          pagination: {
            page: 2,
            page_size: 10,
            total: 23,
            total_pages: 3,
          },
        },
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }) as typeof fetch;

  try {
    const { listProjects } = await import('@/features/projects/api');
    const result = await listProjects({ page: 2, page_size: 10 });

    assert.equal(calls.length, 1);
    assert.equal((calls[0].init?.method ?? 'GET').toUpperCase(), 'GET');

    const url = String(calls[0].input);
    assert.match(url, /\/api\/v1\/admin\/projects/);
    assert.match(url, /page=2/);
    assert.match(url, /page_size=10/);
    assert.match(url, /sort_by=updated_at/);
    assert.match(url, /order=desc/);

    assert.deepEqual(result, {
      items: [
        {
          id: 'project-1',
          title: 'Project 1',
          createdAt: Date.parse(createdAt),
          updatedAt: Date.parse(updatedAt),
        },
      ],
      pagination: {
        page: 2,
        pageSize: 10,
        total: 23,
        totalPages: 3,
      },
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('getProject maps ISO timestamps to numbers, preserves storage keys, and sorts slides by idx', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });

    return new Response(
      JSON.stringify({
        code: 200,
        message: 'success',
        data: {
          id: 'project-1',
          user_id: 'admin',
          name: 'Project 1',
          messages: '[]',
          video_path: 'projects/project-1/video/final.mp4',
          created_at: '2026-03-26T10:00:00Z',
          updated_at: '2026-03-26T10:05:00Z',
          slides: [
            {
              id: 'slide-2',
              project_id: 'project-1',
              type: 'content',
              title: '第二页',
              description: '第二页描述',
              content: '第二页内容',
              idx: 2,
              image_path: 'projects/project-1/slides/slide-2/image/original.webp',
              audio_path: null,
              created_at: '2026-03-26T10:02:00Z',
              updated_at: '2026-03-26T10:06:00Z',
            },
            {
              id: 'slide-1',
              project_id: 'project-1',
              type: 'cover',
              title: '第一页',
              description: '第一页描述',
              content: '第一页内容',
              idx: 1,
              image_path: null,
              audio_path: 'projects/project-1/slides/slide-1/audio/merged.mp3',
              created_at: '2026-03-26T10:01:00Z',
              updated_at: '2026-03-26T10:03:00Z',
            },
          ],
        },
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }) as typeof fetch;

  try {
    const { getProject } = await import('@/features/projects/api');
    const result = await getProject('project-1');

    assert.equal(calls.length, 1);
    assert.equal((calls[0].init?.method ?? 'GET').toUpperCase(), 'GET');
    assert.match(String(calls[0].input), /\/api\/v1\/projects\/project-1/);

    assert.deepEqual(result, {
      id: 'project-1',
      userId: 'admin',
      title: 'Project 1',
      createdAt: Date.parse('2026-03-26T10:00:00Z'),
      updatedAt: Date.parse('2026-03-26T10:05:00Z'),
      messages: [],
      videoPath: 'projects/project-1/video/final.mp4',
      pptPlan: {
        slides: [
          {
            id: 'slide-1',
            type: 'cover',
            title: '第一页',
            description: '第一页描述',
            content: '第一页内容',
            imagePath: undefined,
            audioPath: 'projects/project-1/slides/slide-1/audio/merged.mp3',
            dialogues: undefined,
          },
          {
            id: 'slide-2',
            type: 'content',
            title: '第二页',
            description: '第二页描述',
            content: '第二页内容',
            imagePath: 'projects/project-1/slides/slide-2/image/original.webp',
            audioPath: undefined,
            dialogues: undefined,
          },
        ],
      },
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('downloadVideoFile requests the proxied file endpoint and preserves filename', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });

    return new Response(new Blob(['video-bytes'], { type: 'video/mp4' }), {
      status: 200,
      headers: {
        'Content-Type': 'video/mp4',
        'Content-Disposition': 'attachment; filename="lesson.mp4"',
      },
    });
  }) as typeof fetch;

  try {
    const { downloadVideoFile } = await import('@/features/projects/api');
    const result = await downloadVideoFile('project-42');

    assert.equal(calls.length, 1);
    assert.equal((calls[0].init?.method ?? 'GET').toUpperCase(), 'GET');
    assert.match(String(calls[0].input), /\/api\/v1\/projects\/project-42\/video\/file/);
    assert.equal(result.filename, 'lesson.mp4');
    assert.equal(result.blob.type, 'video/mp4');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('modifySlideImage posts prompt payload to the proxied modify endpoint', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });

    return new Response(
      JSON.stringify({
        code: 200,
        message: '图片修改成功',
        data: null,
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }) as typeof fetch;

  try {
    const { modifySlideImage } = await import('@/features/projects/api');
    await modifySlideImage('project-1', 'slide-2', '改成教室背景');

    assert.equal(calls.length, 1);
    assert.equal((calls[0].init?.method ?? 'GET').toUpperCase(), 'POST');
    assert.match(
      String(calls[0].input),
      /\/api\/v1\/projects\/project-1\/slides\/slide-2\/image\/modify/
    );
    assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { prompt: '改成教室背景' });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('reorderDialogues posts ordered dialogue ids to the proxy endpoint', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });

    return new Response(
      JSON.stringify({
        code: 200,
        message: '对话排序更新成功',
        data: { dialogues: [] },
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }) as typeof fetch;

  try {
    const { reorderDialogues } = await import('@/features/projects/api');
    await reorderDialogues('project-1', 'slide-2', ['dialogue-2', 'dialogue-1']);

    assert.equal(calls.length, 1);
    assert.equal((calls[0].init?.method ?? 'GET').toUpperCase(), 'POST');
    assert.match(
      String(calls[0].input),
      /\/api\/v1\/projects\/project-1\/slides\/slide-2\/dialogues\/reorder/
    );
    assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {
      dialogue_ids: ['dialogue-2', 'dialogue-1'],
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('reorderSlides posts ordered slide ids to the proxy endpoint', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });

    return new Response(
      JSON.stringify({
        code: 200,
        message: '幻灯片排序更新成功',
        data: { slides: [] },
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }) as typeof fetch;

  try {
    const { reorderSlides } = await import('@/features/projects/api');
    await reorderSlides('project-1', ['slide-3', 'slide-1']);

    assert.equal(calls.length, 1);
    assert.equal((calls[0].init?.method ?? 'GET').toUpperCase(), 'POST');
    assert.match(String(calls[0].input), /\/api\/v1\/projects\/project-1\/slides\/reorder/);
    assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {
      slide_ids: ['slide-3', 'slide-1'],
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('getDialogueAudioUrl builds the proxied dialogue audio path', async () => {
  const { getDialogueAudioUrl } = await import('@/features/projects/api');
  const result = getDialogueAudioUrl('project-1', 'slide-2', 'dialogue-3');

  assert.equal(result, '/api/v1/projects/project-1/slides/slide-2/dialogues/dialogue-3/audio/file');
});
