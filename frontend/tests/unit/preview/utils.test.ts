import test from 'node:test';
import assert from 'node:assert/strict';
import type { Dialogue } from '@/features/projects/types';
import {
  buildPreviewQueryString,
  getCurrentSlideImageUrl,
  removeDialogueById,
  reorderDialoguesLocally,
  upsertDialogue,
} from '@/features/preview/utils';

const dialogues: Dialogue[] = [
  { id: 'dialogue-1', role: '旁白', content: '第一句', emotion: '无明显情感', speed: '中速' },
  { id: 'dialogue-2', role: '大雄', content: '第二句', emotion: '开心的', speed: '快速' },
  { id: 'dialogue-3', role: '哆啦A梦', content: '第三句', emotion: '惊讶的', speed: '慢速' },
];

test('reorderDialoguesLocally swaps the selected dialogue with its adjacent item', () => {
  const result = reorderDialoguesLocally(dialogues, 'dialogue-2', -1);
  assert.deepEqual(
    result.map(dialogue => dialogue.id),
    ['dialogue-2', 'dialogue-1', 'dialogue-3']
  );
});

test('upsertDialogue updates existing dialogue and appends new dialogue when missing', () => {
  const updated = upsertDialogue(dialogues, { ...dialogues[1], content: '更新后的第二句' });
  assert.equal(updated[1].content, '更新后的第二句');

  const appended = upsertDialogue(dialogues, {
    id: 'dialogue-4',
    role: '旁白',
    content: '第四句',
    emotion: '无明显情感',
    speed: '中速',
  });
  assert.deepEqual(
    appended.map(dialogue => dialogue.id),
    ['dialogue-1', 'dialogue-2', 'dialogue-3', 'dialogue-4']
  );
});

test('removeDialogueById removes only the specified dialogue', () => {
  const result = removeDialogueById(dialogues, 'dialogue-2');
  assert.deepEqual(
    result.map(dialogue => dialogue.id),
    ['dialogue-1', 'dialogue-3']
  );
});

test('buildPreviewQueryString removes legacy refresh and preserves other params', () => {
  const params = new URLSearchParams('id=project-1&page=3&refresh=123&foo=bar');
  assert.equal(
    buildPreviewQueryString(params, { removeRefresh: true }),
    'id=project-1&page=3&foo=bar'
  );
  assert.equal(
    buildPreviewQueryString(params, { page: 2, removeRefresh: true }),
    'id=project-1&page=2&foo=bar'
  );
});

test('getCurrentSlideImageUrl only exposes the current slide image url', () => {
  assert.equal(getCurrentSlideImageUrl({ slideId: 'slide-1', url: 'blob:a' }, 'slide-1'), 'blob:a');
  assert.equal(getCurrentSlideImageUrl({ slideId: 'slide-1', url: 'blob:a' }, 'slide-2'), null);
  assert.equal(getCurrentSlideImageUrl(null, 'slide-1'), null);
});
