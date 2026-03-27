import type { PPTPlan, Slide, SlideType } from '@/features/projects/types';

type ToolPartLike = {
  type?: string;
  state?: string;
  toolCallId?: string;
  args?: { slides?: unknown };
  output?: { slides?: unknown };
  toolInvocation?: {
    state?: string;
    toolCallId?: string;
    toolCallID?: string;
    args?: { slides?: unknown };
    input?: { slides?: unknown };
    output?: { slides?: unknown };
  };
  input?: { slides?: unknown };
};

export interface ExtractedPptPlanState {
  hasDraft: boolean;
  draftSlides: Slide[];
  hasCompleted: boolean;
  completedSlides: Slide[];
  completedToolCallId: string | null;
}

function toSlideType(type: unknown): SlideType {
  return typeof type === 'string' && type ? (type as SlideType) : 'content';
}

function normalizeToolSlide(input: unknown): Slide | null {
  if (!input || typeof input !== 'object') {
    return null;
  }

  const slide = input as Record<string, unknown>;
  return {
    id: typeof slide.id === 'string' ? slide.id : '',
    type: toSlideType(slide.type),
    title: typeof slide.title === 'string' ? slide.title : '',
    description: typeof slide.description === 'string' ? slide.description : '',
    content: typeof slide.content === 'string' ? slide.content : '',
  };
}

function normalizeToolSlides(input: unknown): Slide[] | null {
  if (!Array.isArray(input)) {
    return null;
  }

  return input.map(normalizeToolSlide).filter((slide): slide is Slide => Boolean(slide));
}

function isCompletedToolState(state: string | undefined) {
  return state === 'result' || state === 'output-available';
}

function getToolSlides(part: ToolPartLike): Slide[] | null {
  const outputSlides = normalizeToolSlides(
    part.output?.slides ?? part.toolInvocation?.output?.slides
  );
  if (outputSlides) {
    return outputSlides;
  }

  return normalizeToolSlides(
    part.args?.slides ??
      part.toolInvocation?.args?.slides ??
      part.input?.slides ??
      part.toolInvocation?.input?.slides
  );
}

export function extractLatestPptPlanState(messages: unknown[]): ExtractedPptPlanState {
  let hasDraft = false;
  let draftSlides: Slide[] = [];
  let hasCompleted = false;
  let completedSlides: Slide[] = [];
  let completedToolCallId: string | null = null;

  for (const message of messages) {
    if (!message || typeof message !== 'object') {
      continue;
    }

    const parts = (message as { parts?: unknown }).parts;
    if (!Array.isArray(parts)) {
      continue;
    }

    for (const rawPart of parts) {
      if (!rawPart || typeof rawPart !== 'object') {
        continue;
      }

      const part = rawPart as ToolPartLike;
      if (part.type !== 'tool-create_ppt_plan') {
        continue;
      }

      const slides = getToolSlides(part);
      if (!slides) {
        continue;
      }

      hasDraft = true;
      draftSlides = slides;

      const state = part.state ?? part.toolInvocation?.state;
      if (!isCompletedToolState(state)) {
        continue;
      }

      hasCompleted = true;
      completedSlides = slides;
      completedToolCallId =
        part.toolCallId ??
        part.toolInvocation?.toolCallId ??
        part.toolInvocation?.toolCallID ??
        null;
    }
  }

  return {
    hasDraft,
    draftSlides,
    hasCompleted,
    completedSlides,
    completedToolCallId,
  };
}

export function createPptPlan(slides: Slide[]): PPTPlan | undefined {
  return slides.length > 0 ? { slides } : undefined;
}

export function getPptPlanSignature(slides: Slide[] | undefined) {
  return JSON.stringify(
    (slides ?? []).map(slide => ({
      type: slide.type,
      title: slide.title,
      description: slide.description,
      content: slide.content ?? '',
    }))
  );
}

export function shouldSyncCompletedPptPlan(
  status: string,
  extraction: ExtractedPptPlanState,
  lastSyncedSignature: string
) {
  if (status !== 'ready' || !extraction.hasCompleted) {
    return false;
  }

  return getPptPlanSignature(extraction.completedSlides) !== lastSyncedSignature;
}

export function shouldApplyIncomingPlanToModal(
  editingSlideIndex: number | null,
  isMutating: boolean
) {
  return editingSlideIndex === null && !isMutating;
}
