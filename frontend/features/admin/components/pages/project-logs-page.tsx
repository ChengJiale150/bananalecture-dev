'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useBasePath } from '@/contexts/base-path-context';
import {
  ScrollText,
  ArrowLeft,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
} from 'lucide-react';
import Pagination from '@/features/admin/components/shared/pagination';
import EmptyState from '@/features/admin/components/shared/empty-state';
import { getProjectLogs } from '@/features/admin/api';
import type { LogEntry } from '@/features/admin/types';

const LEVEL_STYLES: Record<string, string> = {
  ERROR: 'bg-[var(--banana-red)] text-white',
  WARNING: 'bg-[var(--banana-yellow)] text-gray-900',
  INFO: 'bg-[var(--banana-blue)] text-white',
  DEBUG: 'bg-gray-300 text-gray-700',
};

const LEVELS = ['all', 'DEBUG', 'INFO', 'WARNING', 'ERROR'];

export default function ProjectLogsPage() {
  const params = useParams();
  const router = useRouter();
  const { basePath } = useBasePath();
  const projectId = params.projectId as string;

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const [filters, setFilters] = useState({
    level: 'all',
    event: '',
    startTime: '',
    endTime: '',
  });
  const [appliedFilters, setAppliedFilters] = useState(filters);

  const buildQuery = useCallback(
    (off: number) => ({
      level: appliedFilters.level !== 'all' ? appliedFilters.level : undefined,
      event: appliedFilters.event || undefined,
      start_time: appliedFilters.startTime || undefined,
      end_time: appliedFilters.endTime || undefined,
      limit,
      offset: off,
      order: 'desc' as const,
    }),
    [appliedFilters]
  );

  const load = useCallback(
    (off: number) => {
      setLoading(true);
      setError(null);
      getProjectLogs(projectId, buildQuery(off))
        .then(data => {
          setLogs(data.items);
          setTotal(data.total);
        })
        .catch(e => setError(e instanceof Error ? e.message : '加载失败'))
        .finally(() => setLoading(false));
    },
    [projectId, buildQuery]
  );

  useEffect(() => {
    load(offset);
  }, [load, offset]);

  const applyFilters = () => {
    setAppliedFilters(filters);
    setOffset(0);
  };

  const resetFilters = () => {
    setFilters({ level: 'all', event: '', startTime: '', endTime: '' });
    setAppliedFilters({ level: 'all', event: '', startTime: '', endTime: '' });
    setOffset(0);
  };

  const copyJson = (entry: LogEntry, idx: number) => {
    navigator.clipboard.writeText(JSON.stringify(entry, null, 2));
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const page = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push(`${basePath}/admin/projects`)}
          className="flex items-center gap-1 rounded-lg border-2 border-gray-300 px-3 py-1.5 text-xs font-bold text-gray-600 transition-colors hover:border-gray-900 hover:text-gray-900"
        >
          <ArrowLeft size={14} />
          返回项目列表
        </button>
        <h2 className="text-lg font-black text-gray-900 flex items-center gap-2">
          <ScrollText size={20} /> 项目日志
        </h2>
        <span className="font-mono rounded bg-gray-200 px-2 py-0.5 text-xs text-gray-600">
          {projectId}
        </span>
      </div>

      <div className="banana-card p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs font-bold text-gray-500">级别</label>
            <select
              value={filters.level}
              onChange={e => setFilters(f => ({ ...f, level: e.target.value }))}
              className="rounded-lg border-2 border-gray-300 px-3 py-1.5 text-xs font-bold text-gray-700 outline-none focus:border-[var(--banana-blue)]"
            >
              {LEVELS.map(l => (
                <option key={l} value={l.toLowerCase()}>{l}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-bold text-gray-500">事件搜索</label>
            <input
              type="text"
              value={filters.event}
              onChange={e => setFilters(f => ({ ...f, event: e.target.value }))}
              placeholder="事件名称前缀..."
              className="rounded-lg border-2 border-gray-300 px-3 py-1.5 text-xs font-mono outline-none focus:border-[var(--banana-blue)] w-48"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-bold text-gray-500">开始时间</label>
            <input
              type="datetime-local"
              value={filters.startTime}
              onChange={e => setFilters(f => ({ ...f, startTime: e.target.value }))}
              className="rounded-lg border-2 border-gray-300 px-3 py-1.5 text-xs outline-none focus:border-[var(--banana-blue)]"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-bold text-gray-500">结束时间</label>
            <input
              type="datetime-local"
              value={filters.endTime}
              onChange={e => setFilters(f => ({ ...f, endTime: e.target.value }))}
              className="rounded-lg border-2 border-gray-300 px-3 py-1.5 text-xs outline-none focus:border-[var(--banana-blue)]"
            />
          </div>
          <button onClick={applyFilters} className="banana-btn banana-btn-primary text-xs">
            应用筛选
          </button>
          <button onClick={resetFilters} className="banana-btn text-xs border-gray-400 text-gray-600">
            重置
          </button>
        </div>
        {total > 0 && (
          <p className="mt-2 text-xs font-bold text-gray-400">
            筛选命中: {total} 条
          </p>
        )}
      </div>

      {error && (
        <div className="banana-card border-[var(--banana-red)] p-6 text-center">
          <AlertCircle size={32} className="mx-auto mb-2 text-[var(--banana-red)]" />
          <p className="mb-3 font-bold text-gray-700">{error}</p>
          <button onClick={() => load(offset)} className="banana-btn banana-btn-primary">
            重试
          </button>
        </div>
      )}

      {loading && !error && (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={32} className="animate-spin text-[var(--banana-blue)]" />
        </div>
      )}

      {!loading && !error && logs.length === 0 && (
        <EmptyState
          icon={<ScrollText size={64} />}
          title="暂无日志"
          description="该项目还没有日志记录"
        />
      )}

      {!error && logs.length > 0 && (
        <div className="banana-card overflow-hidden">
          <div className="divide-y-2 divide-gray-100">
            {logs.map((entry, idx) => {
              const globalIdx = offset + idx;
              const isExpanded = expandedId === globalIdx;
              return (
                <div key={globalIdx}>
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : globalIdx)}
                    className={`flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50 ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}`}
                  >
                    <span className="shrink-0 text-gray-400">
                      {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </span>
                    <span className="shrink-0 font-mono text-xs text-gray-500 w-44">
                      {entry.timestamp}
                    </span>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-bold ${
                        LEVEL_STYLES[entry.level] ?? 'bg-gray-200 text-gray-700'
                      }`}
                    >
                      {entry.level}
                    </span>
                    <span className="min-w-0 flex-1 truncate font-mono text-xs font-bold text-gray-800">
                      {entry.event || entry.message}
                    </span>
                    <span className="shrink-0 font-mono text-[10px] text-gray-400">
                      {entry.file ? `${entry.file}:${entry.line ?? ''}` : ''}
                    </span>
                  </button>
                  {isExpanded && (
                    <div className="border-t border-gray-100 bg-gray-50 px-4 py-4">
                      <div className="mb-3 space-y-1">
                        <span className="text-xs font-bold text-gray-400">消息</span>
                        <p className="font-mono text-xs text-gray-700 break-all">
                          {entry.message}
                        </p>
                      </div>
                      {Object.keys(entry.context).length > 0 && (
                        <div className="mb-3">
                          <span className="text-xs font-bold text-gray-400">上下文</span>
                          <div className="mt-1 grid grid-cols-1 gap-1 sm:grid-cols-2">
                            {Object.entries(entry.context).map(([key, value]) => (
                              <div
                                key={key}
                                className="rounded bg-white px-2 py-1 border border-gray-200"
                              >
                                <span className="text-[10px] font-bold text-gray-400">{key}</span>
                                <p className="truncate font-mono text-xs text-gray-700">
                                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      <button
                        onClick={() => copyJson(entry, globalIdx)}
                        className="flex items-center gap-1 text-xs font-bold text-gray-500 hover:text-gray-700"
                      >
                        {copiedIdx === globalIdx ? (
                          <Check size={14} className="text-green-600" />
                        ) : (
                          <Copy size={14} />
                        )}
                        {copiedIdx === globalIdx ? '已复制' : '复制 JSON'}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {total > 0 && (
        <div className="flex justify-center">
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            isLoading={loading}
            onPageChange={p => setOffset((p - 1) * limit)}
          />
        </div>
      )}
    </div>
  );
}
