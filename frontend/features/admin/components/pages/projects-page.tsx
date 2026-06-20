'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  FolderOpen,
  ExternalLink,
  Eye,
  AlertCircle,
  X,
  FileText,
} from 'lucide-react';
import Pagination from '@/features/admin/components/shared/pagination';
import EmptyState from '@/features/admin/components/shared/empty-state';
import { listAdminProjects } from '@/features/admin/api';
import type { AdminProjectItem, PaginationDTO } from '@/features/admin/types';

export default function ProjectsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const filterUserId = searchParams.get('user_id');

  const [projects, setProjects] = useState<AdminProjectItem[]>([]);
  const [pagination, setPagination] = useState<PaginationDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    listAdminProjects({
      page,
      page_size: 20,
      user_id: filterUserId ?? undefined,
    })
      .then(data => {
        setProjects(data.items);
        setPagination(data.pagination);
      })
      .catch(e => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false));
  }, [page, filterUserId]);

  useEffect(load, [load]);

  const clearFilter = () => {
    router.push('/admin/projects');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-black text-gray-900 flex items-center gap-2">
          <FolderOpen size={20} /> 项目管理
        </h2>
      </div>

      {filterUserId && (
        <div className="flex items-center gap-2 text-sm font-bold text-gray-600">
          <span>筛选: 用户</span>
          <span className="font-mono rounded bg-[var(--banana-blue)] px-2 py-0.5 text-xs text-white">
            {filterUserId}
          </span>
          <button
            onClick={clearFilter}
            className="ml-1 rounded-full p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-700"
          >
            <X size={14} />
          </button>
        </div>
      )}

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
              <div className="h-6 w-64 rounded bg-gray-200" />
            </div>
          ))}
        </div>
      )}

      {!loading && !error && projects.length === 0 && (
        <EmptyState
          icon={<FolderOpen size={64} />}
          title="暂无项目"
          description={filterUserId ? '该用户还没有项目' : '还没有任何项目'}
        />
      )}

      {!error && projects.length > 0 && (
        <div className="space-y-3">
          {projects.map(project => (
            <div key={project.id} className="banana-card p-4">
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-gray-900" title={project.name}>
                    {project.name}
                  </p>
                  <div className="mt-1 flex items-center gap-3 text-xs text-gray-400">
                    <span className="font-mono rounded bg-gray-100 px-1.5 py-0.5">
                      {project.user_id}
                    </span>
                    <span>创建于 {new Date(project.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <a
                    href={`/preview?id=${project.id}&page=1`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 rounded-lg border-2 border-gray-300 px-3 py-1.5 text-xs font-bold text-gray-600 transition-colors hover:border-gray-900 hover:text-gray-900"
                  >
                    <Eye size={14} />
                    预览
                  </a>
                  <button
                    onClick={() => router.push(`/admin/logs/${project.id}`)}
                    className="flex items-center gap-1 rounded-lg border-2 border-gray-300 px-3 py-1.5 text-xs font-bold text-gray-600 transition-colors hover:border-gray-900 hover:text-gray-900"
                  >
                    <FileText size={14} />
                    日志
                  </button>
                </div>
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
