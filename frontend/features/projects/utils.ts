export const DEFAULT_PROJECT_LIST_PAGE = 1;
export const DEFAULT_PROJECT_LIST_PAGE_SIZE = 10;

export function safeParseProjectMessages(messages: string | null | undefined) {
  if (!messages) return [];

  try {
    const parsed = JSON.parse(messages);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function stringifyProjectMessages(messages: unknown[]) {
  return JSON.stringify(messages);
}

export function normalizePageValue(value: number | string | null | undefined, fallback = 1) {
  const page = typeof value === 'string' ? Number.parseInt(value, 10) : value;
  if (!page || !Number.isFinite(page) || page < 1) {
    return fallback;
  }

  return Math.floor(page);
}

export function clampPage(page: number, totalPages: number) {
  const normalizedTotal = Math.max(1, Math.floor(totalPages) || 1);
  return Math.min(Math.max(1, Math.floor(page) || 1), normalizedTotal);
}

export function getVisiblePaginationPages(currentPage: number, totalPages: number, siblingCount = 1) {
  const safeTotalPages = Math.max(1, totalPages);
  const safeCurrentPage = clampPage(currentPage, safeTotalPages);
  const start = Math.max(1, safeCurrentPage - siblingCount);
  const end = Math.min(safeTotalPages, safeCurrentPage + siblingCount);
  const pages = new Set<number>([1, safeTotalPages]);

  for (let page = start; page <= end; page += 1) {
    pages.add(page);
  }

  return [...pages].sort((left, right) => left - right);
}

export function getSlideIndexFromPageParam(page: number | string | null | undefined, totalSlides: number) {
  if (totalSlides <= 0) return 0;
  return clampPage(normalizePageValue(page, 1), totalSlides) - 1;
}

export function getPageParamFromSlideIndex(index: number) {
  return Math.max(1, Math.floor(index) + 1);
}
