interface CachedImage {
  blob: Blob;
  objectUrl: string;
}

const imageCache = new Map<string, CachedImage>();

function getCacheKey(projectId: string, slideId: string): string {
  return `image:${projectId}:${slideId}`;
}

export function getCachedImage(projectId: string, slideId: string): CachedImage | null {
  const key = getCacheKey(projectId, slideId);
  return imageCache.get(key) ?? null;
}

export function cacheImage(projectId: string, slideId: string, blob: Blob): string {
  const key = getCacheKey(projectId, slideId);
  const existing = imageCache.get(key);
  if (existing) {
    URL.revokeObjectURL(existing.objectUrl);
  }

  const objectUrl = URL.createObjectURL(blob);
  imageCache.set(key, { blob, objectUrl });
  return objectUrl;
}

export function clearImageCache(projectId: string): void {
  const prefix = `image:${projectId}:`;
  for (const [key, cached] of imageCache.entries()) {
    if (key.startsWith(prefix)) {
      URL.revokeObjectURL(cached.objectUrl);
      imageCache.delete(key);
    }
  }
}

export function clearAllImageCache(): void {
  for (const cached of imageCache.values()) {
    URL.revokeObjectURL(cached.objectUrl);
  }
  imageCache.clear();
}

export function hasCachedImage(projectId: string, slideId: string): boolean {
  const key = getCacheKey(projectId, slideId);
  return imageCache.has(key);
}

export function revokeObjectUrl(url: string): void {
  URL.revokeObjectURL(url);
}

export function getCacheSize(): number {
  return imageCache.size;
}
