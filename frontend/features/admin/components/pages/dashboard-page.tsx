'use client';

import { useEffect, useState } from 'react';
import {
  Users,
  FolderOpen,
  Presentation,
  MessageSquare,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import StatsCard from '@/features/admin/components/stats-card';
import EmptyState from '@/features/admin/components/shared/empty-state';
import { getDashboardStats } from '@/features/admin/api';
import type { AdminDashboardStats } from '@/features/admin/types';

const STATUS_KEYS = ['pending', 'running', 'completed', 'failed', 'cancelled'] as const;

const STATUS_LABELS: Record<string, string> = {
  pending: '待处理',
  running: '运行中',
  completed: '已完成',
  failed: '已失败',
  cancelled: '已取消',
};

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-400',
  running: 'bg-[var(--banana-blue)]',
  completed: 'bg-green-500',
  failed: 'bg-[var(--banana-red)]',
  cancelled: 'bg-[var(--banana-yellow)]',
};

export default function DashboardPage() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    getDashboardStats()
      .then(setStats)
      .catch(e => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (error) {
    return (
      <div className="banana-card border-[var(--banana-red)] p-8 text-center">
        <AlertCircle size={48} className="mx-auto mb-4 text-[var(--banana-red)]" />
        <p className="mb-4 font-bold text-gray-700">{error}</p>
        <button onClick={load} className="banana-btn banana-btn-primary">
          重试
        </button>
      </div>
    );
  }

  if (loading && !stats) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="banana-card p-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 animate-pulse rounded-full bg-gray-200" />
              <div className="flex-1 space-y-2">
                <div className="h-3 w-16 animate-pulse rounded bg-gray-200" />
                <div className="h-8 w-20 animate-pulse rounded bg-gray-200" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!stats) return null;

  const taskTotal = stats.tasks.total;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatsCard icon={<Users size={24} />} label="总用户" value={stats.total_users} />
        <StatsCard icon={<FolderOpen size={24} />} label="总项目" value={stats.total_projects} />
        <StatsCard icon={<Presentation size={24} />} label="总幻灯片" value={stats.total_slides} />
        <StatsCard
          icon={<MessageSquare size={24} />}
          label="总对话"
          value={stats.total_dialogues}
        />
      </div>

      <div className="banana-card p-6">
        <h2 className="mb-6 text-lg font-black text-gray-900">任务状态分布</h2>
        <div className="space-y-4">
          {STATUS_KEYS.map(status => {
            const label = STATUS_LABELS[status];
            const count = stats.tasks[status];
            const pct = taskTotal > 0 ? (count / taskTotal) * 100 : 0;
            return (
              <div key={status}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2 font-bold text-gray-700">
                    <span
                      className={`inline-block h-3 w-3 rounded-sm ${
                        STATUS_COLORS[status]
                      }`}
                    />
                    {label}
                  </span>
                  <span className="font-mono text-sm font-bold text-gray-500">{count}</span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-gray-100">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      STATUS_COLORS[status]
                    }`}
                    style={{ width: `${Math.max(pct, 2)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
        <p className="mt-4 text-right text-xs font-bold text-gray-400">总计: {taskTotal}</p>
      </div>
    </div>
  );
}
