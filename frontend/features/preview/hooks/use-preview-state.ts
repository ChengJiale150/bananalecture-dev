import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import type {
  Dialogue,
  GenerationSessionMode,
  GenerationSessionState,
  GenerationStage,
  PPTPlan,
  TaskProgress,
} from '@/features/projects/types';
import {
  addDialogue,
  batchGenerateAudio,
  batchGenerateDialogues,
  batchGenerateImages,
  cancelTask,
  deleteDialogue,
  downloadVideoFile,
  generateDialogues,
  generateSlideAudio,
  generateSlideImage,
  generateVideo,
  getDialogueAudioUrl,
  getProject,
  getSlideAudioUrl,
  getSlideImageUrl,
  getTask,
  listDialogues,
  modifySlideImage,
  reorderDialogues,
  updateDialogue,
} from '@/features/projects/api';
import { getPageParamFromSlideIndex, getSlideIndexFromPageParam } from '@/features/projects/utils';
import {
  advanceGenerationSession,
  attachTaskToGenerationStage,
  clearGenerationSession,
  createGenerationSession,
  finalizeGenerationSession,
  getCurrentGenerationStageState,
  getGenerationOverallProgress,
  getGenerationStageLabel,
  getNextGenerationStage,
  isGenerationSessionActive,
  loadGenerationSession,
  markGenerationStageCompleted,
  persistGenerationSession,
} from '@/features/preview/utils/generation-session';
import {
  clearProjectPreviewCache,
  normalizeDialogues,
  readCachedDialogues,
  readCachedProject,
  removeDialogueById,
  reorderDialoguesLocally,
  upsertDialogue,
  updateCachedProject,
  writeCachedDialogues,
  writeCachedProject,
} from '../utils';

const POLL_INTERVAL_MS = 2000;

function createErroredSession(
  projectId: string,
  mode: GenerationSessionMode,
  stage: GenerationStage,
  message: string
) {
  const base = createGenerationSession(projectId, mode, stage, null);

  return {
    ...base,
    status: 'failed' as const,
    errorMessage: message,
    stages: base.stages.map(item =>
      item.stage === stage ? { ...item, status: 'failed' as const, progress: 0 } : item
    ),
    updatedAt: Date.now(),
  };
}

