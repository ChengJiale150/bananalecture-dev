'use client';

import { BrainCircuit } from 'lucide-react';

/**
 * Optimistic "Agent" bubble rendered the moment the user submits a message.
 *
 * The AI SDK only adds the assistant message once the response stream starts, so without
 * this placeholder the transcript sits on the user's message until the first token —
 * which can be many seconds for a PPT planning request.
 */
export default function PendingAgentMessage({ label = 'thinking...' }: { label?: string }) {
  return (
    <div className="flex flex-col items-start" data-testid="pending-agent-message">
      <div className="max-w-[90%] rounded-2xl rounded-bl-none border-2 border-gray-900 bg-white px-6 py-4 text-gray-900 shadow-[4px_4px_0px_rgba(0,0,0,1)] transition-all lg:max-w-[80%]">
        <div className="mb-2 text-xs font-bold uppercase tracking-wide text-[var(--banana-blue)]">
          Agent
        </div>

        <div
          role="status"
          aria-live="polite"
          className="flex items-center gap-2 py-1 text-sm font-medium text-gray-500"
        >
          <BrainCircuit size={16} className="animate-pulse text-[var(--banana-blue)]" />
          <span>{label}</span>
          <span className="flex items-end gap-1" aria-hidden="true">
            {[0, 1, 2].map(index => (
              <span
                key={index}
                className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--banana-blue)]"
                style={{ animationDelay: `${index * 150}ms` }}
              />
            ))}
          </span>
        </div>
      </div>
    </div>
  );
}
