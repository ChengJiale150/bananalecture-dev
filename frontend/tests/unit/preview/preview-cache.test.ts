import test from 'node:test';
import assert from 'node:assert/strict';
import type { ProjectRecord } from '@/features/projects/types';
import {
  clearCachedDialogues,
  clearProjectPreviewCache,
  readCachedDialogues,
  readCachedProject,
  updateCachedProject,
  writeCachedDialogues,
  writeCachedProject,
} from '@/features/preview/utils';

class SessionStorageMock {
  private store = new Map<string, string>();

  get length() {
    return this.store.size;
  }

  key(index: number) {
    return Array.from(this.store.keys())[index] ?? null;
  }

  getItem(key: string) {
    return this.store.get(key) ?? null;
  }

  setItem(key: string, value: string) {
    this.store.set(key, value);
  }

  removeItem(key: string) {
    this.store.delete(key);
  }

  clear() {
    this.store.clear();
  }
}

function createProject(): ProjectRecord {
  return {
    id: 'project-1',
    userId: 'admin',
    title: 'Project 1',
    createdAt: 1,
    updatedAt: 2,
    messages: [],
    pptPlan: {
      slides: [
        {
          id: 'slide-1',
          type: 'cover',
          title: '封面',
          description: '课程封面',
          dialogues: undefined,
        },
      ],
    },
  };
}

test('preview cache reads from sessionStorage and supports project updates', () => {
  const originalWindow = globalThis.window;
  const sessionStorage = new SessionStorageMock();
  globalThis.window = { sessionStorage } as unknown as typeof window;

  try {
    const project = createProject();
    writeCachedProject(project);

    assert.deepEqual(readCachedProject(project.id), project);

    const updated = updateCachedProject(project.id, (currentProject) => ({
      ...currentProject,
      title: 'Updated Project',
    }));

    assert.equal(updated?.title, 'Updated Project');
    assert.equal(readCachedProject(project.id)?.title, 'Updated Project');
    assert.match(sessionStorage.getItem('preview:project:project-1') ?? '', /Updated Project/);
  } finally {
    globalThis.window = originalWindow;
  }
});

test('dialogue cache supports read, clear, and project-wide invalidation', () => {
  const originalWindow = globalThis.window;
  const sessionStorage = new SessionStorageMock();
  globalThis.window = { sessionStorage } as unknown as typeof window;

  try {
    writeCachedProject(createProject());
    writeCachedDialogues('project-1', 'slide-1', [
      { id: 'dialogue-1', role: '旁白', content: '第一句', emotion: '无明显情感', speed: '中速' },
    ]);
    writeCachedDialogues('project-1', 'slide-2', [
      { id: 'dialogue-2', role: '大雄', content: '第二句', emotion: '开心的', speed: '快速' },
    ]);

    assert.equal(readCachedDialogues('project-1', 'slide-1')?.length, 1);

    clearCachedDialogues('project-1', 'slide-1');
    assert.equal(readCachedDialogues('project-1', 'slide-1'), null);
    assert.equal(readCachedDialogues('project-1', 'slide-2')?.length, 1);

    clearProjectPreviewCache('project-1');
    assert.equal(readCachedProject('project-1'), null);
    assert.equal(readCachedDialogues('project-1', 'slide-2'), null);
    assert.equal(sessionStorage.length, 0);
  } finally {
    globalThis.window = originalWindow;
  }
});
