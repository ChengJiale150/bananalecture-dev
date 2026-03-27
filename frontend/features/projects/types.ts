import {
  DIALOGUE_EMOTIONS,
  DIALOGUE_ROLES,
  DIALOGUE_SPEEDS,
  SLIDE_TYPES,
} from '@/shared/api/banana/types';

export { DIALOGUE_EMOTIONS, DIALOGUE_ROLES, DIALOGUE_SPEEDS, SLIDE_TYPES };

export type SlideType = (typeof SLIDE_TYPES)[number];
export type DialogueRole = (typeof DIALOGUE_ROLES)[number];
export type DialogueEmotion = (typeof DIALOGUE_EMOTIONS)[number];
export type DialogueSpeed = (typeof DIALOGUE_SPEEDS)[number];

export interface Dialogue {
  id: string;
  role: DialogueRole;
  content: string;
  emotion?: DialogueEmotion;
  speed?: DialogueSpeed;
  audioPath?: string;
}

export interface Slide {
  id: string;
  type: SlideType;
  title: string;
  description: string;
  content?: string;
  imagePath?: string;
  audioPath?: string;
  dialogues?: Dialogue[];
}

export interface PPTPlan {
  slides: Slide[];
}

export function moveSlideUp(slides: Slide[], index: number): Slide[] {
  if (index <= 0 || index >= slides.length) return slides;
  const nextSlides = [...slides];
  const current = nextSlides[index];
  nextSlides[index] = nextSlides[index - 1];
  nextSlides[index - 1] = current;
  return nextSlides;
}

export function moveSlideDown(slides: Slide[], index: number): Slide[] {
  if (index < 0 || index >= slides.length - 1) return slides;
  const nextSlides = [...slides];
  const current = nextSlides[index];
  nextSlides[index] = nextSlides[index + 1];
  nextSlides[index + 1] = current;
  return nextSlides;
}

export interface ProjectSummary {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
}

export interface ProjectListPagination {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface ProjectListPage {
  items: ProjectSummary[];
  pagination: ProjectListPagination;
}

export interface ProjectRecord extends ProjectSummary {
  userId: string;
  messages: unknown[];
  videoPath?: string;
  pptPlan?: PPTPlan;
}

export interface TaskProgress {
  id: string;
  projectId: string;
  type: string;
  status: string;
  currentStep: number;
  totalSteps: number;
  errorMessage?: string | null;
  createdAt: string;
  updatedAt: string;
}

export const GENERATION_STAGES = ['images', 'dialogues', 'audio', 'video'] as const;
export const GENERATION_SESSION_MODES = ['pipeline', 'single-stage'] as const;
export const GENERATION_STAGE_STATUSES = [
  'pending',
  'running',
  'completed',
  'failed',
  'cancelled',
] as const;
export const GENERATION_SESSION_STATUSES = ['running', 'completed', 'failed', 'cancelled'] as const;

export type GenerationStage = (typeof GENERATION_STAGES)[number];
export type GenerationSessionMode = (typeof GENERATION_SESSION_MODES)[number];
export type GenerationStageStatus = (typeof GENERATION_STAGE_STATUSES)[number];
export type GenerationSessionStatus = (typeof GENERATION_SESSION_STATUSES)[number];

export interface GenerationStageState {
  stage: GenerationStage;
  label: string;
  status: GenerationStageStatus;
  progress: number;
  taskId?: string;
}

export interface GenerationSessionState {
  mode: GenerationSessionMode;
  projectId: string;
  status: GenerationSessionStatus;
  currentStage: GenerationStage | null;
  stages: GenerationStageState[];
  activeTask?: TaskProgress | null;
  errorMessage?: string | null;
  updatedAt: number;
}
