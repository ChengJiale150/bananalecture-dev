'use client';

import { Loader2 } from 'lucide-react';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { DialogueList } from '@/features/preview/components/dialogue-list';
import { EmptyState } from '@/features/preview/components/empty-state';
import { PreviewFooter } from '@/features/preview/components/preview-footer';
import { PreviewHeader } from '@/features/preview/components/preview-header';
import { SlideViewer } from '@/features/preview/components/slide-viewer';
import { usePreviewState } from '@/features/preview/hooks/use-preview-state';

function PreviewContent() {
  const searchParams = useSearchParams();
  const projectIdFromUrl = searchParams.get('id');
  const pageFromUrl = searchParams.get('page');
  const legacyRefreshTokenFromUrl = searchParams.get('refresh');

  const {
    plan,
    currentSlideIndex,
    setCurrentSlideIndex,
    isLoading,
    isRefreshing,
    isGeneratingAll,
    isDialogueActionPending,
    generationSession,
    overallGenerationProgress,
    currentSlide,
    displayDialogues,
    currentSlideImageUrl,
    currentSlideAudioUrl,
    isGeneratingImage,
    isModifyingImage,
    isGeneratingDialogues,
    isGeneratingAudio,
    handleGenerateDialogues,
    handleGenerateAll,
    handleStartStageGeneration,
    handleStopGeneration,
    handleForceRefresh,
    handleAddDialogue,
    handleUpdateDialogue,
    handleDeleteDialogue,
    handleMoveDialogue,
    handleGenerateImage,
    handleModifyImage,
    handleGenerateAudio,
    handleDownloadVideo,
    projectVideoPath,
  } = usePreviewState(projectIdFromUrl, pageFromUrl, legacyRefreshTokenFromUrl);

  if (isLoading) {
    return (
      <div className="h-screen bg-[#F0F8FF] flex flex-col overflow-hidden">
        <header className="bg-white border-b-4 border-gray-900 shadow-sm h-[72px] animate-pulse" />
        <div className="flex-1 min-h-0 p-4 pb-3">
          <div className="h-full grid min-h-0 gap-4 lg:grid-cols-[minmax(0,1fr)_420px]">
            <div className="rounded-[28px] border-4 border-gray-900 bg-white shadow-[8px_8px_0px_rgba(0,0,0,1)] animate-pulse" />
            <div className="rounded-[28px] border-4 border-gray-900 bg-white shadow-[8px_8px_0px_rgba(0,0,0,1)] animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-[#F0F8FF] flex flex-col overflow-hidden">
      <PreviewHeader
        isGeneratingAll={isGeneratingAll}
        isRefreshing={isRefreshing}
        generationSession={generationSession}
        overallGenerationProgress={overallGenerationProgress}
        hasVideo={Boolean(projectVideoPath)}
        handleStopGeneration={handleStopGeneration}
        handleGenerateAll={handleGenerateAll}
        handleStartStageGeneration={handleStartStageGeneration}
        handleDownloadVideo={handleDownloadVideo}
        handleForceRefresh={handleForceRefresh}
      />

      {plan && plan.slides.length > 0 && currentSlide ? (
        <div className="flex-1 min-h-0 p-4 pb-3">
          <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[minmax(0,1fr)_420px]">
            <SlideViewer
              currentSlide={currentSlide}
              isGeneratingAll={isGeneratingAll}
              isGeneratingImage={isGeneratingImage}
              isModifyingImage={isModifyingImage}
              isGeneratingDialogues={isGeneratingDialogues}
              isGeneratingAudio={isGeneratingAudio}
              handleGenerateDialogues={handleGenerateDialogues}
              handleGenerateImage={handleGenerateImage}
              handleModifyImage={handleModifyImage}
              handleGenerateAudio={handleGenerateAudio}
              slideImageUrl={currentSlideImageUrl}
              slideAudioUrl={currentSlideAudioUrl}
            />
            <DialogueList
              dialogues={displayDialogues}
              isBusy={isDialogueActionPending}
              onAdd={handleAddDialogue}
              onUpdate={handleUpdateDialogue}
              onDelete={handleDeleteDialogue}
              onMove={handleMoveDialogue}
            />
          </div>
        </div>
      ) : (
        <EmptyState />
      )}

      {plan && plan.slides.length > 0 && (
        <PreviewFooter
          currentSlideIndex={currentSlideIndex}
          totalSlides={plan.slides.length}
          onPageSelect={page => setCurrentSlideIndex(page - 1)}
        />
      )}
    </div>
  );
}

export default function PreviewPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#F0F8FF] flex items-center justify-center">
          <Loader2 size={48} className="animate-spin text-[var(--banana-blue)]" />
        </div>
      }
    >
      <PreviewContent />
    </Suspense>
  );
}
