import { Suspense } from 'react';
import { Loader2 } from 'lucide-react';
import AdminProjectsPage from '@/features/admin/components/pages/projects-page';

export default function AdminProjectsRoute() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-16">
          <Loader2 size={32} className="animate-spin text-[var(--banana-blue)]" />
        </div>
      }
    >
      <AdminProjectsPage />
    </Suspense>
  );
}
