import test from 'node:test';
import assert from 'node:assert/strict';

import { buildSystemPrompt } from '@/server/planner/prompt';

test('buildSystemPrompt injects the doraemon prop guideline', () => {
  const prompt = buildSystemPrompt({ templateId: 'doraemon' });

  assert.match(prompt, /## 道具使用规范（全片统一规划）/);
  assert.match(prompt, /全片道具最多 2 个/);
  assert.match(prompt, /content 中写明哆啦A梦从口袋里掏出该道具/);
  assert.match(prompt, /后续对话稿只依据 content 决定道具角色/);
});

test('buildSystemPrompt omits the prop guideline for templates without props', () => {
  const prompt = buildSystemPrompt({ templateId: 'xiyouji' });

  assert.doesNotMatch(prompt, /道具使用规范/);
  assert.doesNotMatch(prompt, /全片道具最多 2 个/);
});
