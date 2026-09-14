import type {
  GenerationSessionMode,
  GenerationSessionState,
  GenerationStage,
  GenerationStageState,
  GenerationStageStatus,
  TaskProgress,
} from '@/features/projects/types';
import {
  GENERATION_STAGES,
  GENERATION_STAGE_LABELS,
  GENERATION_STAGE_STATUS_TEXTS,
} from '@/features/projects/types';

export function getGenerationStageLabel(stage: GenerationStage) {
  return GENERATION_STAGE_LABELS[stage] ?? stage;
}

export function createGenerationStages(): GenerationStageState[] {
  return GENERATION_STAGES.map(stage => ({
    stage,
    label: getGenerationStageLabel(stage),
    status: 'pending',
    progress: 0,
  }));
}

export function createGenerationSession(
  projectId: string,
  mode: GenerationSessionMode,
  activeStage: GenerationStage,
  task?: TaskProgress | null
): GenerationSessionState {
  const stages = createGenerationStages().map(stageState =>
    stageState.stage === activeStage
      ? {
          ...stageState,
          status: task ? mapTaskStatusToStageStatus(task.status) : 'running',
          progress: task ? getTaskProgressPercent(task) : 0,
          taskId: task?.id,
          startedAt: Date.now(),
        }
      : stageState
  );

  return {
    mode,
    projectId,
    status: task ? mapTaskStatusToSessionStatus(task.status) : 'running',
    currentStage: activeStage,
    stages,
    activeTask: task ?? null,
    errorMessage: task?.errorMessage ?? null,
    updatedAt: Date.now(),
  };
}

export function updateGenerationSessionTask(
  session: GenerationSessionState,
  task: TaskProgress
): GenerationSessionState {
  if (!session.currentStage) {
    return {
      ...session,
      activeTask: task,
      status: mapTaskStatusToSessionStatus(task.status),
      errorMessage: task.errorMessage ?? null,
      updatedAt: Date.now(),
    };
  }

  const nextStatus = mapTaskStatusToStageStatus(task.status);
  const nextProgress = getTaskProgressPercent(task);
  const nextSessionStatus = mapTaskStatusToSessionStatus(task.status);

  return {
    ...session,
    status: nextSessionStatus,
    activeTask: task,
    errorMessage: task.errorMessage ?? null,
    failedStage: nextSessionStatus === 'failed' ? session.currentStage : null,
    stages: session.stages.map(stage =>
      stage.stage === session.currentStage
        ? {
            ...stage,
            status: nextStatus,
            progress: nextStatus === 'completed' ? 100 : nextProgress,
            taskId: task.id,
          }
        : stage
    ),
    updatedAt: Date.now(),
  };
}

export function attachTaskToGenerationStage(
  session: GenerationSessionState,
  stage: GenerationStage,
  task: TaskProgress
): GenerationSessionState {
  return {
    ...session,
    status: mapTaskStatusToSessionStatus(task.status),
    currentStage: stage,
    activeTask: task,
    errorMessage: task.errorMessage ?? null,
    stages: session.stages.map(item =>
      item.stage === stage
        ? {
            ...item,
            status: mapTaskStatusToStageStatus(task.status),
            progress:
              mapTaskStatusToStageStatus(task.status) === 'completed'
                ? 100
                : getTaskProgressPercent(task),
            taskId: task.id,
            startedAt: item.startedAt ?? Date.now(),
          }
        : item
    ),
    updatedAt: Date.now(),
  };
}

export function markGenerationStageCompleted(
  session: GenerationSessionState,
  stage: GenerationStage
): GenerationSessionState {
  const nextStages = session.stages.map(item =>
    item.stage === stage
      ? { ...item, status: 'completed' as GenerationStageStatus, progress: 100 }
      : item
  );

  return {
    ...session,
    stages: nextStages,
    activeTask: null,
    errorMessage: null,
    updatedAt: Date.now(),
  };
}

