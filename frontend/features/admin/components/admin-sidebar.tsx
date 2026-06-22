'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useBasePath } from '@/contexts/base-path-context';
import {
  LayoutDashboard,
  Users,
  FolderOpen,
  ScrollText,
  Shield,
  ArrowLeft,
} from 'lucide-react';

export default function AdminSidebar() {
  const pathname = usePathname();
  const { basePath } = useBasePath();

  const NAV_ITEMS = [
    { href: `${basePath}/admin`, label: '仪表盘', icon: LayoutDashboard },
    { href: `${basePath}/admin/users`, label: '用户管理', icon: Users },
    { href: `${basePath}/admin/projects`, label: '项目管理', icon: FolderOpen },
    { href: `${basePath}/admin/logs`, label: '系统日志', icon: ScrollText },
  ];

  return (
    <div className="flex w-60 shrink-0 flex-col bg-[var(--banana-blue)] text-white border-r-4 border-gray-800 shadow-[4px_0px_0px_rgba(0,0,0,0.2)]">
      <div className="flex items-center gap-3 border-b-4 border-gray-800 bg-white p-5 text-gray-900">
        <div className="flex h-10 w-10 items-center justify-center rounded-full border-4 border-gray-900 bg-[var(--banana-yellow)] shadow-[3px_3px_0px_rgba(0,0,0,1)]">
          <Shield size={20} className="text-gray-900" />
        </div>
        <span className="text-lg font-black tracking-tight" style={{ textShadow: '2px 2px 0px #ddd' }}>
          Admin Panel
        </span>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {NAV_ITEMS.map(item => {
          const isActive =
            item.href === `${basePath}/admin`
              ? pathname === `${basePath}/admin`
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-xl border-2 px-4 py-3 text-sm font-bold transition-all ${
                isActive
                  ? 'border-gray-900 bg-white text-gray-900 shadow-[4px_4px_0px_rgba(0,0,0,1)] translate-x-[-1px] translate-y-[-1px]'
                  : 'border-transparent text-white/80 hover:border-white/30 hover:bg-white/10 hover:text-white'
              }`}
            >
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t-4 border-gray-800 p-4">
        <Link
          href={basePath || '/'}
          className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-bold text-white/80 transition-all hover:bg-white/10 hover:text-white"
        >
          <ArrowLeft size={16} />
          返回主应用
        </Link>
      </div>
    </div>
  );
}
