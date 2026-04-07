import { Sparkles } from 'lucide-react';

export function EmptyState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center">
      <div className="bg-white p-12 rounded-full border-4 border-gray-900 shadow-[8px_8px_0px_rgba(0,0,0,1)] mb-8">
        <Sparkles size={64} className="text-[var(--banana-blue)]" />
      </div>
      <h2 className="text-3xl font-black text-gray-900 mb-4">工作空间</h2>
      <p className="text-lg text-gray-600">暂无 PPT 规划数据，请先返回创建规划</p>
    </div>
  );
}