export function usePreviewState(
  projectIdFromUrl: string | null,
  pageFromUrl: string | null,
  refreshToken: string | null
) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [plan, setPlan] = useState<PPTPlan | null>(null);
  const [projectId, setProjectId] = useState(projectIdFromUrl || '');
  const [projectVideoPath, setProjectVideoPath] = useState<string | undefined>();
  const [currentSlideIndex, setCurrentSlideIndexState] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeActionKey, setActiveActionKey] = useState<string | null>(null);
  const [generationSession, setGenerationSession] = useState<GenerationSessionState | null>(null);
  const generationSessionRef = useRef<GenerationSessionState | null>(null);

  useEffect(() => {
    generationSessionRef.current = generationSession;
  }, [generationSession]);

  const setCurrentSlideIndex = useCallback(
    (nextIndex: number) => {
      const nextPage = getPageParamFromSlideIndex(nextIndex);
      const params = new URLSearchParams(searchParams.toString());
      params.set('page', String(nextPage));
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const commitGenerationSession = useCallback(
    (nextSession: GenerationSessionState | null) => {
      generationSessionRef.current = nextSession;
      setGenerationSession(nextSession);

      const storageProjectId = nextSession?.projectId ?? projectId;
      if (!storageProjectId) {
        return;
      }

      if (nextSession) {
        persistGenerationSession(nextSession);
      } else {
        clearGenerationSession(storageProjectId);
      }
    },
    [projectId]
  );

  const applyProjectToState = useCallback((project: Awaited<ReturnType<typeof getProject>>) => {
    setPlan(project.pptPlan ?? null);
    setProjectVideoPath(project.videoPath ?? undefined);
    writeCachedProject(project);
    return project;
  }, []);

  const refreshProject = useCallback(
    async (options?: { force?: boolean; includeCurrentSlideDialogues?: boolean }) => {
      if (!projectId) return null;

      const force = options?.force ?? false;
      const includeCurrentSlideDialogues = options?.includeCurrentSlideDialogues ?? false;

      if (force) {
        clearProjectPreviewCache(projectId);
        setSlideImageTimestamp(Date.now());
        setSlideAudioTimestamp(Date.now());
      }

      const cachedProject = !force ? readCachedProject(projectId) : null;
      const project = cachedProject ?? (await getProject(projectId));
      applyProjectToState(project);

      if (!includeCurrentSlideDialogues) {
        return project;
      }

      const activeSlide = project.pptPlan?.slides[currentSlideIndex];
      if (!activeSlide?.id) {
        return project;
      }

      const dialogues = await listDialogues(projectId, activeSlide.id);
      writeCachedDialogues(projectId, activeSlide.id, dialogues);
      setPlan(prev => {
        if (!prev) {
          return prev;
        }

        return {
          slides: prev.slides.map(slide =>
            slide.id === activeSlide.id ? { ...slide, dialogues } : slide
          ),
        };
      });
      updateCachedProject(projectId, currentProject => ({
        ...currentProject,
        pptPlan: currentProject.pptPlan
          ? {
              slides: currentProject.pptPlan.slides.map(slide =>
                slide.id === activeSlide.id ? { ...slide, dialogues } : slide
              ),
            }
          : currentProject.pptPlan,
      }));

      return project;
    },
    [applyProjectToState, currentSlideIndex, projectId]
  );

  const replaceSlideDialoguesInState = useCallback(
    (slideId: string, dialogues: Dialogue[]) => {
      if (projectId) {
        writeCachedDialogues(projectId, slideId, dialogues);
        updateCachedProject(projectId, project => ({
          ...project,
          pptPlan: project.pptPlan
            ? {
                slides: project.pptPlan.slides.map(slide =>
                  slide.id === slideId ? { ...slide, dialogues } : slide
                ),
              }
            : project.pptPlan,
        }));
      }

      setPlan(prev => {
        if (!prev) return prev;
        return {
          slides: prev.slides.map(slide =>
            slide.id === slideId ? { ...slide, dialogues } : slide
          ),
        };
      });
    },
    [projectId]
  );

  const runAction = useCallback(async <T>(key: string, task: () => Promise<T>) => {
    setActiveActionKey(key);
    try {
      return await task();
    } catch (error) {
      console.error(`Failed action: ${key}`, error);
      return null;
    } finally {
      setActiveActionKey(current => (current === key ? null : current));
    }
  }, []);

  const startStageTask = useCallback(
    async (
      stage: GenerationStage,
      mode: GenerationSessionMode,
      baseSession?: GenerationSessionState | null
    ) => {
      if (!projectId) return;

      const startTask = {
        images: batchGenerateImages,
        dialogues: batchGenerateDialogues,
        audio: batchGenerateAudio,
        video: generateVideo,
      }[stage];

      try {
        const taskId = await startTask(projectId);
        const task = await getTask(taskId);
        const nextSession = baseSession
          ? attachTaskToGenerationStage(
              {
                ...baseSession,
                mode,
                status: 'running',
                currentStage: stage,
                activeTask: null,
                errorMessage: null,
              },
              stage,
              task
            )
          : createGenerationSession(projectId, mode, stage, task);

        commitGenerationSession(nextSession);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : `启动${getGenerationStageLabel(stage)}任务失败`;
        commitGenerationSession(createErroredSession(projectId, mode, stage, message));
      }
    },
    [commitGenerationSession, projectId]
  );

  useEffect(() => {
    const loadPlan = async () => {
      try {
        if (!projectIdFromUrl) {
          setProjectId('');
          setPlan(null);
          setProjectVideoPath(undefined);
          commitGenerationSession(null);
          return;
        }

        setProjectId(projectIdFromUrl);
        const shouldForceRefresh = Boolean(refreshToken);
        if (shouldForceRefresh) {
          clearProjectPreviewCache(projectIdFromUrl);
        }

        const cachedProject = !shouldForceRefresh ? readCachedProject(projectIdFromUrl) : null;
        const project = cachedProject ?? (await getProject(projectIdFromUrl));
        applyProjectToState(project);
        setCurrentSlideIndexState(
          getSlideIndexFromPageParam(pageFromUrl, project.pptPlan?.slides.length ?? 0)
        );
        commitGenerationSession(loadGenerationSession(projectIdFromUrl));
      } catch (error) {
        console.error('Failed to load preview plan:', error);
        setPlan(null);
        setProjectVideoPath(undefined);
      } finally {
        setIsLoading(false);
      }
    };

    void loadPlan();
  }, [applyProjectToState, commitGenerationSession, pageFromUrl, projectIdFromUrl, refreshToken]);

  useEffect(() => {
    if (!plan) return;
    setCurrentSlideIndexState(getSlideIndexFromPageParam(pageFromUrl, plan.slides.length));
  }, [pageFromUrl, plan]);

  useEffect(() => {
    if (!plan || plan.slides.length === 0) return;

    const nextIndex = getSlideIndexFromPageParam(pageFromUrl, plan.slides.length);
    const nextPage = getPageParamFromSlideIndex(nextIndex);
    const currentPage = searchParams.get('page');

    if (currentPage === String(nextPage)) {
      return;
    }

    const params = new URLSearchParams(searchParams.toString());
    params.set('page', String(nextPage));
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }, [pageFromUrl, pathname, plan, router, searchParams]);

  useEffect(() => {
    const restoredSession = generationSessionRef.current;
    if (!restoredSession || restoredSession.status !== 'running' || !projectId) {
      return;
    }

    const currentStage = restoredSession.currentStage;
    const currentStageState = getCurrentGenerationStageState(restoredSession);
    const activeTaskId = restoredSession.activeTask?.id ?? currentStageState?.taskId;

    if (activeTaskId || !currentStage || restoredSession.mode !== 'pipeline') {
      return;
    }

    if (currentStageState?.status === 'completed') {
      const nextStage = getNextGenerationStage(currentStage);
      if (nextStage) {
        void startStageTask(nextStage, restoredSession.mode, restoredSession);
      }
    }
  }, [projectId, startStageTask]);

  const activeSessionStatus = generationSession?.status;
  const activeTaskId =
    activeSessionStatus === 'running' && generationSession
      ? (generationSession.activeTask?.id ??
        getCurrentGenerationStageState(generationSession)?.taskId)
      : undefined;

  useEffect(() => {
    if (activeSessionStatus !== 'running' || !activeTaskId) {
      return;
    }

    let cancelled = false;
    let intervalId = 0;

    const pollTask = async () => {
      try {
        const nextTask = await getTask(activeTaskId);
        if (cancelled) return;

        const currentSession = generationSessionRef.current;
        if (!currentSession) {
          return;
        }

        const updatedSession = updateAndPersistCurrentTask(currentSession, nextTask);

        if (nextTask.status === 'pending' || nextTask.status === 'running') {
          return;
        }

        window.clearInterval(intervalId);
        await refreshProject();

        if (nextTask.status === 'completed') {
          await completeGenerationSession(updatedSession, nextTask);
          return;
        }

        commitGenerationSession(
          finalizeGenerationSession(
            updatedSession,
            nextTask.status === 'cancelled' ? 'cancelled' : 'failed',
            nextTask
          )
        );
      } catch (error) {
        console.error('Failed to poll task:', error);
        window.clearInterval(intervalId);
      }
    };

    const updateAndPersistCurrentTask = (
      currentSession: GenerationSessionState,
      nextTask: TaskProgress
    ) => {
      const nextSession = attachTaskToGenerationStage(
        {
          ...currentSession,
          activeTask: nextTask,
        },
        currentSession.currentStage ?? 'images',
        nextTask
      );
      commitGenerationSession(nextSession);
      return nextSession;
    };

    const completeGenerationSession = async (
      currentSession: GenerationSessionState,
      nextTask: TaskProgress
    ) => {
      const activeStage = currentSession.currentStage;
      if (!activeStage) {
        commitGenerationSession(finalizeGenerationSession(currentSession, 'completed', nextTask));
        return;
      }

      const completedSession = markGenerationStageCompleted(currentSession, activeStage);

      if (completedSession.mode === 'pipeline') {
        const nextStage = getNextGenerationStage(activeStage);
        if (nextStage) {
          const advancedSession = advanceGenerationSession(completedSession, nextStage);
          commitGenerationSession(advancedSession);
          await startStageTask(nextStage, 'pipeline', advancedSession);
          return;
        }
      }

      commitGenerationSession(finalizeGenerationSession(completedSession, 'completed', nextTask));
    };

    void pollTask();
    intervalId = window.setInterval(() => {
      void pollTask();
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [activeSessionStatus, activeTaskId, commitGenerationSession, refreshProject, startStageTask]);

  const currentSlide = plan?.slides[currentSlideIndex];
  const [slideImageTimestamp, setSlideImageTimestamp] = useState(Date.now());
  const [slideAudioTimestamp, setSlideAudioTimestamp] = useState(Date.now());

  useEffect(() => {
    if (!currentSlide?.id || Array.isArray(currentSlide.dialogues)) return;

    let cancelled = false;
    const loadDialogues = async () => {
      try {
        const cachedDialogues = readCachedDialogues(projectId, currentSlide.id);
        if (cachedDialogues) {
          replaceSlideDialoguesInState(currentSlide.id, cachedDialogues);
          return;
        }

        const dialogues = await listDialogues(projectId, currentSlide.id);
        if (cancelled) return;
        replaceSlideDialoguesInState(currentSlide.id, dialogues);
      } catch (error) {
        console.error('Failed to fetch dialogues:', error);
      }
    };

    void loadDialogues();
    return () => {
      cancelled = true;
    };
  }, [currentSlide?.dialogues, currentSlide?.id, projectId, replaceSlideDialoguesInState]);

  const displayDialogues = useMemo(() => currentSlide?.dialogues ?? [], [currentSlide]);
  const slideImageUrl = useMemo(
    () =>
      projectId && currentSlide?.id && currentSlide.imagePath
        ? `${getSlideImageUrl(projectId, currentSlide.id)}?t=${slideImageTimestamp}`
        : null,
    [currentSlide?.id, currentSlide?.imagePath, projectId, slideImageTimestamp]
  );
  const slideAudioUrl = useMemo(
    () =>
      projectId && currentSlide?.id && currentSlide.audioPath
        ? `${getSlideAudioUrl(projectId, currentSlide.id)}?t=${slideAudioTimestamp}`
        : null,
    [currentSlide?.audioPath, currentSlide?.id, projectId, slideAudioTimestamp]
  );

  const handleGenerateDialogues = useCallback(async () => {
    if (!projectId || !currentSlide?.id) return;
    const actionKey = `generate-dialogues:${currentSlide.id}`;
    await runAction(actionKey, async () => {
      const dialogues = normalizeDialogues(await generateDialogues(projectId, currentSlide.id));
      replaceSlideDialoguesInState(currentSlide.id, dialogues);
      return dialogues;
    });
  }, [currentSlide?.id, projectId, replaceSlideDialoguesInState, runAction]);

  const handleStartStageGeneration = useCallback(
    async (stage: GenerationStage) => {
      if (!projectId || isGenerationSessionActive(generationSessionRef.current)) {
        return;
      }

      await startStageTask(stage, 'single-stage');
    },
    [projectId, startStageTask]
  );

  const handleGenerateAll = useCallback(async () => {
    if (!projectId || isGenerationSessionActive(generationSessionRef.current)) {
      return;
    }

    await startStageTask('images', 'pipeline');
  }, [projectId, startStageTask]);

  const handleStopGeneration = useCallback(async () => {
    const activeTaskId = generationSessionRef.current?.activeTask?.id;
    if (!activeTaskId) return;

    try {
      const cancelledTask = await cancelTask(activeTaskId);
      const currentSession = generationSessionRef.current;
      if (!currentSession) return;
      commitGenerationSession(
        finalizeGenerationSession(currentSession, 'cancelled', cancelledTask)
      );
    } catch (error) {
      console.error('Failed to cancel task:', error);
    }
  }, [commitGenerationSession]);

  const handleAddDialogue = useCallback(async () => {
    if (!projectId || !currentSlide?.id) return null;
    const actionKey = `dialogue-add:${currentSlide.id}`;
    return runAction(actionKey, async () => {
      const createdDialogue = await addDialogue(projectId, currentSlide.id, {
        id: '',
        role: '旁白',
        content: '',
        emotion: '无明显情感',
        speed: '中速',
      });
      replaceSlideDialoguesInState(currentSlide.id, [...displayDialogues, createdDialogue]);
      return createdDialogue;
    });
  }, [currentSlide?.id, displayDialogues, projectId, replaceSlideDialoguesInState, runAction]);

  const handleUpdateDialogue = useCallback(
    async (dialogue: Dialogue) => {
      if (!projectId || !currentSlide?.id) return false;
      const actionKey = `dialogue-update:${dialogue.id}`;
      const result = await runAction(actionKey, async () => {
        const updatedDialogue = await updateDialogue(projectId, currentSlide.id, dialogue);
        replaceSlideDialoguesInState(
          currentSlide.id,
          upsertDialogue(displayDialogues, updatedDialogue)
        );
        return updatedDialogue;
      });
      return Boolean(result);
    },
    [currentSlide?.id, displayDialogues, projectId, replaceSlideDialoguesInState, runAction]
  );

  const handleDeleteDialogue = useCallback(
    async (dialogueId: string) => {
      if (!projectId || !currentSlide?.id) return false;
      const previousDialogues = displayDialogues;
      replaceSlideDialoguesInState(
        currentSlide.id,
        removeDialogueById(previousDialogues, dialogueId)
      );

      const actionKey = `dialogue-delete:${dialogueId}`;
      const result = await runAction(actionKey, async () => {
        await deleteDialogue(projectId, currentSlide.id, dialogueId);
        return true;
      });

      if (!result) {
        replaceSlideDialoguesInState(currentSlide.id, previousDialogues);
        return false;
      }

      return true;
    },
    [currentSlide?.id, displayDialogues, projectId, replaceSlideDialoguesInState, runAction]
  );

  const handleMoveDialogue = useCallback(
    async (dialogueId: string, direction: -1 | 1) => {
      if (!projectId || !currentSlide?.id) return false;
      const previousDialogues = displayDialogues;
      const reorderedDialogues = reorderDialoguesLocally(previousDialogues, dialogueId, direction);
      if (reorderedDialogues === previousDialogues) {
        return false;
      }

      replaceSlideDialoguesInState(currentSlide.id, reorderedDialogues);

      const actionKey = `dialogue-reorder:${currentSlide.id}`;
      const result = await runAction(actionKey, async () => {
        await reorderDialogues(
          projectId,
          currentSlide.id,
          reorderedDialogues.map(dialogue => dialogue.id)
        );
        return true;
      });

      if (!result) {
        replaceSlideDialoguesInState(currentSlide.id, previousDialogues);
        return false;
      }

      return true;
    },
    [currentSlide?.id, displayDialogues, projectId, replaceSlideDialoguesInState, runAction]
  );

  const handleGenerateImage = useCallback(async () => {
    if (!projectId || !currentSlide?.id) return;
    const actionKey = `generate-image:${currentSlide.id}`;
    await runAction(actionKey, async () => {
      await generateSlideImage(projectId, currentSlide.id);
      await refreshProject({ force: true });
      return true;
    });
  }, [currentSlide?.id, projectId, refreshProject, runAction]);

  const handleModifyImage = useCallback(
    async (prompt: string) => {
      if (!projectId || !currentSlide?.id) return false;
      const actionKey = `modify-image:${currentSlide.id}`;
      const result = await runAction(actionKey, async () => {
        await modifySlideImage(projectId, currentSlide.id, prompt);
        await refreshProject({ force: true });
        return true;
      });
      return Boolean(result);
    },
    [currentSlide?.id, projectId, refreshProject, runAction]
  );

  const handleGenerateAudio = useCallback(async () => {
    if (!projectId || !currentSlide?.id) return;
    const actionKey = `generate-audio:${currentSlide.id}`;
    await runAction(actionKey, async () => {
      await generateSlideAudio(projectId, currentSlide.id);
      await refreshProject({ force: true });
      return true;
    });
  }, [currentSlide?.id, projectId, refreshProject, runAction]);

  const handleDownloadVideo = useCallback(async () => {
    if (!projectId) return;

    try {
      const { blob, filename } = await downloadVideoFile(projectId);
      const objectUrl = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(objectUrl);
    } catch (error) {
      console.error('Failed to download video:', error);
    }
  }, [projectId]);

  const handleForceRefresh = useCallback(async () => {
    if (!projectId || isRefreshing) {
      return;
    }

    setIsRefreshing(true);
    setIsLoading(true);

    try {
      await refreshProject({ force: true, includeCurrentSlideDialogues: true });
    } catch (error) {
      console.error('Failed to force refresh preview:', error);
    } finally {
      setIsRefreshing(false);
      setIsLoading(false);
    }
  }, [isRefreshing, projectId, refreshProject]);

  const overallGenerationProgress = useMemo(
    () => getGenerationOverallProgress(generationSession),
    [generationSession]
  );

  return {
    plan,
    projectId,
    currentSlideIndex,
    setCurrentSlideIndex,
    isLoading,
    isRefreshing,
    isGeneratingAll: isGenerationSessionActive(generationSession),
    isDialogueActionPending: activeActionKey?.startsWith('dialogue-') ?? false,
    generationSession,
    overallGenerationProgress,
    currentSlide,
    displayDialogues,
    currentSlideImageUrl: slideImageUrl,
    currentSlideAudioUrl: slideAudioUrl,
    projectVideoPath,
    isGeneratingImage: activeActionKey === `generate-image:${currentSlide?.id ?? ''}`,
    isModifyingImage: activeActionKey === `modify-image:${currentSlide?.id ?? ''}`,
    isGeneratingDialogues: activeActionKey === `generate-dialogues:${currentSlide?.id ?? ''}`,
    isGeneratingAudio: activeActionKey === `generate-audio:${currentSlide?.id ?? ''}`,
    handleGenerateDialogues,
    handleGenerateAll,
    handleStartStageGeneration,
    handleStopGeneration,
    handleForceRefresh,
    handleAddDialogue,
    handleUpdateDialogue,
    handleDeleteDialogue,
    handleMoveDialogue,
    handleGenerateImage,
    handleModifyImage,
    handleGenerateAudio,
    handleDownloadVideo,
  };
}
