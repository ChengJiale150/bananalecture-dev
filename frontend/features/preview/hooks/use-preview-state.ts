import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import type {
  Dialogue,
  GenerationSessionMode,
  GenerationSessionState,
  GenerationStage,
  GenerationStageStatus,
  PPTPlan,
  TaskProgress,
} from '@/features/projects/types';
import { GENERATION_STAGES } from '@/features/projects/types';
import {
  addDialogue,
  batchGenerateAudio,
  batchGenerateDialogues,
  batchGenerateImages,
  cancelGeneration,
  deleteDialogue,
  downloadVideoFile,
  fetchSlideImageBlob,
  generateDialogues,
  generateSlideAudio,
  generateSlideImage,
  generateVideo,
  getGenerationStatus,
  getProject,
  getSlideAudioUrl,
  getTask,
  listDialogues,
  mapGenerationSession,
  modifySlideImage,
  pauseGeneration,
  reorderDialogues,
  resumeGeneration,
  startGeneration,
  updateDialogue,
} from '@/features/projects/api';
import { cacheImage, getCachedImage } from '@/features/preview/utils/image-cache';
import { getPageParamFromSlideIndex, getSlideIndexFromPageParam } from '@/features/projects/utils';
import {
  getEstimatedRemainingSeconds,
  getGenerationOverallProgress,
  isGenerationSessionActive,
  isGenerationSessionResumable,
} from '@/features/preview/utils/generation-session';
import {
  buildPreviewQueryString,
  clearProjectPreviewCache,
  consumePreviewRefresh,
  getCurrentSlideImageUrl,
  normalizeDialogues,
  readCachedDialogues,
  readCachedProject,
  removeDialogueById,
  reorderDialoguesLocally,
  type SlideImageState,
  upsertDialogue,
  updateCachedProject,
  writeCachedDialogues,
  writeCachedProject,
} from '../utils';

const POLL_INTERVAL_MS = 2000;

