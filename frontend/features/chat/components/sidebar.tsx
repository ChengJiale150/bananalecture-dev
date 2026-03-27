import {
  MessageSquare,
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  Settings,
  GraduationCap,
  User,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from 'lucide-react';
import { useMemo, useState, type MouseEvent } from 'react';
import { getVisiblePaginationPages } from '@/features/projects/utils';

interface ProjectSummaryItem {
  id: string;
  title: string;
  createdAt: number;
}

interface SidebarProps {
  projects: ProjectSummaryItem[];
  currentProjectId: string | null;
  currentPage: number;
  totalPages: number;
  isLoadingProjects: boolean;
  isLoadingProjectDetail: boolean;
  onSelect: (id: string) => void;
  onPageChange: (page: number) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, newTitle: string) => Promise<void>;
}

export default function Sidebar({
  projects,
  currentProjectId,
  currentPage,
  totalPages,
  isLoadingProjects,
  isLoadingProjectDetail,
  onSelect,
  onPageChange,
  onNew,
  onDelete,
  onRename,
}: SidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);
  const [isRenaming, setIsRenaming] = useState(false);

  const visiblePages = useMemo(
    () => getVisiblePaginationPages(currentPage, totalPages),
    [currentPage, totalPages]
  );

  const startEditing = (project: ProjectSummaryItem, e: MouseEvent) => {
    e.stopPropagation();
    setEditingId(project.id);
    setEditTitle(project.title);
  };

  const saveEdit = async (e?: MouseEvent) => {
    e?.stopPropagation();

    if (!editingId || !editTitle.trim() || isRenaming) {
      return;
    }

    setIsRenaming(true);
    try {
      await onRename(editingId, editTitle.trim());
      setEditingId(null);
      setEditTitle('');
    } finally {
      setIsRenaming(false);
    }
  };

  const cancelEdit = (e: MouseEvent) => {
    e.stopPropagation();
    if (isRenaming) return;
    setEditingId(null);
    setEditTitle('');
  };

  return (
    <div
      className={`${isExpanded ? 'w-72' : 'w-20'} bg-[var(--doraemon-blue)] text-white flex flex-col h-screen border-r-4 border-gray-800 shadow-[4px_0px_0px_rgba(0,0,0,0.2)] z-10 relative transition-all duration-300`}
    >
      <div
        className={`${isExpanded ? 'p-6' : 'p-4'} border-b-4 border-gray-800 bg-white text-gray-900 flex flex-row items-center justify-center gap-4`}
      >
        <div className="w-12 h-12 bg-[var(--doraemon-yellow)] rounded-full border-4 border-gray-900 flex items-center justify-center shadow-[4px_4px_0px_rgba(0,0,0,1)]">
          <GraduationCap size={isExpanded ? 28 : 20} className="text-gray-900" />
        </div>
        {isExpanded && (
          <h1
            className="text-xl font-black tracking-tight"
            style={{ textShadow: '2px 2px 0px #ddd' }}
          >
            Banana Lecture
          </h1>
        )}
      </div>

      <div
        className={`${isExpanded ? 'p-4' : 'p-2'} border-b-4 border-gray-800 bg-[var(--doraemon-blue)]`}
      >
        <button
          onClick={onNew}
          className={`w-full flex items-center justify-center gap-2 doraemon-btn doraemon-btn-danger ${isExpanded ? '' : 'aspect-square'}`}
          title={isExpanded ? '' : 'New Project'}
        >
          <Plus size={20} strokeWidth={3} />
          {isExpanded && <span>New Project</span>}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-[#e6f7ff]">
        {isExpanded && (
          <div className="flex items-center justify-between rounded-xl border-2 border-gray-900 bg-white px-3 py-2 text-xs font-bold text-gray-600 shadow-[2px_2px_0px_rgba(0,0,0,1)]">
            <span>项目列表</span>
            <span>
              第 {currentPage} / {Math.max(totalPages, 1)} 页
            </span>
          </div>
        )}

        {isLoadingProjects && isExpanded ? (
          <div className="flex items-center justify-center gap-2 text-sm font-bold text-gray-500 py-8">
            <Loader2 size={16} className="animate-spin" />
            <span>加载项目中...</span>
          </div>
        ) : null}

        {!isLoadingProjects && projects.length === 0 && isExpanded ? (
          <div className="text-gray-500 font-bold text-sm text-center mt-8">No projects yet!</div>
        ) : null}

        {projects.map(project => (
          <div
            key={project.id}
            className={`
              group flex items-center justify-between p-3 rounded-xl border-2 cursor-pointer transition-all
              ${
                currentProjectId === project.id
                  ? 'bg-white border-gray-900 shadow-[4px_4px_0px_rgba(0,0,0,1)] translate-x-[-2px] translate-y-[-2px]'
                  : 'bg-white/80 border-transparent hover:border-gray-900 hover:shadow-[2px_2px_0px_rgba(0,0,0,0.5)]'
              }
            `}
            onClick={() => onSelect(project.id)}
            title={isExpanded ? project.title : ''}
          >
            <div
              className={`flex items-center gap-3 overflow-hidden flex-1 text-gray-800 ${!isExpanded ? 'justify-center' : ''}`}
            >
              {currentProjectId === project.id && isLoadingProjectDetail ? (
                <Loader2 size={18} className="shrink-0 animate-spin text-[var(--doraemon-blue)]" />
              ) : (
                <MessageSquare
                  size={18}
                  className={`shrink-0 ${currentProjectId === project.id ? 'text-[var(--doraemon-blue)]' : 'text-gray-400'}`}
                />
              )}

              {isExpanded &&
                (editingId === project.id ? (
                  <div
                    className="flex items-center gap-1 flex-1"
                    onClick={e => e.stopPropagation()}
                  >
                    <input
                      className="bg-white text-gray-900 text-xs p-1 rounded w-full outline-none border-2 border-[var(--doraemon-blue)]"
                      value={editTitle}
                      onChange={e => setEditTitle(e.target.value)}
                      autoFocus
                      disabled={isRenaming}
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          void saveEdit();
                        }
                        if (e.key === 'Escape') {
                          setEditingId(null);
                        }
                      }}
                    />
                    <button
                      onClick={e => void saveEdit(e)}
                      className="text-green-600 hover:text-green-500 bg-green-100 p-1 rounded border border-green-600"
                      disabled={isRenaming}
                    >
                      <Check size={14} />
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="text-red-600 hover:text-red-500 bg-red-100 p-1 rounded border border-red-600"
                      disabled={isRenaming}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col overflow-hidden flex-1">
                    <span
                      className={`text-sm truncate font-bold ${currentProjectId === project.id ? 'text-gray-900' : 'text-gray-600'}`}
                      title={project.title}
                    >
                      {project.title || 'Untitled'}
                    </span>
                    <span className="text-[10px] text-gray-400 font-medium">
                      {new Date(project.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                ))}
            </div>

            {isExpanded && !editingId && (
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={e => startEditing(project, e)}
                  className="p-1 hover:bg-blue-100 text-gray-500 rounded"
                  title="Rename project"
                >
                  <Edit2 size={14} />
                </button>
                <button
                  onClick={e => {
                    e.stopPropagation();
                    onDelete(project.id);
                  }}
                  className="p-1 hover:bg-red-100 text-gray-500 rounded"
                  title="Delete project"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {isExpanded && totalPages > 1 ? (
        <div className="border-t-4 border-gray-800 bg-white px-3 py-3">
          <div className="flex items-center justify-between gap-2">
            <button
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage <= 1 || isLoadingProjects}
              className="rounded-lg border-2 border-gray-900 px-3 py-1 text-xs font-bold text-gray-700 disabled:cursor-not-allowed disabled:border-gray-200 disabled:text-gray-300"
            >
              上一页
            </button>
            <div className="flex items-center gap-1">
              {visiblePages.map(page => (
                <button
                  key={page}
                  onClick={() => onPageChange(page)}
                  disabled={isLoadingProjects}
                  className={`min-w-8 rounded-lg border-2 px-2 py-1 text-xs font-bold transition-colors ${
                    page === currentPage
                      ? 'border-gray-900 bg-[var(--doraemon-blue)] text-white'
                      : 'border-gray-300 bg-white text-gray-700 hover:border-gray-900'
                  }`}
                >
                  {page}
                </button>
              ))}
            </div>
            <button
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage >= totalPages || isLoadingProjects}
              className="rounded-lg border-2 border-gray-900 px-3 py-1 text-xs font-bold text-gray-700 disabled:cursor-not-allowed disabled:border-gray-200 disabled:text-gray-300"
            >
              下一页
            </button>
          </div>
        </div>
      ) : null}

      {isExpanded && (
        <div className="p-4 border-t-4 border-gray-800 bg-white text-gray-900">
          <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
            Configuration
          </div>
          <div className="space-y-2">
            <button className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-gray-100 border-2 border-transparent hover:border-gray-200 transition-colors">
              <span className="flex items-center gap-2 font-bold text-sm">
                <Settings size={16} />
                Settings
              </span>
            </button>
          </div>
        </div>
      )}

      <div
        className={`${isExpanded ? 'p-4' : 'p-2'} border-t-4 border-gray-800 bg-gray-50 text-gray-900`}
      >
        <button
          className={`w-full flex items-center ${isExpanded ? 'justify-between' : 'justify-center'} p-3 rounded-xl hover:bg-white border-2 border-transparent hover:border-gray-300 transition-all shadow-sm`}
        >
          <span className={`flex items-center ${isExpanded ? 'gap-3' : ''} font-bold text-sm`}>
            <div className="w-8 h-8 bg-[var(--doraemon-blue)] rounded-full flex items-center justify-center">
              <User size={16} className="text-white" />
            </div>
            {isExpanded && <span>User</span>}
          </span>
        </button>
      </div>

      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-12 bg-white border-2 border-gray-800 rounded-r-lg shadow-lg hover:bg-gray-50 transition-colors flex items-center justify-center z-20"
      >
        {isExpanded ? (
          <ChevronLeft size={14} className="text-gray-700" />
        ) : (
          <ChevronRight size={14} className="text-gray-700" />
        )}
      </button>
    </div>
  );
}
