import {
  createBananaLectureApiClient,
  type AddDialogueRequest,
  type CreateProjectRequest,
  type ListProjectsQuery,
  type SlideInputDTO,
  type UpdateDialogueRequest,
} from '@/shared/api/banana';
import type {
  DialogueDTO,
  ProjectDetailDTO,
  ProjectListItemDTO,
  SlideDTO,
  TaskDTO,
} from '@/shared/api/banana/types';
import type {
  Dialogue,
  DialogueEmotion,
  DialogueRole,
  DialogueSpeed,
  GenerationStage,
  ProjectListPage,
  ProjectRecord,
  ProjectSummary,
  Slide,
  SlideType,
  TaskProgress,
} from '@/features/projects/types';
import {
  DEFAULT_PROJECT_LIST_PAGE,
  DEFAULT_PROJECT_LIST_PAGE_SIZE,
  safeParseProjectMessages,
  stringifyProjectMessages,
} from '@/features/projects/utils';

const DEFAULT_USER_ID = 'admin';

function getApiClient() {
  return createBananaLectureApiClient();
}

function parseApiTimestamp(value: string): number {
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function toDialogueRole(role: string): DialogueRole {
  return role as DialogueRole;
}

function toDialogueEmotion(emotion: string): DialogueEmotion {
  return emotion as DialogueEmotion;
}

function toDialogueSpeed(speed: string): DialogueSpeed {
  return speed as DialogueSpeed;
}

function mapDialogue(dto: DialogueDTO): Dialogue {
  return {
    id: dto.id,
    role: toDialogueRole(dto.role),
    content: dto.content,
    emotion: toDialogueEmotion(dto.emotion),
    speed: toDialogueSpeed(dto.speed),
    audioPath: dto.audio_path ?? undefined,
  };
}

function mapSlide(dto: SlideDTO, dialogues?: Dialogue[]): Slide {
  return {
    id: dto.id,
    type: dto.type as SlideType,
    title: dto.title,
    description: dto.description,
    content: dto.content ?? undefined,
    imagePath: dto.image_path ?? undefined,
    audioPath: dto.audio_path ?? undefined,
    dialogues,
  };
}

function mapProjectSummary(dto: ProjectListItemDTO): ProjectSummary {
  return {
    id: dto.id,
    title: dto.name,
    createdAt: parseApiTimestamp(dto.created_at),
    updatedAt: parseApiTimestamp(dto.updated_at),
  };
}

function mapProjectRecord(dto: ProjectDetailDTO): ProjectRecord {
  return {
    id: dto.id,
    userId: dto.user_id,
    title: dto.name,
    createdAt: parseApiTimestamp(dto.created_at),
    updatedAt: parseApiTimestamp(dto.updated_at),
    messages: safeParseProjectMessages(dto.messages),
    videoPath: dto.video_path ?? undefined,
    pptPlan: dto.slides.length > 0 ? { slides: dto.slides.sort((a, b) => a.idx - b.idx).map((slide) => mapSlide(slide)) } : undefined,
  };
}

function mapTask(dto: TaskDTO): TaskProgress {
  return {
    id: dto.id,
    projectId: dto.project_id,
    type: dto.type,
    status: dto.status,
    currentStep: dto.current_step,
    totalSteps: dto.total_steps,
    errorMessage: dto.error_message,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function createSlideInput(slide: Slide): SlideInputDTO {
  return {
    type: slide.type,
    title: slide.title,
    description: slide.description,
    content: slide.content ?? '',
  };
}

export function createDialogueInput(dialogue: Dialogue): AddDialogueRequest {
  return {
    role: dialogue.role,
    content: dialogue.content,
    emotion: dialogue.emotion,
    speed: dialogue.speed,
  };
}

export function createDialogueUpdateInput(dialogue: Dialogue): UpdateDialogueRequest {
  return {
    role: dialogue.role,
    content: dialogue.content,
    emotion: dialogue.emotion,
    speed: dialogue.speed,
  };
}

export async function listProjects(query: ListProjectsQuery = {}): Promise<ProjectListPage> {
  const apiClient = getApiClient();
  const response = await apiClient.listProjects(DEFAULT_USER_ID, {
    page: query.page ?? DEFAULT_PROJECT_LIST_PAGE,
    page_size: query.page_size ?? DEFAULT_PROJECT_LIST_PAGE_SIZE,
    sort_by: 'updated_at',
    order: 'desc',
    ...query,
  });
  return {
    items: response.data.items.map(mapProjectSummary),
    pagination: {
      page: response.data.pagination.page,
      pageSize: response.data.pagination.page_size,
      total: response.data.pagination.total,
      totalPages: response.data.pagination.total_pages,
    },
  };
}

export async function createProject(payload: Pick<CreateProjectRequest, 'name'>) {
  const apiClient = getApiClient();
  const response = await apiClient.createProject({
    user_id: DEFAULT_USER_ID,
    name: payload.name,
  });

  return response.data.id;
}

export async function getProject(projectId: string) {
  const apiClient = getApiClient();
  const response = await apiClient.getProject(projectId);
  return mapProjectRecord(response.data);
}

export async function renameProject(projectId: string, title: string) {
  const apiClient = getApiClient();
  await apiClient.updateProject(projectId, { name: title });
}

export async function updateProjectMessages(projectId: string, messages: any[]) {
  const apiClient = getApiClient();
  await apiClient.updateProject(projectId, { messages: stringifyProjectMessages(messages) });
}

export async function updateProjectTitleAndMessages(projectId: string, title: string, messages: any[]) {
  const apiClient = getApiClient();
  await apiClient.updateProject(projectId, {
    name: title,
    messages: stringifyProjectMessages(messages),
  });
}

export async function deleteProject(projectId: string) {
  const apiClient = getApiClient();
  await apiClient.deleteProject(projectId);
}

export async function replaceProjectSlides(projectId: string, slides: Slide[]) {
  const apiClient = getApiClient();
  const response = await apiClient.createSlides(projectId, {
    slides: slides.map(createSlideInput),
  });
  return response.data.items.sort((a, b) => a.idx - b.idx).map((slide) => mapSlide(slide));
}

export async function updateSlide(projectId: string, slideId: string, slide: Slide) {
  const apiClient = getApiClient();
  const response = await apiClient.updateSlide(projectId, slideId, createSlideInput(slide));
  return mapSlide(response.data);
}

export async function addSlide(projectId: string, slide: Slide) {
  const apiClient = getApiClient();
  const response = await apiClient.addSlide(projectId, createSlideInput(slide));
  return mapSlide(response.data);
}

export async function deleteSlide(projectId: string, slideId: string) {
  const apiClient = getApiClient();
  await apiClient.deleteSlide(projectId, slideId);
}

export async function reorderSlides(projectId: string, slideIds: string[]) {
  const apiClient = getApiClient();
  await apiClient.reorderSlides(projectId, { slide_ids: slideIds });
}

export async function listDialogues(projectId: string, slideId: string) {
  const apiClient = getApiClient();
  const response = await apiClient.listDialogues(projectId, slideId);
  return response.data.items.sort((a, b) => a.idx - b.idx).map(mapDialogue);
}

export async function generateDialogues(projectId: string, slideId: string) {
  const apiClient = getApiClient();
  const response = await apiClient.generateSlideDialogues(projectId, slideId);
  return response.data.dialogues.sort((a, b) => a.idx - b.idx).map(mapDialogue);
}

export async function batchGenerateDialogues(projectId: string) {
  const apiClient = getApiClient();
  const response = await apiClient.batchGenerateDialogues(projectId);
  return response.data.task_id;
}

export async function addDialogue(projectId: string, slideId: string, dialogue: Dialogue) {
  const apiClient = getApiClient();
  const response = await apiClient.addDialogue(projectId, slideId, createDialogueInput(dialogue));
  return mapDialogue(response.data);
}

export async function updateDialogue(projectId: string, slideId: string, dialogue: Dialogue) {
  const apiClient = getApiClient();
  const response = await apiClient.updateDialogue(
    projectId,
    slideId,
    dialogue.id,
    createDialogueUpdateInput(dialogue),
  );
  return mapDialogue(response.data);
}

export async function deleteDialogue(projectId: string, slideId: string, dialogueId: string) {
  const apiClient = getApiClient();
  await apiClient.deleteDialogue(projectId, slideId, dialogueId);
}

export async function reorderDialogues(projectId: string, slideId: string, dialogueIds: string[]) {
  const apiClient = getApiClient();
  await apiClient.reorderDialogues(projectId, slideId, { dialogue_ids: dialogueIds });
}

export async function generateSlideImage(projectId: string, slideId: string) {
  const apiClient = getApiClient();
  await apiClient.generateSlideImage(projectId, slideId);
}

export async function modifySlideImage(projectId: string, slideId: string, prompt: string) {
  const apiClient = getApiClient();
  await apiClient.modifySlideImage(projectId, slideId, { prompt });
}

export async function batchGenerateImages(projectId: string) {
  const apiClient = getApiClient();
  const response = await apiClient.batchGenerateImages(projectId);
  return response.data.task_id;
}

export async function generateSlideAudio(projectId: string, slideId: string) {
  const apiClient = getApiClient();
  await apiClient.generateSlideAudio(projectId, slideId);
}

export async function batchGenerateAudio(projectId: string) {
  const apiClient = getApiClient();
  const response = await apiClient.batchGenerateAudio(projectId);
  return response.data.task_id;
}

export async function generateVideo(projectId: string) {
  const apiClient = getApiClient();
  const response = await apiClient.generateVideo(projectId);
  return response.data.task_id;
}

export async function getTask(taskId: string) {
  const apiClient = getApiClient();
  const response = await apiClient.getTask(taskId);
  return mapTask(response.data);
}

export async function cancelTask(taskId: string) {
  const apiClient = getApiClient();
  const response = await apiClient.cancelTask(taskId);
  return mapTask(response.data);
}

export function getSlideImageUrl(projectId: string, slideId: string) {
  const apiClient = getApiClient();
  return apiClient.getSlideImageFileUrl(projectId, slideId);
}

export function getSlideAudioUrl(projectId: string, slideId: string) {
  const apiClient = getApiClient();
  return apiClient.getSlideAudioFileUrl(projectId, slideId);
}

export function getDialogueAudioUrl(projectId: string, slideId: string, dialogueId: string) {
  const apiClient = getApiClient();
  return apiClient.getDialogueAudioFileUrl(projectId, slideId, dialogueId);
}

export function getVideoUrl(projectId: string) {
  const apiClient = getApiClient();
  return apiClient.getVideoFileUrl(projectId);
}

function getFilenameFromContentDisposition(value: string | null) {
  if (!value) {
    return null;
  }

  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const asciiMatch = value.match(/filename="?([^"]+)"?/i);
  return asciiMatch?.[1] ?? null;
}

export function getGenerationTaskStarter(stage: GenerationStage) {
  switch (stage) {
    case 'images':
      return batchGenerateImages;
    case 'dialogues':
      return batchGenerateDialogues;
    case 'audio':
      return batchGenerateAudio;
    case 'video':
      return generateVideo;
  }
}

export async function downloadVideoFile(projectId: string) {
  const apiClient = getApiClient();
  const response = await apiClient.getVideoFile(projectId);
  if (!response.ok) {
    let message = response.statusText || 'Failed to download video';

    try {
      const payload = (await response.json()) as { message?: string };
      message = payload.message || message;
    } catch {
      // Ignore parse failure and use status text fallback.
    }

    throw new Error(message);
  }

  const blob = await response.blob();
  const filename =
    getFilenameFromContentDisposition(response.headers.get('Content-Disposition')) ??
    `${projectId}.mp4`;

  return { blob, filename };
}
