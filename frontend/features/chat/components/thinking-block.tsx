'use client';

import { useEffect, useState } from 'react';
import { BrainCircuit, ChevronDown, ChevronRight } from 'lucide-react';

export function ThinkingBlock({ content, isComplete }: { content: string; isComplete?: boolean }) {
  const [isOpen, setIsOpen] = useState(true);

  useEffect(() => {
    if (isComplete) {
      setIsOpen(false);
    }
  }, [isComplete]);

  return (
    <div className="my-2 overflow-hidden rounded-lg border border-gray-200 bg-gray-50">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center gap-2 bg-gray-100 p-2 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-200"
      >
        {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <BrainCircuit size={14} />
        <span>Thinking Process</span>
      </button>

      {isOpen ? (
        <div className="border-t border-gray-200 bg-gray-50/50 p-3 font-mono text-sm whitespace-pre-wrap text-gray-600">
          {content}
        </div>
      ) : null}
    </div>
  );
}
