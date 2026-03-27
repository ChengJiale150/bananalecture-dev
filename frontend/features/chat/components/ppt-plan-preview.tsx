'use client';

import { Sparkles, Maximize2, ChevronRight } from 'lucide-react';
import { useState, useMemo } from 'react';
import type { Slide, SlideType } from '@/features/projects/types';
import dynamic from 'next/dynamic';

// Lazy load the modal for better initial load performance
const PPTPlanModal = dynamic(() => import('./ppt-plan-modal'), {
  loading: () => (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white p-6 rounded-xl border-2 border-gray-900 animate-pulse">
        加载编辑器...
      </div>
    </div>
  ),
});

interface PPTPlanPreviewProps {
  pptPlan: { slides: Slide[] } | undefined;
  onUpdateSlide: (slide: Slide) => Promise<Slide | null>;
  onAddSlide: (slide: Slide) => Promise<Slide | null>;
  onDeleteSlide: (slideId: string) => Promise<boolean>;
  onReorderSlides: (slideIds: string[]) => Promise<boolean>;
}

export default function PPTPlanPreview({
  pptPlan,
  onUpdateSlide,
  onAddSlide,
  onDeleteSlide,
  onReorderSlides,
}: PPTPlanPreviewProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const slides = pptPlan?.slides || [];

  // Use useMemo for dots to avoid unnecessary recalculations
  const slideDots = useMemo(() => {
    if (!slides.length) return null;
    return (
      <div className="flex items-center gap-1 ml-4 flex-shrink-0">
        {slides.slice(0, 8).map((slide, index) => (
          <div
            key={index}
            className={`w-2 h-2 rounded-full ${getSlideDotColor(slide.type)}`}
            title={getSlideTypeLabel(slide.type)}
          />
        ))}
        {slides.length > 8 && <div className="text-xs text-gray-400">+{slides.length - 8}</div>}
      </div>
    );
  }, [slides]);

  if (!pptPlan || slides.length === 0) {
    return null;
  }

  return (
    <>
      <div className="w-full bg-[#F0F8FF] border-t-2 border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-3">
          <button
            onClick={() => setIsModalOpen(true)}
            className="w-full flex items-center justify-between p-3 bg-white border-2 border-[var(--doraemon-blue)] rounded-xl shadow-[3px_3px_0px_var(--doraemon-blue)] hover:shadow-[4px_4px_0px_var(--doraemon-blue)] hover:translate-x-[-1px] hover:translate-y-[-1px] transition-all"
          >
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 bg-[var(--doraemon-yellow)] rounded-full border-2 border-gray-900">
                <Sparkles size={20} className="text-gray-900" />
              </div>
              <div className="text-left flex-1 min-w-0">
                <div className="font-bold text-gray-900">PPT 规划</div>
                <div className="text-xs text-gray-500 truncate">
                  {slides
                    .slice(0, 3)
                    .map(s => s.title)
                    .join(' → ')}
                  {slides.length > 3 ? ' ...' : ''}
                </div>
              </div>
              {slideDots}
            </div>
            <div className="flex items-center gap-2 text-[var(--doraemon-blue)]">
              <Maximize2 size={18} />
              <ChevronRight size={18} />
            </div>
          </button>
        </div>
      </div>

      {isModalOpen && (
        <PPTPlanModal
          pptPlan={pptPlan}
          onUpdateSlide={onUpdateSlide}
          onAddSlide={onAddSlide}
          onDeleteSlide={onDeleteSlide}
          onReorderSlides={onReorderSlides}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </>
  );
}

function getSlideDotColor(type: SlideType) {
  switch (type) {
    case 'cover':
      return 'bg-[var(--doraemon-yellow)]';
    case 'introduction':
      return 'bg-[var(--doraemon-blue)]';
    case 'content':
      return 'bg-yellow-400';
    case 'summary':
      return 'bg-green-500';
    case 'ending':
      return 'bg-pink-500';
    default:
      return 'bg-gray-400';
  }
}

function getSlideTypeLabel(type: SlideType) {
  switch (type) {
    case 'cover':
      return '封面页';
    case 'introduction':
      return '引入页';
    case 'content':
      return '正文页';
    case 'summary':
      return '总结页';
    case 'ending':
      return '结束页';
    default:
      return type;
  }
}
