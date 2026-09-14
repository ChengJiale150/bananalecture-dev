'use client';

import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface PanelErrorBoundaryProps {
  /** Short label of the panel that failed, used in the fallback copy. */
  label: string;
  children: ReactNode;
}

interface PanelErrorBoundaryState {
  message: string | null;
}

/**
 * Keeps a render failure inside one panel from tearing down the whole workspace.
 * Without it, an error thrown while rendering the editor (for example a React
 * "Maximum update depth exceeded" caused by a state loop) unmounts the chat panel
 * as well, which leaves the user with a dead conversation and no explanation.
 */
export default class PanelErrorBoundary extends Component<
  PanelErrorBoundaryProps,
  PanelErrorBoundaryState
> {
  state: PanelErrorBoundaryState = { message: null };

  static getDerivedStateFromError(error: unknown): PanelErrorBoundaryState {
    return { message: error instanceof Error ? error.message : String(error) };
  }

  componentDidCatch(error: unknown, errorInfo: ErrorInfo) {
    console.error(`[${this.props.label}] render failed`, error, errorInfo.componentStack);
  }

  private handleReset = () => {
    this.setState({ message: null });
  };

  render() {
    if (this.state.message) {
      return (
        <div className="flex h-full items-center justify-center p-3">
          <div className="max-w-md rounded-2xl border-2 border-gray-900 bg-white p-6 text-center shadow-[6px_6px_0px_rgba(0,0,0,1)]">
            <div className="mb-3 flex justify-center">
              <AlertTriangle size={28} className="text-[var(--banana-red)]" />
            </div>
            <h3 className="text-lg font-black text-gray-900">{this.props.label}渲染失败</h3>
            <p className="mt-2 break-words text-sm font-medium text-gray-500">
              {this.state.message}
            </p>
            <button
              type="button"
              onClick={this.handleReset}
              className="mt-4 rounded-xl border-2 border-gray-900 bg-[var(--banana-blue)] px-4 py-2 text-sm font-bold text-white shadow-[3px_3px_0px_rgba(0,0,0,1)] transition-all hover:brightness-110 active:scale-95"
            >
              重新加载面板
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