export function advanceGenerationSession(
  session: GenerationSessionState,
  nextStage: GenerationStage | null
): GenerationSessionState {
  if (!nextStage) {
    return {
      ...session,
      currentStage: null,
      status: 'completed',
      activeTask: null,
      updatedAt: Date.now(),
    };
  }

  return {
    ...session,
    currentStage: nextStage,
    status: 'running',
    activeTask: null,
    stages: session.stages.map(stage =>
      stage.stage === nextStage
        ? { ...stage, status: 'running', progress: 0, taskId: undefined, startedAt: Date.now() }
        : stage
    ),
    updatedAt: Date.now(),
  };
}

export function finalizeGenerationSession(
  session: GenerationSessionState,
  status: Extract<GenerationSessionState['status'], 'failed' | 'cancelled' | 'completed'>,
  task?: TaskProgress | null
): GenerationSessionState {
  const currentStage = session.currentStage;

  return {
    ...session,
    status,
    activeTask: task ?? null,
    errorMessage: task?.errorMessage ?? session.errorMessage ?? null,
    failedStage: status === 'failed' ? currentStage : session.failedStage ?? null,
    stages: currentStage
      ? session.stages.map(stage =>
          stage.stage === currentStage
            ? {
                ...stage,
                status: status === 'completed' ? 'completed' : status,
                progress: status === 'completed' ? 100 : stage.progress,
                taskId: task?.id ?? stage.taskId,
              }
            : stage
        )
      : session.stages,
    updatedAt: Date.now(),
  };
}

export function getNextGenerationStage(stage: GenerationStage): GenerationStage | null {
  const currentIndex = GENERATION_STAGES.indexOf(stage);
  if (currentIndex === -1 || currentIndex === GENERATION_STAGES.length - 1) {
    return null;
  }

  return GENERATION_STAGES[currentIndex + 1];
}

export function getTaskProgressPercent(task: Pick<TaskProgress, 'currentStep' | 'totalSteps'>) {
  if (task.totalSteps <= 0) {
    return 0;
  }

  const ratio = task.currentStep / task.totalSteps;
  return Math.max(0, Math.min(100, ratio * 100));
}

export function getGenerationOverallProgress(session: GenerationSessionState | null) {
  if (!session) {
    return 0;
  }

  if (session.mode === 'single-stage') {
    const activeStage = session.currentStage
      ? session.stages.find(stage => stage.stage === session.currentStage)
      : null;

    if (!activeStage) {
      return 0;
    }

    return Math.max(0, Math.min(100, activeStage.progress));
  }

  const stageWeight = 100 / GENERATION_STAGES.length;
  return session.stages.reduce((total, stage) => {
    if (stage.status === 'completed') {
      return total + stageWeight;
    }

    if (stage.status === 'running') {
      return total + (stage.progress / 100) * stageWeight;
    }

    return total;
  }, 0);
}

const ESTIMATED_SECONDS_PER_STEP: Record<GenerationStage, number> = {
  images: 90,
  dialogues: 60,
  audio: 30,
  video: 10,
};

export function getEstimatedRemainingSeconds(
  session: GenerationSessionState | null,
  activeTask: TaskProgress | null | undefined
): number | null {
  if (!session || session.status !== 'running') {
    return null;
  }

  let totalRemaining = 0;
  const now = Date.now();

  for (const stage of session.stages) {
    if (stage.status === 'completed' || stage.status === 'failed' || stage.status === 'cancelled') {
      continue;
    }

    const perStep = ESTIMATED_SECONDS_PER_STEP[stage.stage];

    if (stage.status === 'running' && activeTask && activeTask.totalSteps > 0) {
      const remainingSteps = activeTask.totalSteps - activeTask.currentStep;
      if (remainingSteps <= 0) {
        continue;
      }

      if (stage.startedAt && activeTask.currentStep > 0) {
        const elapsedSeconds = (now - stage.startedAt) / 1000;
        const actualRate = elapsedSeconds / activeTask.currentStep;
        totalRemaining += actualRate * remainingSteps;
      } else {
        totalRemaining += perStep * remainingSteps;
      }
    } else if (stage.status === 'pending') {
      const estimatedSteps = activeTask?.totalSteps ?? 1;
      totalRemaining += perStep * estimatedSteps;
    } else if (stage.status === 'running' && !activeTask) {
      totalRemaining += perStep;
    }
  }

  return Math.ceil(totalRemaining);
}

