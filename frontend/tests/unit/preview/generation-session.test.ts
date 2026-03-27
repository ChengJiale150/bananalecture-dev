import test from 'node:test';
import assert from 'node:assert/strict';
import type { TaskProgress } from '@/features/projects/types';
import {
  advanceGenerationSession,
  attachTaskToGenerationStage,
  createGenerationSession,
  getGenerationOverallProgress,
  getNextGenerationStage,
  markGenerationStageCompleted,
} from '@/features/preview/utils/generation-session';

function createTask(overrides: Partial<TaskProgress> = {}): TaskProgress {
  return {
    id: 'task-1',
    projectId: 'project-1',
    type: 'image_generation',
    status: 'running',
    currentStep: 5,
    totalSteps: 10,
    errorMessage: null,
    createdAt: '2026-03-26T00:00:00.000Z',
    updatedAt: '2026-03-26T00:00:00.000Z',
    ...overrides,
  };
}

test('pipeline progress advances in 25 percent stage increments', () => {
  const imagesTask = createTask({ currentStep: 5, totalSteps: 10 });
  const session = createGenerationSession('project-1', 'pipeline', 'images', imagesTask);

  assert.equal(Math.round(getGenerationOverallProgress(session)), 13);

  const completedImages = markGenerationStageCompleted(session, 'images');
  const advanced = advanceGenerationSession(completedImages, 'dialogues');
  const dialoguesTask = createTask({
    id: 'task-2',
    type: 'dialogue_generation',
    currentStep: 4,
    totalSteps: 8,
  });
  const updated = attachTaskToGenerationStage(advanced, 'dialogues', dialoguesTask);

  assert.equal(Math.round(getGenerationOverallProgress(updated)), 38);
});

test('single stage sessions only fill the selected stage range', () => {
  const audioTask = createTask({
    id: 'task-3',
    type: 'audio_generation',
    currentStep: 1,
    totalSteps: 2,
  });
  const session = createGenerationSession('project-1', 'single-stage', 'audio', audioTask);

  assert.equal(Math.round(getGenerationOverallProgress(session)), 50);
});

test('getNextGenerationStage follows the configured order', () => {
  assert.equal(getNextGenerationStage('images'), 'dialogues');
  assert.equal(getNextGenerationStage('dialogues'), 'audio');
  assert.equal(getNextGenerationStage('audio'), 'video');
  assert.equal(getNextGenerationStage('video'), null);
});
