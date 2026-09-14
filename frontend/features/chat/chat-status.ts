/**
 * Composer (chat input) status policy.
 *
 * The AI SDK reports `ready | submitted | streaming | error`. A failed request must
 * never leave the composer unusable: the user has to be able to read what happened,
 * type a new message and send it again.
 */

const DEFAULT_ERROR_TEXT = '对话请求失败，请检查网络或稍后重试。';
const MAX_ERROR_TEXT_LENGTH = 200;

export interface ComposerState {
  /** The textarea accepts input. */
  canType: boolean;
  /** The send button is enabled; requires non-empty text. */
  canSend: boolean;
  /** The stop button replaces the send button. */
  showStop: boolean;
  /** The last request failed, so the failure has to be surfaced to the user. */
  isFailed: boolean;
}

export function getComposerState(status: string, hasText: boolean): ComposerState {
  const isFailed = status === 'error';

  return {
    canType: status !== 'streaming',
    canSend: hasText && (status === 'ready' || isFailed),
    showStop: status === 'submitted' || status === 'streaming',
    isFailed,
  };
}

/** Minimal transcript shape needed to decide whether an assistant reply is on screen. */
export interface ChatMessageLike {
  role?: string;
}

/**
 * The optimistic "Agent / thinking..." bubble is needed exactly while a request is in
 * flight but no assistant message has been rendered yet.
 *
 * `useChat` only pushes the assistant message when the first stream chunk arrives, so
 * between `sendMessage()` and the first token the transcript would otherwise end on the
 * user's own message — leaving the user staring at a silent panel while the API warms up.
 */
export function shouldShowPendingAssistant(
  status: string,
  messages: readonly ChatMessageLike[]
): boolean {
  if (status !== 'submitted' && status !== 'streaming') {
    return false;
  }

  return messages[messages.length - 1]?.role !== 'assistant';
}

function clampErrorText(text: string) {
  return text.length > MAX_ERROR_TEXT_LENGTH ? `${text.slice(0, MAX_ERROR_TEXT_LENGTH)}…` : text;
}

function extractErrorMessage(payload: unknown) {
  if (!payload || typeof payload !== 'object') {
    return null;
  }

  const candidate = payload as { error?: unknown; message?: unknown; detail?: unknown };
  for (const value of [candidate.error, candidate.message, candidate.detail]) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }

  return null;
}

/**
 * The chat transport throws `new Error(await response.text())`, so the raw message can
 * be a JSON envelope, plain text or an HTML error page. Normalize it for display.
 */
export function getChatErrorText(error: unknown): string {
  if (!error) {
    return DEFAULT_ERROR_TEXT;
  }

  const raw = error instanceof Error ? error.message : String(error);
  const trimmed = raw.trim();
  if (!trimmed) {
    return DEFAULT_ERROR_TEXT;
  }

  const jsonStart = trimmed.indexOf('{');
  if (jsonStart !== -1) {
    try {
      const message = extractErrorMessage(JSON.parse(trimmed.slice(jsonStart)));
      if (message) {
        return clampErrorText(message);
      }
    } catch {
      // Not JSON — fall through to the raw text.
    }
  }

  if (trimmed.startsWith('<')) {
    return DEFAULT_ERROR_TEXT;
  }

  return clampErrorText(trimmed);
}
