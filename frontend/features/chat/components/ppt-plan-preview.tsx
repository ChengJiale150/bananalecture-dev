'use client';

import { memo } from 'react';
import dynamic from 'next/dynamic';
import type { Slide } from '@/features/projects/types';

const PPTPlanModal = dynamic(() => import('./ppt-plan-modal'));
interface PPTPlanPreviewProps {
  pptPlan: { slides: Slide[] } | undefined;
  onUpdateSlide: (slide: Slide) => Promise<Slide | null>;
  onAddSlide: (slide: Slide) => Promise<Slide | null>;
  onDeleteSlide: (slideId: string) => Promise<boolean>;
  onReorderSlides: (slideIds: string[]) => Promise<boolean>;
  onSaveAndPreview?: () => void | Promise<void>;
  canCompleteEdit?: boolean;
  isCompletingEdit?: boolean;
  isChatActive?: boolean;
  isPlanPendingSync?: boolean;
}

function PPTPlanPreview({
  pptPlan,
  onUpdateSlide,
  onAddSlide,
  onDeleteSlide,
  onReorderSlides,
  onSaveAndPreview,
  canCompleteEdit = true,
  isCompletingEdit = false,
  isChatActive = false,
  isPlanPendingSync = false,
}: PPTPlanPreviewProps) {
  if (!pptPlan || pptPlan.slides.length === 0) {
    return (
      <div className="h-full">
        <div className="flex h-full items-center justify-center rounded-2xl border-2 border-dashed border-gray-300 bg-white/80 p-8 text-center">
          <div>
            <h3 className="text-lg font-bold text-gray-900">PPT 规划编辑器</h3>
            <p className="mt-2 text-sm text-gray-500">生成规划后可在这里直接编辑页面内容。</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full">
      <PPTPlanModal
        pptPlan={pptPlan}
        onUpdateSlide={onUpdateSlide}
        onAddSlide={onAddSlide}
        onDeleteSlide={onDeleteSlide}
        onReorderSlides={onReorderSlides}
        onSaveAndPreview={onSaveAndPreview}
        canCompleteEdit={canCompleteEdit}
        isCompletingEdit={isCompletingEdit}
        isChatActive={isChatActive}
        isPlanPendingSync={isPlanPendingSync}
        onClose={() => {}}
        embedded={true}
      />
    </div>
  );
}

/**
 * Memoized because the chat panel re-renders on every streamed chunk, while the plan only
 * changes when the planner actually produces new slides.
 */
export default memo(PPTPlanPreview);
