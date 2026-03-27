import {
  createBananaLectureRequester,
  type BananaLectureApiClientOptions,
  type QueryParams,
} from '@/shared/api/banana/request';
import type {
  AddDialogueDataDTO,
  AddDialogueRequest,
  AddSlideDataDTO,
  AddSlideRequest,
  ApiResponse,
  CreateProjectRequest,
  CreateSlidesDataDTO,
  CreateSlidesRequest,
  DialogueDTO,
  DialoguesListDataDTO,
  GenerateDialoguesDataDTO,
  ListProjectsQuery,
  ModifyImageRequest,
  ProjectDTO,
  ProjectDetailDTO,
  ProjectListDataDTO,
  ReorderDialoguesDataDTO,
  ReorderDialoguesRequest,
  ReorderSlidesDataDTO,
  ReorderSlidesRequest,
  SlideDTO,
  SlidesListDataDTO,
  TaskDTO,
  TaskReferenceDTO,
  UpdateDialogueRequest,
  UpdateProjectRequest,
  UpdateSlideRequest,
} from '@/shared/api/banana/types';

export function createBananaLectureApiClient(options: BananaLectureApiClientOptions = {}) {
  const requester = createBananaLectureRequester(options);

  return {
    createProject(payload: CreateProjectRequest): Promise<ApiResponse<ProjectDTO>> {
      return requester.requestJson<ProjectDTO>('/projects', { method: 'POST', body: payload });
    },

    listProjects(
      userId: string,
      query?: ListProjectsQuery
    ): Promise<ApiResponse<ProjectListDataDTO>> {
      return requester.requestJson<ProjectListDataDTO>(`/${userId}/projects`, {
        method: 'GET',
        query: query as QueryParams | undefined,
      });
    },

    getProject(projectId: string): Promise<ApiResponse<ProjectDetailDTO>> {
      return requester.requestJson<ProjectDetailDTO>(`/projects/${projectId}`, { method: 'GET' });
    },

    updateProject(
      projectId: string,
      payload: UpdateProjectRequest
    ): Promise<ApiResponse<Partial<ProjectDTO>>> {
      return requester.requestJson<Partial<ProjectDTO>>(`/projects/${projectId}`, {
        method: 'PUT',
        body: payload,
      });
    },

    deleteProject(projectId: string): Promise<ApiResponse<null>> {
      return requester.requestJson<null>(`/projects/${projectId}`, { method: 'DELETE' });
    },

    createSlides(
      projectId: string,
      payload: CreateSlidesRequest
    ): Promise<ApiResponse<CreateSlidesDataDTO>> {
      return requester.requestJson<CreateSlidesDataDTO>(`/projects/${projectId}/slides`, {
        method: 'POST',
        body: payload,
      });
    },

    listSlides(projectId: string): Promise<ApiResponse<SlidesListDataDTO>> {
      return requester.requestJson<SlidesListDataDTO>(`/projects/${projectId}/slides`, {
        method: 'GET',
      });
    },

    updateSlide(
      projectId: string,
      slideId: string,
      payload: UpdateSlideRequest
    ): Promise<ApiResponse<SlideDTO>> {
      return requester.requestJson<SlideDTO>(`/projects/${projectId}/slides/${slideId}`, {
        method: 'PUT',
        body: payload,
      });
    },

    deleteSlide(projectId: string, slideId: string): Promise<ApiResponse<null>> {
      return requester.requestJson<null>(`/projects/${projectId}/slides/${slideId}`, {
        method: 'DELETE',
      });
    },

    reorderSlides(
      projectId: string,
      payload: ReorderSlidesRequest
    ): Promise<ApiResponse<ReorderSlidesDataDTO>> {
      return requester.requestJson<ReorderSlidesDataDTO>(`/projects/${projectId}/slides/reorder`, {
        method: 'POST',
        body: payload,
      });
    },

    addSlide(projectId: string, payload: AddSlideRequest): Promise<ApiResponse<AddSlideDataDTO>> {
      return requester.requestJson<AddSlideDataDTO>(`/projects/${projectId}/slides/add`, {
        method: 'POST',
        body: payload,
      });
    },

    generateSlideImage(projectId: string, slideId: string): Promise<ApiResponse<null>> {
      return requester.requestJson<null>(
        `/projects/${projectId}/slides/${slideId}/image/generate`,
        { method: 'POST' }
      );
    },

    modifySlideImage(
      projectId: string,
      slideId: string,
      payload: ModifyImageRequest
    ): Promise<ApiResponse<null>> {
      return requester.requestJson<null>(`/projects/${projectId}/slides/${slideId}/image/modify`, {
        method: 'POST',
        body: payload,
      });
    },

    batchGenerateImages(projectId: string): Promise<ApiResponse<TaskReferenceDTO>> {
      return requester.requestJson<TaskReferenceDTO>(
        `/projects/${projectId}/images/batch-generate`,
        { method: 'POST' }
      );
    },

    getSlideImageFile(projectId: string, slideId: string) {
      return requester.request(`/projects/${projectId}/slides/${slideId}/image/file`, {
        method: 'GET',
      });
    },

    getSlideImageFileBlob(projectId: string, slideId: string) {
      return requester.requestBlob(`/projects/${projectId}/slides/${slideId}/image/file`, {
        method: 'GET',
      });
    },

    getSlideImageFileUrl(projectId: string, slideId: string) {
      return requester.buildFileUrl(`/projects/${projectId}/slides/${slideId}/image/file`);
    },

    generateSlideDialogues(
      projectId: string,
      slideId: string
    ): Promise<ApiResponse<GenerateDialoguesDataDTO>> {
      return requester.requestJson<GenerateDialoguesDataDTO>(
        `/projects/${projectId}/slides/${slideId}/dialogues/generate`,
        { method: 'POST' }
      );
    },

    batchGenerateDialogues(projectId: string): Promise<ApiResponse<TaskReferenceDTO>> {
      return requester.requestJson<TaskReferenceDTO>(
        `/projects/${projectId}/dialogues/batch-generate`,
        { method: 'POST' }
      );
    },

    listDialogues(projectId: string, slideId: string): Promise<ApiResponse<DialoguesListDataDTO>> {
      return requester.requestJson<DialoguesListDataDTO>(
        `/projects/${projectId}/slides/${slideId}/dialogues`,
        { method: 'GET' }
      );
    },

    updateDialogue(
      projectId: string,
      slideId: string,
      dialogueId: string,
      payload: UpdateDialogueRequest
    ): Promise<ApiResponse<DialogueDTO>> {
      return requester.requestJson<DialogueDTO>(
        `/projects/${projectId}/slides/${slideId}/dialogues/${dialogueId}`,
        { method: 'PUT', body: payload }
      );
    },

    deleteDialogue(
      projectId: string,
      slideId: string,
      dialogueId: string
    ): Promise<ApiResponse<null>> {
      return requester.requestJson<null>(
        `/projects/${projectId}/slides/${slideId}/dialogues/${dialogueId}`,
        { method: 'DELETE' }
      );
    },

    reorderDialogues(
      projectId: string,
      slideId: string,
      payload: ReorderDialoguesRequest
    ): Promise<ApiResponse<ReorderDialoguesDataDTO>> {
      return requester.requestJson<ReorderDialoguesDataDTO>(
        `/projects/${projectId}/slides/${slideId}/dialogues/reorder`,
        { method: 'POST', body: payload }
      );
    },

    addDialogue(
      projectId: string,
      slideId: string,
      payload: AddDialogueRequest
    ): Promise<ApiResponse<AddDialogueDataDTO>> {
      return requester.requestJson<AddDialogueDataDTO>(
        `/projects/${projectId}/slides/${slideId}/dialogues/add`,
        { method: 'POST', body: payload }
      );
    },

    generateSlideAudio(projectId: string, slideId: string): Promise<ApiResponse<null>> {
      return requester.requestJson<null>(
        `/projects/${projectId}/slides/${slideId}/audio/generate`,
        { method: 'POST' }
      );
    },

    batchGenerateAudio(projectId: string): Promise<ApiResponse<TaskReferenceDTO>> {
      return requester.requestJson<TaskReferenceDTO>(
        `/projects/${projectId}/audio/batch-generate`,
        { method: 'POST' }
      );
    },

    getDialogueAudioFile(projectId: string, slideId: string, dialogueId: string) {
      return requester.request(
        `/projects/${projectId}/slides/${slideId}/dialogues/${dialogueId}/audio/file`,
        { method: 'GET' }
      );
    },

    getDialogueAudioFileBlob(projectId: string, slideId: string, dialogueId: string) {
      return requester.requestBlob(
        `/projects/${projectId}/slides/${slideId}/dialogues/${dialogueId}/audio/file`,
        { method: 'GET' }
      );
    },

    getDialogueAudioFileUrl(projectId: string, slideId: string, dialogueId: string) {
      return requester.buildFileUrl(
        `/projects/${projectId}/slides/${slideId}/dialogues/${dialogueId}/audio/file`
      );
    },

    getSlideAudioFile(projectId: string, slideId: string) {
      return requester.request(`/projects/${projectId}/slides/${slideId}/audio/file`, {
        method: 'GET',
      });
    },

    getSlideAudioFileBlob(projectId: string, slideId: string) {
      return requester.requestBlob(`/projects/${projectId}/slides/${slideId}/audio/file`, {
        method: 'GET',
      });
    },

    getSlideAudioFileUrl(projectId: string, slideId: string) {
      return requester.buildFileUrl(`/projects/${projectId}/slides/${slideId}/audio/file`);
    },

    generateVideo(projectId: string): Promise<ApiResponse<TaskReferenceDTO>> {
      return requester.requestJson<TaskReferenceDTO>(`/projects/${projectId}/video/generate`, {
        method: 'POST',
      });
    },

    getVideoFile(projectId: string) {
      return requester.request(`/projects/${projectId}/video/file`, { method: 'GET' });
    },

    getVideoFileBlob(projectId: string) {
      return requester.requestBlob(`/projects/${projectId}/video/file`, { method: 'GET' });
    },

    getVideoFileUrl(projectId: string) {
      return requester.buildFileUrl(`/projects/${projectId}/video/file`);
    },

    getTask(taskId: string): Promise<ApiResponse<TaskDTO>> {
      return requester.requestJson<TaskDTO>(`/tasks/${taskId}`, { method: 'GET' });
    },

    cancelTask(taskId: string): Promise<ApiResponse<TaskDTO>> {
      return requester.requestJson<TaskDTO>(`/tasks/${taskId}`, { method: 'DELETE' });
    },
  };
}

export type BananaLectureApiClient = ReturnType<typeof createBananaLectureApiClient>;
