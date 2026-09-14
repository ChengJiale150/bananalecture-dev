'use client';

import { CheckCircle2, Loader2 } from 'lucide-react';
import { DEFAULT_TEMPLATE_ID, getTemplateName } from '@/shared/template-config';

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

export default function ToolView({ invocation, templateId }: { invocation: ToolInvocation; templateId?: string }) {
  const { toolName, args, state } = invocation;
  const templateName = getTemplateName(templateId ?? DEFAULT_TEMPLATE_ID);
  const isComplete =
    state === 'result' ||
    state === 'output-available' ||
    state === 'output-error' ||
    state === 'output-denied';
  const isStreaming = state === 'partial-call' || state === 'call' || state === 'input-available';

  if (!args && isStreaming) {
    return (
      <div className="my-4">
        <div className="p-4 bg-white border-2 border-[var(--banana-blue)] rounded-xl shadow-[4px_4px_0px_var(--banana-blue)]">
          <div className="flex items-center gap-2 text-[var(--banana-blue)] font-bold">
            <Loader2 size={20} className="animate-spin" />
            <span>正在生成{templateName}教学漫画 PPT 规划...</span>
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

    return (
      <div className="my-4">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 p-4 bg-white border-2 border-[var(--banana-blue)] rounded-xl shadow-[4px_4px_0px_var(--banana-blue)]">
          {isComplete ? (
            <CheckCircle2 size={20} className="text-green-500" />
          ) : (
            <Loader2 size={20} className="animate-spin text-[var(--banana-blue)]" />
          )}
          <span className="font-bold text-[var(--banana-blue)]">
            {templateName}教学漫画 PPT 规划
          </span>
          <span className="text-sm text-gray-500">
            {slides.length > 0 ? `${slides.length} 页` : '准备中'}
          </span>
          <span className="w-full text-xs text-gray-500 sm:w-auto">
            {isStreaming
              ? '正在左侧编辑器实时生成，可稍后直接编辑'
              : '规划已完成并同步到左侧编辑器，编辑后即可进入 PPT 预览'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="my-4 p-4 bg-white border-2 border-gray-900 rounded-xl shadow-[4px_4px_0px_rgba(0,0,0,1)] text-sm font-mono">
      <div className="font-black text-gray-900 text-xs mb-2 uppercase tracking-widest flex items-center gap-2">
        <div className="w-3 h-3 bg-[var(--banana-blue)] rounded-full"></div>
        TOOL: {toolName}
        {isStreaming && <Loader2 size={12} className="animate-spin" />}
      </div>
      <div className="bg-gray-50 p-3 rounded-lg border-2 border-gray-200 overflow-x-auto text-xs">
        {JSON.stringify(args, null, 2)}
      </div>
    </div>
  );
}
