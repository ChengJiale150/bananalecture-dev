import type {
  AdminDashboardStatsDTO,
  AdminUserItemDTO,
  AdminUserListDTO,
  AdminUsersQuery,
  AdminProjectsQuery,
  AdminProjectItemDTO,
  LogEntryDTO,
  LogListDTO,
  LogQuery,
  PaginationDTO,
} from '@/shared/api/banana/types';

export type AdminDashboardStats = AdminDashboardStatsDTO;
export type AdminUserItem = AdminUserItemDTO;
export type AdminUserList = AdminUserListDTO;
export type AdminProjectItem = AdminProjectItemDTO;
export type LogEntry = LogEntryDTO;
export type LogList = LogListDTO;
export type { AdminUsersQuery, AdminProjectsQuery, LogQuery, PaginationDTO };

export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}