export function usePreviewState(
  projectIdFromUrl: string | null,
  pageFromUrl: string | null,
  legacyRefreshToken: string | null
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
  const [slideImageState, setSlideImageState] = useState<SlideImageState | null>(null);
  const [slideImageReloadToken, setSlideImageReloadToken] = useState(0);
  const generationSessionRef = useRef<GenerationSessionState | null>(null);
  const initialRefreshProjectRef = useRef<string | null>(null);

  useEffect(() => {
    generationSessionRef.current = generationSession;
  }, [generationSession]);

  const setCurrentSlideIndex = useCallback(
    (nextIndex: number) => {
      const nextPage = getPageParamFromSlideIndex(nextIndex);
      const nextQuery = buildPreviewQueryString(searchParams, {
        page: nextPage,
        removeRefresh: true,
      });
      router.replace(`${pathname}?${nextQuery}`, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const commitGenerationSession = useCallback(
    (nextSession: GenerationSessionState | null) => {
      generationSessionRef.current = nextSession;
      setGenerationSession(nextSession);
    },
    []
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
        setSlideImageState(null);
        setSlideImageReloadToken(current => current + 1);
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
    ) => {
      if (!projectId) return;

      const startTask = {
        images: batchGenerateImages,
        dialogues: batchGenerateDialogues,
        audio: batchGenerateAudio,
        video: generateVideo,
      }[stage];

      const taskId = await startTask(projectId);
      const task = await getTask(taskId);

      const stages = GENERATION_STAGES.map(s => ({
        stage: s,
        label: s,
        status: (s === stage ? 'running' : 'pending') as GenerationStageStatus,
        progress: 0,
        taskId: s === stage ? task.id : undefined,
      }));

      commitGenerationSession({
        mode,
        projectId,
        status: 'running',
        currentStage: stage,
        stages,
        activeTask: task,
        errorMessage: null,
        updatedAt: Date.now(),
      });
    },
    [commitGenerationSession, projectId]
  );

  useEffect(() => {
    if (!legacyRefreshToken) {
      return;
    }

    const nextQuery = buildPreviewQueryString(searchParams, { removeRefresh: true });
    router.replace(`${pathname}?${nextQuery}`, { scroll: false });
  }, [legacyRefreshToken, pathname, router, searchParams]);

  useEffect(() => {
    const loadPlan = async () => {
      try {
        if (!projectIdFromUrl) {
          setProjectId('');
          setPlan(null);
          setProjectVideoPath(undefined);
          setSlideImageState(null);
          commitGenerationSession(null);
          initialRefreshProjectRef.current = null;
          return;
        }

        setProjectId(projectIdFromUrl);
        const shouldConsumeInitialRefresh = initialRefreshProjectRef.current !== projectIdFromUrl;
        const shouldForceRefresh =
          (shouldConsumeInitialRefresh && Boolean(legacyRefreshToken)) ||
          (shouldConsumeInitialRefresh && consumePreviewRefresh(projectIdFromUrl));
        if (shouldForceRefresh) {
          clearProjectPreviewCache(projectIdFromUrl);
          setSlideImageState(null);
          setSlideImageReloadToken(current => current + 1);
        }
        if (shouldConsumeInitialRefresh) {
          initialRefreshProjectRef.current = projectIdFromUrl;
        }

        const cachedProject = !shouldForceRefresh ? readCachedProject(projectIdFromUrl) : null;
        const project = cachedProject ?? (await getProject(projectIdFromUrl));
        applyProjectToState(project);
        setCurrentSlideIndexState(
          getSlideIndexFromPageParam(pageFromUrl, project.pptPlan?.slides.length ?? 0)
        );
        try {
          const genStatus = await getGenerationStatus(projectIdFromUrl);
          commitGenerationSession(mapGenerationSession(genStatus));
        } catch {
          commitGenerationSession(null);
        }
      } catch (error) {
        console.error('Failed to load preview plan:', error);
        setPlan(null);
        setProjectVideoPath(undefined);
      } finally {
        setIsLoading(false);
      }
    };

    void loadPlan();
  }, [applyProjectToState, commitGenerationSession, legacyRefreshToken, pageFromUrl, projectIdFromUrl]);

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

    const nextQuery = buildPreviewQueryString(searchParams, {
      page: nextPage,
      removeRefresh: true,
    });
    router.replace(`${pathname}?${nextQuery}`, { scroll: false });
  }, [pageFromUrl, pathname, plan, router, searchParams]);

  useEffect(() => {
    if (!projectId) return;

    getGenerationStatus(projectId)
      .then(status => {
        if (status) {
          commitGenerationSession(mapGenerationSession(status));
        }
      })
      .catch(() => {
        // No active session — that's fine
      });
  }, [projectId, commitGenerationSession]);

  useEffect(() => {
    if (!generationSession || !projectId) return;
    if (generationSession.status !== 'running') return;

    let cancelled = false;
    let intervalId = 0;

    const pollPipeline = async () => {
      try {
        const status = await getGenerationStatus(projectId);
        if (cancelled) return;

        const nextSession = mapGenerationSession(status);
        commitGenerationSession(nextSession);

        if (nextSession.status !== 'running') {
          window.clearInterval(intervalId);
          await refreshProject({ force: true });
        }
      } catch (error) {
        console.error('Failed to poll pipeline:', error);
        window.clearInterval(intervalId);
      }
    };

    void pollPipeline();
    intervalId = window.setInterval(pollPipeline, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [generationSession?.status, projectId, commitGenerationSession, refreshProject]);

  const currentSlide = plan?.slides[currentSlideIndex];
  const [slideAudioTimestamp, setSlideAudioTimestamp] = useState(Date.now());

  useEffect(() => {
    if (!projectId || !currentSlide?.id || !currentSlide.imagePath) {
      setSlideImageState(null);
      return;
    }

    let cancelled = false;
    const targetSlideId = currentSlide.id;
    const loadImage = async () => {
      const cached = getCachedImage(projectId, targetSlideId);
      if (cached) {
        if (!cancelled) {
          setSlideImageState({ slideId: targetSlideId, url: cached.objectUrl });
        }
        return;
      }

      try {
        const blob = await fetchSlideImageBlob(projectId, targetSlideId);
        if (cancelled) return;
        const objectUrl = cacheImage(projectId, targetSlideId, blob);
        if (!cancelled) {
          setSlideImageState({ slideId: targetSlideId, url: objectUrl });
        }
      } catch (error) {
        console.error('Failed to fetch slide image:', error);
        if (!cancelled) {
          setSlideImageState(current => (current?.slideId === targetSlideId ? null : current));
        }
      }
    };

    void loadImage();
    return () => {
      cancelled = true;
    };
  }, [currentSlide?.id, currentSlide?.imagePath, projectId, slideImageReloadToken]);

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
  const slideImageUrl = getCurrentSlideImageUrl(slideImageState, currentSlide?.id);
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

    try {
      await startGeneration(projectId);
      const status = await getGenerationStatus(projectId);
      commitGenerationSession(mapGenerationSession(status));
    } catch (error) {
      console.error('Failed to start generation:', error);
    }
  }, [projectId, commitGenerationSession]);

  const handlePauseGeneration = useCallback(async () => {
    if (!projectId) return;

    try {
      const status = await pauseGeneration(projectId);
      commitGenerationSession(mapGenerationSession(status));
    } catch (error) {
      console.error('Failed to pause generation:', error);
    }
  }, [projectId, commitGenerationSession]);

  const handleResumeGeneration = useCallback(async () => {
    if (!projectId) return;

    try {
      const status = await resumeGeneration(projectId);
      commitGenerationSession(mapGenerationSession(status));
    } catch (error) {
      console.error('Failed to resume generation:', error);
    }
  }, [projectId, commitGenerationSession]);

  const handleStopGeneration = useCallback(async () => {
    if (!projectId) return;

    try {
      const status = await cancelGeneration(projectId);
      commitGenerationSession(mapGenerationSession(status));
    } catch (error) {
      console.error('Failed to cancel generation:', error);
    }
  }, [projectId, commitGenerationSession]);

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

  const estimatedRemainingSeconds = useMemo(
    () => getEstimatedRemainingSeconds(generationSession, generationSession?.activeTask ?? null),
    [generationSession]
  );

  const genSession = generationSession;
  return {
    plan,
    projectId,
    currentSlideIndex,
    setCurrentSlideIndex,
    isLoading,
    isRefreshing,
    isGeneratingAll: isGenerationSessionActive(genSession),
    isPaused: genSession?.status === 'paused',
    isResumable: isGenerationSessionResumable(genSession),
    isDialogueActionPending: activeActionKey?.startsWith('dialogue-') ?? false,
    generationSession: genSession,
    overallGenerationProgress,
    estimatedRemainingSeconds,
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
    handlePauseGeneration,
    handleResumeGeneration,
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
