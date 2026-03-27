'use client';

import {
  X,
  Sparkles,
  BookOpen,
  Lightbulb,
  FileText,
  Star,
  Edit2,
  Save,
  Trash2,
  Plus,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { shouldApplyIncomingPlanToModal } from '@/features/chat/ppt-plan-state';
import type { Slide, SlideType } from '@/features/projects/types';
import { moveSlideDown, moveSlideUp } from '@/features/projects/types';

interface PPTPlanModalProps {
  pptPlan: { slides: Slide[] };
  onUpdateSlide: (slide: Slide) => Promise<Slide | null>;
  onAddSlide: (slide: Slide) => Promise<Slide | null>;
  onDeleteSlide: (slideId: string) => Promise<boolean>;
  onReorderSlides: (slideIds: string[]) => Promise<boolean>;
  onClose: () => void;
}

function createNewSlideDraft(): Slide {
  return {
    id: '',
    type: 'content',
    title: '新页面',
    description: '请输入页面描述',
    content: '',
  };
}

export default function PPTPlanModal({
  pptPlan,
  onUpdateSlide,
  onAddSlide,
  onDeleteSlide,
  onReorderSlides,
  onClose,
}: PPTPlanModalProps) {
  const [slides, setSlides] = useState<Slide[]>(pptPlan.slides);
  const [editingSlideIndex, setEditingSlideIndex] = useState<number | null>(null);
  const [editingSlide, setEditingSlide] = useState<Slide | null>(null);
  const [isMutating, setIsMutating] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!shouldApplyIncomingPlanToModal(editingSlideIndex, isMutating)) {
      return;
    }

    setSlides(pptPlan.slides);
  }, [editingSlideIndex, isMutating, pptPlan.slides]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const getSlideIcon = (type: SlideType) => {
    switch (type) {
      case 'cover':
        return <Sparkles size={20} className="text-[var(--doraemon-yellow)]" />;
      case 'introduction':
        return <BookOpen size={20} className="text-[var(--doraemon-blue)]" />;
      case 'content':
        return <Lightbulb size={20} className="text-yellow-500" />;
      case 'summary':
        return <FileText size={20} className="text-green-500" />;
      case 'ending':
        return <Star size={20} className="text-pink-500" />;
      default:
        return <FileText size={20} />;
    }
  };

  const getSlideTypeLabel = (type: SlideType) => {
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
  };

  const getSlideBorderColor = (type: SlideType) => {
    switch (type) {
      case 'cover':
        return 'border-[var(--doraemon-yellow)]';
      case 'introduction':
        return 'border-[var(--doraemon-blue)]';
      case 'content':
        return 'border-yellow-400';
      case 'summary':
        return 'border-green-400';
      case 'ending':
        return 'border-pink-400';
      default:
        return 'border-gray-300';
    }
  };

  const getSlideShadowColor = (type: SlideType) => {
    switch (type) {
      case 'cover':
        return 'shadow-[4px_4px_0px_var(--doraemon-yellow)]';
      case 'introduction':
        return 'shadow-[4px_4px_0px_var(--doraemon-blue)]';
      case 'content':
        return 'shadow-[4px_4px_0px_rgba(250,204,21,1)]';
      case 'summary':
        return 'shadow-[4px_4px_0px_rgba(74,222,128,1)]';
      case 'ending':
        return 'shadow-[4px_4px_0px_rgba(244,114,182,1)]';
      default:
        return 'shadow-[4px_4px_0px_rgba(0,0,0,1)]';
    }
  };

  const startEditSlide = (index: number) => {
    setEditingSlideIndex(index);
    setEditingSlide({ ...slides[index] });
  };

  const saveEditSlide = async () => {
    if (editingSlideIndex === null || !editingSlide) return;
    setIsMutating(true);
    try {
      const updatedSlide = await onUpdateSlide(editingSlide);
      if (!updatedSlide) return;
      setSlides(prev =>
        prev.map((slide, index) => (index === editingSlideIndex ? updatedSlide : slide))
      );
      setEditingSlideIndex(null);
      setEditingSlide(null);
    } finally {
      setIsMutating(false);
    }
  };

  const handleMoveSlide = async (index: number, direction: -1 | 1) => {
    const nextSlides = direction === -1 ? moveSlideUp(slides, index) : moveSlideDown(slides, index);
    if (nextSlides === slides) return;

    const previousSlides = slides;
    setSlides(nextSlides);
    setIsMutating(true);
    try {
      const success = await onReorderSlides(nextSlides.map(slide => slide.id));
      if (!success) {
        setSlides(previousSlides);
      }
    } finally {
      setIsMutating(false);
    }
  };

  const handleDeleteSlide = async (index: number) => {
    const slide = slides[index];
    if (!slide) return;

    const previousSlides = slides;
    const nextSlides = slides.filter((_, currentIndex) => currentIndex !== index);
    setSlides(nextSlides);
    if (editingSlideIndex === index) {
      setEditingSlideIndex(null);
      setEditingSlide(null);
    }

    setIsMutating(true);
    try {
      const success = await onDeleteSlide(slide.id);
      if (!success) {
        setSlides(previousSlides);
      }
    } finally {
      setIsMutating(false);
    }
  };

  const handleAddSlide = async () => {
    setIsMutating(true);
    try {
      const createdSlide = await onAddSlide(createNewSlideDraft());
      if (!createdSlide) return;
      setSlides(prev => [...prev, createdSlide]);
      setEditingSlideIndex(slides.length);
      setEditingSlide(createdSlide);
    } finally {
      setIsMutating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-[#F0F8FF] rounded-2xl border-4 border-gray-900 shadow-[8px_8px_0px_rgba(0,0,0,1)] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 bg-white border-b-4 border-gray-900">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[var(--doraemon-yellow)] rounded-full border-2 border-gray-900 flex items-center justify-center">
              <Sparkles size={24} className="text-gray-900" />
            </div>
            <div>
              <h2 className="text-xl font-black text-gray-900">PPT 规划编辑器</h2>
              <p className="text-sm text-gray-500">
                {slides.length} 页，流式预览，完成后统一同步到后端
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 bg-[var(--doraemon-red)] text-white rounded-xl border-2 border-gray-900 hover:brightness-110 active:scale-95 transition-all shadow-[2px_2px_0px_rgba(0,0,0,1)]"
          >
            <X size={24} />
          </button>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6">
          <div className="space-y-4">
            {slides.map((slide, index) => (
              <div
                key={slide.id || index}
                className={`p-4 bg-white border-2 rounded-xl ${getSlideBorderColor(slide.type)} ${getSlideShadowColor(slide.type)}`}
              >
                {editingSlideIndex === index ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="flex items-center justify-center w-8 h-8 bg-gray-100 rounded-full font-bold text-gray-700">
                          {index + 1}
                        </div>
                        <select
                          value={editingSlide?.type}
                          onChange={e =>
                            setEditingSlide({ ...editingSlide!, type: e.target.value as SlideType })
                          }
                          className="border-2 border-gray-300 rounded-lg px-2 py-1 text-sm font-medium"
                        >
                          <option value="cover">封面页</option>
                          <option value="introduction">引入页</option>
                          <option value="content">正文页</option>
                          <option value="summary">总结页</option>
                          <option value="ending">结束页</option>
                        </select>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => void saveEditSlide()}
                          disabled={isMutating || !editingSlide?.title.trim()}
                          className="p-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors border-2 border-green-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <Save size={16} />
                        </button>
                        <button
                          onClick={() => {
                            setEditingSlideIndex(null);
                            setEditingSlide(null);
                          }}
                          disabled={isMutating}
                          className="p-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors border-2 border-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    </div>
                    <input
                      type="text"
                      value={editingSlide?.title || ''}
                      onChange={e => setEditingSlide({ ...editingSlide!, title: e.target.value })}
                      className="w-full border-2 border-gray-300 rounded-lg px-3 py-2 font-bold"
                      placeholder="标题"
                    />
                    <textarea
                      value={editingSlide?.description || ''}
                      onChange={e =>
                        setEditingSlide({ ...editingSlide!, description: e.target.value })
                      }
                      className="w-full border-2 border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
                      rows={2}
                      placeholder="描述"
                    />
                    <textarea
                      value={editingSlide?.content || ''}
                      onChange={e => setEditingSlide({ ...editingSlide!, content: e.target.value })}
                      className="w-full border-2 border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
                      rows={6}
                      placeholder="详细内容 (支持 Markdown)"
                    />
                  </div>
                ) : (
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-8 h-8 bg-gray-100 rounded-full font-bold text-gray-700">
                          {index + 1}
                        </div>
                        <div className="flex items-center gap-2">
                          {getSlideIcon(slide.type)}
                          <span className="font-bold text-gray-700">
                            {getSlideTypeLabel(slide.type)}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => void handleMoveSlide(index, -1)}
                          disabled={index === 0 || editingSlideIndex !== null || isMutating}
                          className={`p-2 rounded-lg transition-colors ${index === 0 || editingSlideIndex !== null || isMutating ? 'text-gray-300 cursor-not-allowed' : 'hover:bg-gray-100 text-gray-600'}`}
                          title="上移"
                        >
                          <ChevronUp size={16} />
                        </button>
                        <button
                          onClick={() => void handleMoveSlide(index, 1)}
                          disabled={
                            index === slides.length - 1 || editingSlideIndex !== null || isMutating
                          }
                          className={`p-2 rounded-lg transition-colors ${index === slides.length - 1 || editingSlideIndex !== null || isMutating ? 'text-gray-300 cursor-not-allowed' : 'hover:bg-gray-100 text-gray-600'}`}
                          title="下移"
                        >
                          <ChevronDown size={16} />
                        </button>
                        <button
                          onClick={() => startEditSlide(index)}
                          disabled={isMutating}
                          className="p-2 hover:bg-gray-100 rounded-lg transition-colors disabled:text-gray-300 disabled:cursor-not-allowed"
                          title="编辑"
                        >
                          <Edit2 size={16} className="text-gray-600" />
                        </button>
                        <button
                          onClick={() => void handleDeleteSlide(index)}
                          disabled={isMutating}
                          className="p-2 hover:bg-red-100 rounded-lg transition-colors disabled:text-gray-300 disabled:cursor-not-allowed"
                          title="删除"
                        >
                          <Trash2 size={16} className="text-red-600" />
                        </button>
                      </div>
                    </div>
                    <h3 className="font-bold text-lg text-gray-900 mb-2">{slide.title}</h3>
                    <p className="text-gray-600 text-sm mb-3">{slide.description}</p>
                    {slide.content && (
                      <div className="text-gray-700 text-sm bg-gray-50 p-3 rounded-lg border border-gray-200 prose prose-sm max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{slide.content}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            <button
              onClick={() => void handleAddSlide()}
              disabled={isMutating}
              className="w-full flex items-center justify-center gap-2 p-4 bg-white border-2 border-dashed border-gray-400 rounded-xl hover:border-[var(--doraemon-blue)] hover:bg-[#F0F8FF] transition-all disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400"
            >
              <Plus size={20} className="text-gray-600" />
              <span className="font-bold text-gray-600">添加新页面</span>
            </button>
          </div>
        </div>

        <div className="p-4 bg-white border-t-4 border-gray-900">
          <button
            onClick={onClose}
            className="w-full p-3 bg-gray-200 text-gray-800 font-bold rounded-xl border-2 border-gray-900 hover:brightness-110 active:scale-95 transition-all shadow-[3px_3px_0px_rgba(0,0,0,1)]"
          >
            完成编辑
          </button>
        </div>
      </div>
    </div>
  );
}
