import type { ReactNode } from 'react';

interface StatsCardProps {
  icon: ReactNode;
  label: string;
  value: number | string;
  loading?: boolean;
}

export default function StatsCard({ icon, label, value, loading }: StatsCardProps) {
  return (
    <div className="banana-card p-6">
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-gray-900 bg-[var(--banana-yellow)] shadow-[2px_2px_0px_rgba(0,0,0,1)]">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-wide text-gray-500">{label}</p>
          {loading ? (
            <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-200" />
          ) : (
            <p className="text-3xl font-black text-gray-900">{value}</p>
          )}
        </div>
      </div>
    </div>
  );
}
