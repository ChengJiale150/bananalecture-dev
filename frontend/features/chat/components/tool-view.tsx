'use client';

import {
  ChevronDown,
  ChevronRight,
  BookOpen,
  Sparkles,
  Lightbulb,
  FileText,
  Star,
  Loader2,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ToolInvocation {
  toolCallId: string;
  toolName: string;
  args: any;
  result?: any;
  state?:
    | 'result'
    | 'partial-call'
    | 'call'
    | 'input-available'
    | 'output-available'
    | 'output-error'
    | 'output-denied'
    | 'approval-requested'
    | 'approval-responded';
  approval?: {
    id: string;
    approved?: boolean;
    reason?: string;
  };
}

export default function ToolView({ invocation }: { invocation: ToolInvocation }) {
  const { toolName, args, state } = invocation;
  const isComplete =
    state === 'result' ||
    state === 'output-available' ||
    state === 'output-error' ||
    state === 'output-denied';
  const isStreaming = state === 'partial-call' || state === 'call' || state === 'input-available';
  const [isExpanded, setIsExpanded] = useState(!isComplete);

  useEffect(() => {
    if (isComplete) {
      setIsExpanded(false);
    } else if (isStreaming) {
      setIsExpanded(true);
    }
  }, [isComplete, isStreaming]);

  if (!args && isStreaming) {
    return (
      <div className="my-4">
        <div className="p-4 bg-white border-2 border-[var(--doraemon-blue)] rounded-xl shadow-[4px_4px_0px_var(--doraemon-blue)]">
          <div className="flex items-center gap-2 text-[var(--doraemon-blue)] font-bold">
            <Loader2 size={20} className="animate-spin" />
            <span>正在生成哆啦A梦教学漫画 PPT 规划...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!args) {
    return (
      <div className="my-2 p-3 bg-white border-2 border-gray-200 rounded-xl text-sm font-mono text-gray-500 animate-pulse">
        Loading tool {toolName}...
      </div>
    );
  }

  if (toolName === 'create_ppt_plan') {
    const slides = Array.isArray(args.slides) ? args.slides : [];

    const getSlideIcon = (type: string) => {
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

    const getSlideTypeLabel = (type: string) => {
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

    const getSlideBorderColor = (type: string) => {
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

    const getSlideShadowColor = (type: string) => {
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

    return (
      <div className="my-4">
        <div className="p-4 bg-white border-2 border-[var(--doraemon-blue)] rounded-xl shadow-[4px_4px_0px_var(--doraemon-blue)] mb-4">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full flex items-center justify-between font-bold text-[var(--doraemon-blue)] mb-1 hover:brightness-110 transition-all"
          >
            <div className="flex items-center gap-2">
              {isStreaming ? (
                <Loader2 size={24} className="animate-spin" />
              ) : (
                <Sparkles size={24} />
              )}
              <span className="text-lg">哆啦A梦教学漫画 PPT 规划</span>
              {isStreaming && (
                <span className="text-sm text-gray-500 font-normal">
                  (生成中... {slides.length} 页)
                </span>
              )}
            </div>
            {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          </button>
        </div>

        {isExpanded && (
          <div className="space-y-4">
            {slides.map((slide: any, index: number) => (
              <div
                key={index}
                className={`p-4 bg-white border-2 rounded-xl ${getSlideBorderColor(slide.type)} ${getSlideShadowColor(slide.type)} transition-all duration-300`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="flex items-center justify-center w-8 h-8 bg-gray-100 rounded-full font-bold text-gray-700">
                    {index + 1}
                  </div>
                  <div className="flex items-center gap-2">
                    {getSlideIcon(slide.type)}
                    <span className="font-bold text-gray-700">{getSlideTypeLabel(slide.type)}</span>
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
            ))}
            {isStreaming && slides.length > 0 && (
              <div className="flex items-center gap-2 text-gray-500 text-sm p-4 bg-gray-50 rounded-xl border-2 border-dashed border-gray-300">
                <Loader2 size={16} className="animate-spin" />
                <span>正在生成更多内容...</span>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="my-4 p-4 bg-white border-2 border-gray-900 rounded-xl shadow-[4px_4px_0px_rgba(0,0,0,1)] text-sm font-mono">
      <div className="font-black text-gray-900 text-xs mb-2 uppercase tracking-widest flex items-center gap-2">
        <div className="w-3 h-3 bg-[var(--doraemon-blue)] rounded-full"></div>
        TOOL: {toolName}
        {isStreaming && <Loader2 size={12} className="animate-spin" />}
      </div>
      <div className="bg-gray-50 p-3 rounded-lg border-2 border-gray-200 overflow-x-auto text-xs">
        {JSON.stringify(args, null, 2)}
      </div>
    </div>
  );
}
