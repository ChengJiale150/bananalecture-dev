export const SLIDE_TYPES = ['cover', 'introduction', 'content', 'summary', 'ending'] as const;
export const DIALOGUE_ROLES = ['大雄', '哆啦A梦', '旁白', '其他男声', '其他女声', '道具'] as const;
export const DIALOGUE_EMOTIONS = [
  '开心的',
  '悲伤的',
  '生气的',
  '害怕的',
  '惊讶的',
  '无明显情感',
] as const;
export const DIALOGUE_SPEEDS = ['慢速', '中速', '快速'] as const;
export const TASK_TYPES = [
  'dialogue_generation',
  'audio_generation',
  'image_generation',
  'video_generation',
] as const;
export const TASK_STATUSES = ['pending', 'running', 'completed', 'cancelled', 'failed'] as const;

export type SlideType = (typeof SLIDE_TYPES)[number];
export type DialogueRole = (typeof DIALOGUE_ROLES)[number];
export type DialogueEmotion = (typeof DIALOGUE_EMOTIONS)[number];
export type DialogueSpeed = (typeof DIALOGUE_SPEEDS)[number];
export type TaskType = (typeof TASK_TYPES)[number];
export type TaskStatus = (typeof TASK_STATUSES)[number];

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export interface TaskReferenceDTO {
  task_id: string;
  project_id: string;
}

export interface PaginationDTO {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ProjectDTO {
  id: string;
  user_id: string;
  name: string;
  messages: string | null;
  // Storage keys are not direct browser URLs. Use the proxied file endpoints instead.
  video_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectListItemDTO {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface SlideDTO {
  id: string;
  project_id: string;
  type: SlideType | string;
  title: string;
  description: string;
  content: string | null;
  idx: number;
  // Storage keys are not direct browser URLs. Use the proxied file endpoints instead.
  image_path: string | null;
  // Storage keys are not direct browser URLs. Use the proxied file endpoints instead.
  audio_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface DialogueDTO {
  id: string;
  slide_id: string;
  role: DialogueRole | string;
  content: string;
  emotion: DialogueEmotion | string;
  speed: DialogueSpeed | string;
  idx: number;
  // Storage keys are not direct browser URLs. Use the proxied file endpoints instead.
  audio_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskDTO {
  id: string;
  project_id: string;
  type: TaskType | string;
  status: TaskStatus | string;
  current_step: number;
  total_steps: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectListDataDTO {
  items: ProjectListItemDTO[];
  pagination: PaginationDTO;
}

export interface ProjectDetailDTO extends ProjectDTO {
  slides: SlideDTO[];
}

export interface SlidesListDataDTO {
  items: SlideDTO[];
}

export interface CreateSlidesDataDTO {
  items: SlideDTO[];
}

export type AddSlideDataDTO = SlideDTO;

export interface ReorderSlidesDataDTO {
  slides: Array<Pick<SlideDTO, 'id' | 'idx'>>;
}

export interface DialoguesListDataDTO {
  items: DialogueDTO[];
  total: number;
}

export interface GenerateDialoguesDataDTO {
  slide_id: string;
  dialogues: DialogueDTO[];
}

export type AddDialogueDataDTO = DialogueDTO;

export interface ReorderDialoguesDataDTO {
  dialogues: Array<Pick<DialogueDTO, 'id' | 'idx'>>;
}

export interface CreateProjectRequest {
  name: string;
  user_id?: string;
}

export interface UpdateProjectRequest {
  name?: string;
  messages?: string;
}

export interface SlideInputDTO {
  type?: SlideType | string;
  title?: string;
  description?: string;
  content?: string;
}

export interface CreateSlidesRequest {
  slides: SlideInputDTO[];
}

export type AddSlideRequest = SlideInputDTO;

export type UpdateSlideRequest = SlideInputDTO;

export interface ReorderSlidesRequest {
  slide_ids: string[];
}

export interface AddDialogueRequest {
  role?: DialogueRole | string;
  content?: string;
  emotion?: DialogueEmotion | string;
  speed?: DialogueSpeed | string;
}

export interface UpdateDialogueRequest {
  role?: DialogueRole | string;
  content?: string;
  emotion?: DialogueEmotion | string;
  speed?: DialogueSpeed | string;
}

export interface ReorderDialoguesRequest {
  dialogue_ids: string[];
}

export interface ModifyImageRequest {
  prompt: string;
}

export interface ListProjectsQuery {
  page?: number;
  page_size?: number;
  sort_by?: string;
  order?: 'asc' | 'desc';
}

// Admin Dashboard
export interface AdminTaskStatsDTO {
  total: number;
  pending: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
}

export interface AdminDashboardStatsDTO {
  total_users: number;
  total_projects: number;
  total_slides: number;
  total_dialogues: number;
  tasks: AdminTaskStatsDTO;
}

// Admin User List
export interface AdminUserItemDTO {
  user_id: string;
  project_count: number;
  last_active_at: string;
}

export interface AdminUserListDTO {
  items: AdminUserItemDTO[];
  pagination: PaginationDTO;
}

// Admin Project List
export interface AdminProjectItemDTO {
  id: string;
  user_id: string;
  name: string;
  messages: string | null;
  video_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminProjectListDataDTO {
  items: AdminProjectItemDTO[];
  pagination: PaginationDTO;
}

// Log Entry
export interface LogEntryDTO {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  event: string | null;
  context: Record<string, unknown>;
  file: string | null;
  function: string | null;
  line: number | null;
}

export interface LogListDTO {
  total: number;
  offset: number;
  limit: number;
  items: LogEntryDTO[];
}

// Admin Query Params
export interface AdminUsersQuery {
  page?: number;
  page_size?: number;
  sort_by?: 'user_id' | 'project_count' | 'last_active_at';
  order?: 'asc' | 'desc';
}

export interface AdminProjectsQuery {
  user_id?: string;
  page?: number;
  page_size?: number;
  sort_by?: 'created_at' | 'updated_at' | 'name';
  order?: 'asc' | 'desc';
}

export interface LogQuery {
  level?: string;
  event?: string;
  start_time?: string;
  end_time?: string;
  limit?: number;
  offset?: number;
  order?: 'asc' | 'desc';
}
