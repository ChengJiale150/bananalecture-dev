const PREVIEW_REFRESH_PREFIX = 'preview:refresh:';

function canUseSessionStorage() {
  return typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined';
}

function getRefreshStorageKey(projectId: string) {
  return `${PREVIEW_REFRESH_PREFIX}${projectId}`;
}

export function markPreviewRefresh(projectId: string) {
  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.setItem(getRefreshStorageKey(projectId), '1');
}

export function consumePreviewRefresh(projectId: string) {
  if (!canUseSessionStorage()) {
    return false;
  }

  const storageKey = getRefreshStorageKey(projectId);
  const hasRefreshSignal = window.sessionStorage.getItem(storageKey) !== null;
  if (hasRefreshSignal) {
    window.sessionStorage.removeItem(storageKey);
  }

  return hasRefreshSignal;
}
