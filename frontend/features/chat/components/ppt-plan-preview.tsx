'use client';

import type { Slide } from '@/features/projects/types';
import PPTPlanModal from './ppt-plan-modal';

interface PPTPlanPreviewProps {
  pptPlan: { slides: Slide[] } | undefined;
  onUpdateSlide: (slide: Slide) => Promise<Slide | null>;
  onAddSlide: (slide: Slide) => Promise<Slide | null>;
  onDeleteSlide: (slideId: string) => Promise<boolean>;
  onReorderSlides: (slideIds: string[]) => Promise<boolean>;
  onSaveAndPreview?: () => void | Promise<void>;
}

export default function PPTPlanPreview({
  pptPlan,
  onUpdateSlide,
  onAddSlide,
  onDeleteSlide,
  onReorderSlides,
  onSaveAndPreview,
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
        onClose={() => {}}
        embedded={true}
      />
    </div>
  );
}