export function getCurrentGenerationStageState(session: GenerationSessionState | null) {
  if (!session?.currentStage) {
    return null;
  }

  return session.stages.find(stage => stage.stage === session.currentStage) ?? null;
}

export function isGenerationSessionActive(session: GenerationSessionState | null) {
  return Boolean(session && session.status === 'running');
}

export interface GenerationStatusView {
  stage: GenerationStage;
  label: string;
  statusText: string;
  progressText: string | null;
  isActive: boolean;
}

export interface GenerationFailureView {
  stageLabel: string | null;
  message: string;
}

export function getActiveGenerationStageState(session: GenerationSessionState | null) {
  if (!session) {
    return null;
  }

  const fallbackStage =
    session.status === 'running'
      ? session.stages.find(stage => stage.status === 'running') ?? null
      : null;

  const activeStage = session.currentStage
    ? session.stages.find(stage => stage.stage === session.currentStage) ?? fallbackStage
    : fallbackStage;

  if (!activeStage) {
    return null;
  }

  if (session.status !== 'running' && session.status !== 'paused' && session.status !== 'failed') {
    return null;
  }

  return activeStage;
}

export function getGenerationStageStatus(
  session: GenerationSessionState | null
): GenerationStatusView | null {
  const stageState = getActiveGenerationStageState(session);
  if (!stageState) {
    return null;
  }

  const isActive = session?.status === 'running';
  const task = session?.activeTask ?? null;
  const totalSteps = task?.totalSteps ?? 0;
  const currentStep = Math.max(0, task?.currentStep ?? 0);

  let progressText: string | null = null;
  if (isActive && totalSteps > 0) {
    if (stageState.stage === 'video' && currentStep >= totalSteps) {
      progressText = '正在合成视频';
    } else {
      const displayStep = Math.min(Math.max(currentStep, 1), totalSteps);
      progressText = `第 ${displayStep}/${totalSteps} 页`;
    }
  }

  let statusText = GENERATION_STAGE_STATUS_TEXTS.running;
  if (session?.status === 'paused') {
    statusText = GENERATION_STAGE_STATUS_TEXTS.paused;
  } else if (session?.status === 'failed' || stageState.status === 'failed') {
    statusText = GENERATION_STAGE_STATUS_TEXTS.failed;
  } else if (stageState.status === 'pending') {
    statusText = GENERATION_STAGE_STATUS_TEXTS.pending;
  }

  return {
    stage: stageState.stage,
    label: stageState.label || getGenerationStageLabel(stageState.stage),
    statusText,
    progressText,
    isActive,
  };
}

export function getGenerationFailure(
  session: GenerationSessionState | null
): GenerationFailureView | null {
  if (!session || session.status !== 'failed') {
    return null;
  }

  const failedStage = session.failedStage ?? session.currentStage ?? null;
  const stageLabel = failedStage ? getGenerationStageLabel(failedStage) : null;

  return {
    stageLabel,
    message: stageLabel
      ? `${stageLabel}生成失败，请点击“继续生成”重试`
      : '生成失败，请点击“继续生成”重试',
  };
}

export function isGenerationSessionResumable(session: GenerationSessionState | null) {
  return Boolean(session && (session.status === 'paused' || session.status === 'failed'));
}

export function mapTaskStatusToStageStatus(status: string): GenerationStageStatus {
  switch (status) {
    case 'completed':
      return 'completed';
    case 'failed':
      return 'failed';
    case 'cancelled':
      return 'cancelled';
    case 'paused':
      return 'paused';
    default:
      return 'running';
  }
}

function mapTaskStatusToSessionStatus(status: string): GenerationSessionState['status'] {
  switch (status) {
    case 'completed':
      return 'completed';
    case 'failed':
      return 'failed';
    case 'cancelled':
      return 'cancelled';
    case 'paused':
      return 'paused';
    default:
      return 'running';
  }
}

export function persistGenerationSession(_session: GenerationSessionState) {
  // No-op: generation session is managed server-side
}

export function loadGenerationSession(_projectId: string) {
  return null;
}

export function clearGenerationSession(_projectId: string) {
  // No-op: generation session is managed server-side
}
