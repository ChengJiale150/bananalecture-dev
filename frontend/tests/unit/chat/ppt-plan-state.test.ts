import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createPptPlan,
  extractLatestPptPlanState,
  getPptPlanSignature,
  shouldApplyIncomingPlanToModal,
  shouldSyncCompletedPptPlan,
} from '@/features/chat/ppt-plan-state';

test('extractLatestPptPlanState keeps the latest draft and completed tool result separately', () => {
  const state = extractLatestPptPlanState([
    {
      id: 'm1',
      parts: [
        {
          type: 'tool-create_ppt_plan',
          state: 'output-available',
          toolCallId: 'tool-1',
          output: {
            slides: [
              { type: 'cover', title: '封面', description: '已完成', content: '第一页' },
            ],
          },
        },
      ],
    },
    {
      id: 'm2',
      parts: [
        {
          type: 'tool-create_ppt_plan',
          state: 'input-available',
          toolCallId: 'tool-2',
          args: {
            slides: [
              { type: 'cover', title: '新草案', description: '流式中', content: '第二版' },
            ],
          },
        },
      ],
    },
  ]);

  assert.equal(state.hasDraft, true);
  assert.equal(state.hasCompleted, true);
  assert.equal(state.completedToolCallId, 'tool-1');
  assert.equal(state.draftSlides[0]?.title, '新草案');
  assert.equal(state.completedSlides[0]?.title, '封面');
});

test('shouldSyncCompletedPptPlan only allows syncing completed plans after chat returns to ready', () => {
  const extraction = extractLatestPptPlanState([
    {
      id: 'm1',
      parts: [
        {
          type: 'tool-create_ppt_plan',
          state: 'output-available',
          toolCallId: 'tool-1',
          output: {
            slides: [
              { type: 'cover', title: '封面', description: '介绍', content: '内容' },
            ],
          },
        },
      ],
    },
  ]);

  const signature = getPptPlanSignature(extraction.completedSlides);

  assert.equal(shouldSyncCompletedPptPlan('streaming', extraction, '[]'), false);
  assert.equal(shouldSyncCompletedPptPlan('ready', extraction, '[]'), true);
  assert.equal(shouldSyncCompletedPptPlan('ready', extraction, signature), false);
});

test('getPptPlanSignature ignores backend ids and media fields when comparing plans', () => {
  const first = getPptPlanSignature([
    {
      id: 'slide-1',
      type: 'cover',
      title: '封面',
      description: '介绍',
      content: '内容',
      imagePath: 'a.png',
      audioPath: 'a.mp3',
    },
  ]);
  const second = getPptPlanSignature([
    {
      id: 'slide-99',
      type: 'cover',
      title: '封面',
      description: '介绍',
      content: '内容',
      imagePath: 'b.png',
      audioPath: 'b.mp3',
    },
  ]);

  assert.equal(first, second);
  assert.deepEqual(createPptPlan([]), undefined);
  assert.deepEqual(createPptPlan([{ id: '', type: 'content', title: '页', description: '描述', content: '' }]), {
    slides: [{ id: '', type: 'content', title: '页', description: '描述', content: '' }],
  });
});

test('shouldApplyIncomingPlanToModal blocks prop sync while editing or mutating', () => {
  assert.equal(shouldApplyIncomingPlanToModal(null, false), true);
  assert.equal(shouldApplyIncomingPlanToModal(0, false), false);
  assert.equal(shouldApplyIncomingPlanToModal(null, true), false);
});
