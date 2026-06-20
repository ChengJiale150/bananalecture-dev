'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  isLoading: boolean;
  onPageChange: (page: number) => void;
}

function getVisiblePages(currentPage: number, totalPages: number): number[] {
  const pages: number[] = [];
  const start = Math.max(1, currentPage - 2);
  const end = Math.min(totalPages, currentPage + 2);
  for (let i = start; i <= end; i++) {
    pages.push(i);
  }
  return pages;
}

export default function Pagination({
  currentPage,
  totalPages,
  isLoading,
  onPageChange,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  const visiblePages = getVisiblePages(currentPage, totalPages);

  return (
    <div className="flex items-center justify-between gap-2">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1 || isLoading}
        className="rounded-lg border-2 border-gray-900 px-3 py-1 text-xs font-bold text-gray-700 disabled:cursor-not-allowed disabled:border-gray-200 disabled:text-gray-300"
      >
        <ChevronLeft size={14} className="inline mr-1" />
        上一页
      </button>
      <div className="flex items-center gap-1">
        {visiblePages.map(page => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            disabled={isLoading}
            className={`min-w-8 rounded-lg border-2 px-2 py-1 text-xs font-bold transition-colors ${
              page === currentPage
                ? 'border-gray-900 bg-[var(--banana-blue)] text-white'
                : 'border-gray-300 bg-white text-gray-700 hover:border-gray-900'
            }`}
          >
            {page}
          </button>
        ))}
      </div>
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages || isLoading}
        className="rounded-lg border-2 border-gray-900 px-3 py-1 text-xs font-bold text-gray-700 disabled:cursor-not-allowed disabled:border-gray-200 disabled:text-gray-300"
      >
        下一页
        <ChevronRight size={14} className="inline ml-1" />
      </button>
    </div>
  );
}
