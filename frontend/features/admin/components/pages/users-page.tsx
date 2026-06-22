'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useBasePath } from '@/contexts/base-path-context';
import { Users, User, AlertCircle, Loader2, ExternalLink } from 'lucide-react';
import Pagination from '@/features/admin/components/shared/pagination';
import EmptyState from '@/features/admin/components/shared/empty-state';
import { listAdminUsers } from '@/features/admin/api';
import type { AdminUserItem, PaginationDTO } from '@/features/admin/types';

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '刚刚';
  if (mins < 60) return `${mins}分钟前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  return `${days}天前`;
}

type SortKey = 'user_id' | 'project_count' | 'last_active_at';

export default function UsersPage() {
  const router = useRouter();
  const { basePath } = useBasePath();
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [pagination, setPagination] = useState<PaginationDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<SortKey>('last_active_at');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    listAdminUsers({ page, page_size: 20, sort_by: sortBy, order })
      .then(data => {
        setUsers(data.items);
        setPagination(data.pagination);
      })
      .catch(e => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false));
  }, [page, sortBy, order]);

  useEffect(load, [load]);

  const handleSortChange = (value: string) => {
    const [col, dir] = value.split('_') as [SortKey, 'asc' | 'desc'];
    setSortBy(col);
    setOrder(dir);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-black text-gray-900 flex items-center gap-2">
          <Users size={20} /> 用户管理
        </h2>
        <select
          value={`${sortBy}_${order}`}
          onChange={e => handleSortChange(e.target.value)}
          className="rounded-lg border-2 border-gray-300 px-3 py-1.5 text-xs font-bold text-gray-700 outline-none focus:border-[var(--banana-blue)]"
        >
          <option value="last_active_at_desc">最近活跃 ↓</option>
          <option value="last_active_at_asc">最近活跃 ↑</option>
          <option value="project_count_desc">项目数 ↓</option>
          <option value="project_count_asc">项目数 ↑</option>
          <option value="user_id_asc">用户 ID A-Z</option>
          <option value="user_id_desc">用户 ID Z-A</option>
        </select>
      </div>

      {error && (
        <div className="banana-card border-[var(--banana-red)] p-6 text-center">
          <AlertCircle size={32} className="mx-auto mb-2 text-[var(--banana-red)]" />
          <p className="mb-3 font-bold text-gray-700">{error}</p>
          <button onClick={load} className="banana-btn banana-btn-primary">重试</button>
        </div>
      )}

      {loading && !error && (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="banana-card p-4 animate-pulse">
              <div className="h-6 w-48 rounded bg-gray-200" />
            </div>
          ))}
        </div>
      )}

      {!loading && !error && users.length === 0 && (
        <EmptyState
          icon={<Users size={64} />}
          title="暂无用户"
          description="还没有用户创建项目"
        />
      )}

      {!error && users.length > 0 && (
        <div className="space-y-3">
          {users.map(user => (
            <div key={user.user_id} className="banana-card p-4">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-4 min-w-0 flex-1">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-gray-900 bg-[var(--banana-blue)]">
                    <User size={18} className="text-white" />
                  </div>
                  <div className="min-w-0">
                    <p
                      className="truncate font-mono text-sm font-bold text-gray-900"
                      title={user.user_id}
                    >
                      {user.user_id}
                    </p>
                    <p className="text-xs text-gray-400">
                      最后活跃 {formatRelativeTime(user.last_active_at)}
                    </p>
                  </div>
                </div>
                <div className="shrink-0 text-center">
                  <span className="banana-btn banana-btn-warning inline-block px-3 py-1 text-xs">
                    {user.project_count} 个项目
                  </span>
                </div>
                <button
                  onClick={() =>
                    router.push(`${basePath}/admin/projects?user_id=${encodeURIComponent(user.user_id)}`)
                  }
                  className="flex items-center gap-1 rounded-lg border-2 border-gray-300 px-3 py-1.5 text-xs font-bold text-gray-600 transition-colors hover:border-gray-900 hover:text-gray-900"
                >
                  <ExternalLink size={14} />
                  查看项目
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {pagination && (
        <div className="flex justify-center">
          <Pagination
            currentPage={pagination.page}
            totalPages={pagination.total_pages}
            isLoading={loading}
            onPageChange={setPage}
          />
        </div>
      )}
    </div>
  );
}
