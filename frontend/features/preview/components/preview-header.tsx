import {
  ArrowLeft,
  ChevronDown,
  Download,
  FileText,
  Image as ImageIcon,
  Loader2,
  RefreshCw,
  Settings,
  Sparkles,
  Square,
  Video,
  Volume2,
} from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import { useBasePath } from '@/contexts/base-path-context';
import type { GenerationSessionState, GenerationStage } from '@/features/projects/types';

interface PreviewHeaderProps {
  isGeneratingAll: boolean;
  isRefreshing: boolean;
  generationSession: GenerationSessionState | null;
  overallGenerationProgress: number;
  hasVideo: boolean;
  handleStopGeneration: () => void;
  handleGenerateAll: () => void;
  handleStartStageGeneration: (stage: GenerationStage) => void;
  handleDownloadVideo: () => void;
  handleForceRefresh: () => Promise<void>;
}

const ADVANCED_ACTIONS: Array<{ stage: GenerationStage; label: string; icon: typeof ImageIcon }> = [
  { stage: 'images', label: '批量生成图片', icon: ImageIcon },
  { stage: 'dialogues', label: '批量生成口播稿', icon: FileText },
  { stage: 'audio', label: '批量生成音频', icon: Volume2 },
  { stage: 'video', label: '批量生成视频', icon: Video },
];

export function PreviewHeader({
  isGeneratingAll,
  isRefreshing,
  generationSession,
  overallGenerationProgress,
  hasVideo,
  handleStopGeneration,
  handleGenerateAll,
  handleStartStageGeneration,
  handleDownloadVideo,
  handleForceRefresh,
}: PreviewHeaderProps) {
  const { basePath } = useBasePath();
  const [showAdvancedTools, setShowAdvancedTools] = useState(false);
  const progressValue = generationSession ? Math.round(overallGenerationProgress) : 0;
  const progressTone =
    generationSession?.status === 'failed'
      ? 'bg-red-500'
      : generationSession?.status === 'cancelled'
        ? 'bg-gray-400'
        : generationSession?.status === 'completed'
          ? 'bg-green-500'
          : 'bg-[var(--banana-blue)]';

  return (
    <header className="bg-white border-b-4 border-gray-900 shadow-sm flex-none z-10 relative">
      <div className="px-6 py-3 flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link
            href={basePath || '/'}
            className="flex items-center gap-2 px-3 py-2 bg-gray-100 text-gray-700 rounded-xl border-2 border-gray-900 hover:bg-gray-200 transition-all shadow-[2px_2px_0px_rgba(0,0,0,1)]"
            title="返回规划空间"
          >
            <ArrowLeft size={18} />
          </Link>
          <button
            onClick={handleGenerateAll}
            disabled={isGeneratingAll}
            className={`flex items-center gap-2 px-6 py-3 text-white font-black rounded-full border-2 border-gray-900 transition-all shadow-[3px_3px_0px_rgba(0,0,0,1)] ${
              isGeneratingAll
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-[var(--banana-blue)] hover:brightness-110'
            }`}
          >
            <Sparkles size={18} />
            {isGeneratingAll ? '生成进行中' : '一键生成'}
          </button>
          <button
            onClick={handleDownloadVideo}
            disabled={!hasVideo}
            className={`flex items-center gap-2 px-6 py-3 font-bold rounded-full border-2 transition-all ${
              hasVideo
                ? 'bg-white text-orange-500 border-orange-500 hover:bg-orange-50'
                : 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
            }`}
          >
            <Download size={18} />
            下载视频
          </button>
        </div>

        <div className="flex items-center gap-4 relative">
          <div className="relative">
            <button
              onClick={() => setShowAdvancedTools(value => !value)}
              className="flex items-center gap-2 px-4 py-2 bg-white text-orange-500 font-bold rounded-full border-2 border-orange-500 hover:bg-orange-50 transition-all"
            >
              <Settings size={18} />
              高级功能 <ChevronDown size={16} />
            </button>
            {showAdvancedTools && (
              <div className="absolute top-full mt-2 right-0 bg-white border-2 border-[var(--banana-blue)] rounded-xl shadow-lg w-56 overflow-hidden z-50">
                {ADVANCED_ACTIONS.map((action, index) => {
                  const Icon = action.icon;

                  return (
                    <button
                      key={action.stage}
                      onClick={() => {
                        void handleStartStageGeneration(action.stage);
                        setShowAdvancedTools(false);
                      }}
                      disabled={isGeneratingAll}
                      className={`w-full flex items-center gap-2 px-4 py-3 text-left text-[var(--banana-blue)] hover:bg-blue-50 ${
                        index < ADVANCED_ACTIONS.length - 1 ? 'border-b border-gray-100' : ''
                      } ${isGeneratingAll ? 'cursor-not-allowed bg-gray-50 text-gray-300' : ''}`}
                    >
                      <Icon size={16} />
                      {action.label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
          <button
            onClick={() => void handleForceRefresh()}
            disabled={isRefreshing}
            className={`flex items-center gap-2 px-4 py-2 font-bold rounded-full border-2 transition-all ${
              isRefreshing
                ? 'bg-green-100 text-green-400 border-green-200 cursor-wait'
                : 'bg-white text-green-500 border-green-500 hover:bg-green-50'
            }`}
          >
            {isRefreshing ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <RefreshCw size={18} />
            )}
            {isRefreshing ? '重新加载中' : '刷新'}
          </button>
        </div>
      </div>

      <div className="px-6 pb-3">
        <div className="rounded-2xl border-2 border-gray-900 bg-[#F7FBFF] px-4 py-3 shadow-[4px_4px_0px_rgba(0,0,0,1)]">
          <div className="flex items-center gap-3">
            <div className="h-3 flex-1 overflow-hidden rounded-full border border-gray-900 bg-white">
              <div
                className={`h-full transition-all duration-500 ${progressTone}`}
                style={{ width: `${progressValue}%` }}
              />
            </div>
            <div className="min-w-14 text-right text-sm font-black text-gray-900">
              {progressValue}%
            </div>
            {isGeneratingAll && (
              <button
                onClick={handleStopGeneration}
                className="flex items-center gap-1 rounded-lg bg-red-100 px-3 py-1.5 text-sm font-bold text-red-600 transition-colors hover:bg-red-200"
                title="停止生成"
              >
                <Square size={14} fill="currentColor" />
                停止
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
