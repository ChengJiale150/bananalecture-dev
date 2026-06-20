'use client';

import { usePathname } from 'next/navigation';
import { Shield } from 'lucide-react';
import type { ReactNode } from 'react';
import AdminSidebar from '@/features/admin/components/admin-sidebar';

const PAGE_TITLES: Record<string, string> = {
  '/admin': '仪表盘',
  '/admin/users': '用户管理',
  '/admin/projects': '项目管理',
  '/admin/logs': '系统日志',
};

export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  const isProjectLogs = pathname.startsWith('/admin/logs/');
  const title = isProjectLogs ? '项目日志' : (PAGE_TITLES[pathname] ?? 'Admin');

  return (
    <div className="flex h-screen overflow-hidden bg-[#F0F8FF]">
      <AdminSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 shrink-0 items-center gap-3 border-b-4 border-gray-800 bg-white px-6 shadow-sm">
          <Shield size={20} className="text-[var(--banana-blue)]" />
          <span className="text-lg font-black text-gray-900">{title}</span>
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
