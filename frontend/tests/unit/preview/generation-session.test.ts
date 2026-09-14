import test from 'node:test';
import assert from 'node:assert/strict';
import type { TaskProgress } from '@/features/projects/types';
import {
  advanceGenerationSession,
  attachTaskToGenerationStage,
  createGenerationSession,
  finalizeGenerationSession,
  getActiveGenerationStageState,
  getGenerationFailure,
  getGenerationOverallProgress,
  getGenerationStageLabel,
  getGenerationStageStatus,
  getNextGenerationStage,
  markGenerationStageCompleted,
  updateGenerationSessionTask,
} from '@/features/preview/utils/generation-session';
import type { GenerationStage } from '@/features/projects/types';

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

test('stage status view reports the running stage and page position', () => {
  const task = createTask({ currentStep: 3, totalSteps: 10 });
  const session = createGenerationSession('project-1', 'pipeline', 'images', task);

  const view = getGenerationStageStatus(session);

  assert.equal(view?.stage, 'images');
  assert.equal(view?.label, '图片');
  assert.equal(view?.statusText, '生成中');
  assert.equal(view?.progressText, '第 3/10 页');
  assert.equal(view?.isActive, true);
});

test('stage status view reports the video composition step', () => {
  const renderingTask = createTask({
    id: 'task-video',
    type: 'video_generation',
    currentStep: 10,
    totalSteps: 11,
  });
  const renderingSession = createGenerationSession('project-1', 'pipeline', 'video', renderingTask);
  assert.equal(getGenerationStageStatus(renderingSession)?.progressText, '第 10/11 页');

  const composingSession = updateGenerationSessionTask(
    renderingSession,
    createTask({ id: 'task-video', type: 'video_generation', currentStep: 11, totalSteps: 11 })
  );

  const view = getGenerationStageStatus(composingSession);

  assert.equal(view?.label, '视频');
  assert.equal(view?.progressText, '正在合成视频');
});

test('stage status view hides the page position when total steps is unknown', () => {
  const task = createTask({ currentStep: 0, totalSteps: 0 });
  const session = createGenerationSession('project-1', 'pipeline', 'audio', task);

  const view = getGenerationStageStatus(session);

  assert.equal(view?.progressText, null);
  assert.equal(view?.isActive, true);
});

test('stage status view clamps out-of-range current steps', () => {
  const task = createTask({ currentStep: 12, totalSteps: 10 });
  const session = createGenerationSession('project-1', 'pipeline', 'images', task);

  assert.equal(getGenerationStageStatus(session)?.progressText, '第 10/10 页');
});

test('stage status view marks paused sessions as inactive', () => {
  const task = createTask({ status: 'paused', currentStep: 2, totalSteps: 10 });
  const session = createGenerationSession('project-1', 'pipeline', 'dialogues', task);

  const view = getGenerationStageStatus(session);

  assert.equal(view?.label, '口播稿');
  assert.equal(view?.statusText, '已暂停');
  assert.equal(view?.isActive, false);
  assert.equal(view?.progressText, null);
});

test('stage status view falls back to the first running stage when current stage is missing', () => {
  const task = createTask({ currentStep: 1, totalSteps: 4 });
  const session = {
    ...createGenerationSession('project-1', 'pipeline', 'audio', task),
    currentStage: null,
  };

  assert.equal(getActiveGenerationStageState(session)?.stage, 'audio');
  assert.equal(getGenerationStageStatus(session)?.label, '音频');
});

test('stage status view is empty when no session is running', () => {
  assert.equal(getGenerationStageStatus(null), null);
  assert.equal(getActiveGenerationStageState(null), null);
});

test('failed task polling records the failed stage and friendly retry message', () => {
  const task = createTask({ currentStep: 4, totalSteps: 10 });
  const running = createGenerationSession('project-1', 'single-stage', 'images', task);
  const failedTask = createTask({ status: 'failed', currentStep: 4, totalSteps: 10 });
  const failed = updateGenerationSessionTask(running, failedTask);

  assert.equal(failed.status, 'failed');
  assert.equal(failed.failedStage, 'images');
  assert.equal(getGenerationStageStatus(failed)?.statusText, '生成失败');

  const failure = getGenerationFailure(failed);
  assert.equal(failure?.stageLabel, '图片');
  assert.equal(failure?.message, '图片生成失败，请点击“继续生成”重试');
  assert.equal(failure?.message.includes('Slide'), false);
});

test('resuming a failed session clears the failure and reports progress again', () => {
  const running = createGenerationSession(
    'project-1',
    'single-stage',
    'images',
    createTask({ currentStep: 4, totalSteps: 10 })
  );
  const failed = updateGenerationSessionTask(
    running,
    createTask({ status: 'failed', currentStep: 4, totalSteps: 10 })
  );

  const resumed = updateGenerationSessionTask(
    failed,
    createTask({ status: 'running', currentStep: 5, totalSteps: 10 })
  );

  assert.equal(resumed.status, 'running');
  assert.equal(resumed.failedStage, null);
  assert.equal(getGenerationFailure(resumed), null);
  assert.equal(getGenerationStageStatus(resumed)?.progressText, '第 5/10 页');
});

test('finalizing a failed session keeps the stage for the failure message', () => {
  const task = createTask({ currentStep: 2, totalSteps: 6 });
  const running = createGenerationSession('project-1', 'single-stage', 'dialogues', task);
  const failed = finalizeGenerationSession(running, 'failed');

  assert.equal(failed.failedStage, 'dialogues');
  assert.equal(getGenerationFailure(failed)?.stageLabel, '口播稿');
});

test('successful sessions have no failure message', () => {
  const task = createTask({ currentStep: 10, totalSteps: 10 });
  const session = createGenerationSession('project-1', 'pipeline', 'images', task);

  assert.equal(getGenerationFailure(session), null);
  assert.equal(getGenerationFailure(finalizeGenerationSession(session, 'completed')), null);
});

test('stage labels are localized for every generation stage', () => {
  const stages: GenerationStage[] = ['images', 'dialogues', 'audio', 'video'];

  assert.deepEqual(stages.map(getGenerationStageLabel), ['图片', '口播稿', '音频', '视频']);
});

test('single stage sessions created by startStageTask expose Chinese labels', () => {
  const task = createTask({ id: 'task-4', type: 'image_generation', currentStep: 1, totalSteps: 3 });
  const session = createGenerationSession('project-1', 'single-stage', 'images', task);

  assert.equal(session.stages[0].label, '图片');
  assert.equal(getGenerationStageStatus(session)?.label, '图片');
});
