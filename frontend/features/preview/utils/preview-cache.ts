import type { Dialogue, ProjectRecord } from '@/features/projects/types';

const PROJECT_CACHE_PREFIX = 'preview:project:';
const DIALOGUES_CACHE_PREFIX = 'preview:dialogues:';

const projectMemoryCache = new Map<string, ProjectRecord>();
const dialogueMemoryCache = new Map<string, Dialogue[]>();

function canUseSessionStorage() {
  return typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined';
}

function getProjectStorageKey(projectId: string) {
  return `${PROJECT_CACHE_PREFIX}${projectId}`;
}

function getDialoguesStorageKey(projectId: string, slideId: string) {
  return `${DIALOGUES_CACHE_PREFIX}${projectId}:${slideId}`;
}

function getDialogueStoragePrefix(projectId: string) {
  return `${DIALOGUES_CACHE_PREFIX}${projectId}:`;
}

export function readCachedProject(projectId: string) {
  const memoryValue = projectMemoryCache.get(projectId);
  if (memoryValue) {
    return memoryValue;
  }

  if (!canUseSessionStorage()) {
    return null;
  }

  const raw = window.sessionStorage.getItem(getProjectStorageKey(projectId));
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as ProjectRecord;
    projectMemoryCache.set(projectId, parsed);
    return parsed;
  } catch {
    window.sessionStorage.removeItem(getProjectStorageKey(projectId));
    return null;
  }
}

export function writeCachedProject(project: ProjectRecord) {
  projectMemoryCache.set(project.id, project);

  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.setItem(getProjectStorageKey(project.id), JSON.stringify(project));
}

export function updateCachedProject(
  projectId: string,
  updater: (project: ProjectRecord) => ProjectRecord,
) {
  const current = readCachedProject(projectId);
  if (!current) {
    return null;
  }

  const next = updater(current);
  writeCachedProject(next);
  return next;
}

export function clearCachedProject(projectId: string) {
  projectMemoryCache.delete(projectId);

  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.removeItem(getProjectStorageKey(projectId));
}

export function readCachedDialogues(projectId: string, slideId: string) {
  const cacheKey = `${projectId}:${slideId}`;
  const memoryValue = dialogueMemoryCache.get(cacheKey);
  if (memoryValue) {
    return memoryValue;
  }

  if (!canUseSessionStorage()) {
    return null;
  }

  const raw = window.sessionStorage.getItem(getDialoguesStorageKey(projectId, slideId));
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as Dialogue[];
    dialogueMemoryCache.set(cacheKey, parsed);
    return parsed;
  } catch {
    window.sessionStorage.removeItem(getDialoguesStorageKey(projectId, slideId));
    return null;
  }
}

export function writeCachedDialogues(projectId: string, slideId: string, dialogues: Dialogue[]) {
  const cacheKey = `${projectId}:${slideId}`;
  dialogueMemoryCache.set(cacheKey, dialogues);

  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.setItem(getDialoguesStorageKey(projectId, slideId), JSON.stringify(dialogues));
}

export function clearCachedDialogues(projectId: string, slideId: string) {
  const cacheKey = `${projectId}:${slideId}`;
  dialogueMemoryCache.delete(cacheKey);

  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.removeItem(getDialoguesStorageKey(projectId, slideId));
}

export function clearProjectPreviewCache(projectId: string) {
  clearCachedProject(projectId);

  for (const cacheKey of dialogueMemoryCache.keys()) {
    if (cacheKey.startsWith(`${projectId}:`)) {
      dialogueMemoryCache.delete(cacheKey);
    }
  }

  if (!canUseSessionStorage()) {
    return;
  }

  const prefix = getDialogueStoragePrefix(projectId);
  const keysToDelete: string[] = [];
  for (let index = 0; index < window.sessionStorage.length; index += 1) {
    const key = window.sessionStorage.key(index);
    if (key?.startsWith(prefix)) {
      keysToDelete.push(key);
    }
  }

  keysToDelete.forEach((key) => window.sessionStorage.removeItem(key));
}
