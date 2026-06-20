import { createBananaLectureApiClient } from '@/shared/api/banana';
import type {
  AdminDashboardStats,
  AdminUserList,
  AdminUsersQuery,
  AdminProjectsQuery,
  AdminProjectItem,
  LogList,
  LogQuery,
} from './types';

function getClient() {
  return createBananaLectureApiClient({
    getHeaders: (): Record<string, string> => {
      if (typeof localStorage === 'undefined') return {};
      const userId = localStorage.getItem('banana_user_id');
      if (!userId) return {};
      return { 'X-User-Id': userId };
    },
  });
}

export async function getDashboardStats(): Promise<AdminDashboardStats> {
  const res = await getClient().getAdminDashboardStats();
  return res.data;
}

export async function listAdminUsers(query: AdminUsersQuery = {}): Promise<AdminUserList> {
  const res = await getClient().listAdminUsers({
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
    sort_by: query.sort_by ?? 'last_active_at',
    order: query.order ?? 'desc',
  });
  return res.data;
}

export async function listAdminProjects(query: AdminProjectsQuery = {}): Promise<{
  items: AdminProjectItem[];
  pagination: { page: number; page_size: number; total: number; total_pages: number };
}> {
  const res = await getClient().listAdminProjects({
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
    sort_by: query.sort_by ?? 'created_at',
    order: query.order ?? 'desc',
    ...(query.user_id ? { user_id: query.user_id } : {}),
  });
  return res.data;
}

export async function getSystemLogs(query: LogQuery = {}): Promise<LogList> {
  const res = await getClient().getSystemLogs({
    limit: query.limit ?? 50,
    offset: query.offset ?? 0,
    order: query.order ?? 'desc',
    ...(query.level && query.level !== 'all' ? { level: query.level } : {}),
    ...(query.event ? { event: query.event } : {}),
    ...(query.start_time ? { start_time: query.start_time } : {}),
    ...(query.end_time ? { end_time: query.end_time } : {}),
  });
  return res.data;
}

export async function getProjectLogs(
  projectId: string,
  query: LogQuery = {}
): Promise<LogList> {
  const res = await getClient().getProjectLogs(projectId, {
    limit: query.limit ?? 50,
    offset: query.offset ?? 0,
    order: query.order ?? 'desc',
    ...(query.level && query.level !== 'all' ? { level: query.level } : {}),
    ...(query.event ? { event: query.event } : {}),
    ...(query.start_time ? { start_time: query.start_time } : {}),
    ...(query.end_time ? { end_time: query.end_time } : {}),
  });
  return res.data;
}
