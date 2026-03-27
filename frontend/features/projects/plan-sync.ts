import type { Slide } from '@/features/projects/types';
import { addSlide, deleteSlide, reorderSlides, updateSlide } from '@/features/projects/api';

export function slideChanged(previous: Slide, next: Slide) {
  return (
    previous.type !== next.type ||
    previous.title !== next.title ||
    previous.description !== next.description ||
    (previous.content ?? '') !== (next.content ?? '') ||
    (previous.imagePath ?? '') !== (next.imagePath ?? '') ||
    (previous.audioPath ?? '') !== (next.audioPath ?? '')
  );
}

export async function syncManualPlanChanges(
  projectId: string,
  previousPlan: { slides: Slide[] } | undefined,
  nextPlan: { slides: Slide[] },
) {
  const previousSlides = previousPlan?.slides ?? [];
  const previousById = new Map(previousSlides.map((slide) => [slide.id, slide]));
  const incomingIds = new Set(nextPlan.slides.map((slide) => slide.id));

  for (const previousSlide of previousSlides) {
    if (!incomingIds.has(previousSlide.id)) {
      await deleteSlide(projectId, previousSlide.id);
    }
  }

  const resolvedSlides: Slide[] = [];

  for (const slide of nextPlan.slides) {
    const existing = previousById.get(slide.id);
    if (existing) {
      if (slideChanged(existing, slide)) {
        resolvedSlides.push(await updateSlide(projectId, slide.id, slide));
      } else {
        resolvedSlides.push(slide);
      }
      continue;
    }

    resolvedSlides.push(await addSlide(projectId, slide));
  }

  if (resolvedSlides.length > 0) {
    await reorderSlides(
      projectId,
      resolvedSlides.map((slide) => slide.id),
    );
  }

  return { slides: resolvedSlides };
}
