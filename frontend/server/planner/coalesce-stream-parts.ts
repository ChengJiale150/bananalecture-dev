import type { StreamTextTransform, TextStreamPart, ToolSet } from 'ai';

/**
 * Providers stream tool arguments and text token by token. Every model-stream part becomes
 * one UI message chunk, and every UI chunk commits a new `messages` snapshot inside
 * `useChat`, re-rendering the whole planning workspace. A four-slide plan can produce
 * thousands of deltas, which makes React outrun its own commit cycle
 * ("Maximum update depth exceeded" from `useSyncExternalStore`).
 *
 * Merging consecutive deltas of the same kind and id keeps the streamed preview while
 * cutting the chunk count by one to two orders of magnitude.
 */
type DeltaKind = 'text' | 'reasoning' | 'tool-input';

interface DeltaDescriptor {
  kind: DeltaKind;
  /** Stream part field that carries the payload. */
  field: 'text' | 'delta';
  /** Buffer key: deltas are only merged while the kind and the id match. */
  key: string;
  length: number;
}

export const DEFAULT_COALESCE_FLUSH_LENGTH = 60;

/**
 * The part shape is handled loosely here (AI SDK unions) and narrowed again at the boundary
 * of {@link coalesceStreamDeltas}, which is generic over the agent's tool set.
 */
type StreamPart = TextStreamPart<ToolSet>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function describeDelta(part: StreamPart): DeltaDescriptor | null {
  if (!isRecord(part)) {
    return null;
  }

  const { type, id } = part as { type?: unknown; id?: unknown };
  if (typeof id !== 'string') {
    return null;
  }

  if (type === 'text-delta' && typeof (part as { text?: unknown }).text === 'string') {
    const text = (part as { text: string }).text;
    return { kind: 'text', field: 'text', key: `text:${id}`, length: text.length };
  }

  if (type === 'reasoning-delta' && typeof (part as { text?: unknown }).text === 'string') {
    const text = (part as { text: string }).text;
    return { kind: 'reasoning', field: 'text', key: `reasoning:${id}`, length: text.length };
  }

  if (type === 'tool-input-delta' && typeof (part as { delta?: unknown }).delta === 'string') {
    const delta = (part as { delta: string }).delta;
    return { kind: 'tool-input', field: 'delta', key: `tool-input:${id}`, length: delta.length };
  }

  return null;
}

/**
 * Concatenates the incoming delta onto the buffered one. The incoming part is the base so
 * that the newest ids/provider metadata survive; only the payload is accumulated.
 */
export function mergeStreamDeltas(buffered: StreamPart, incoming: StreamPart): StreamPart {
  const descriptor = describeDelta(incoming);
  if (!descriptor) {
    return incoming;
  }

  const bufferedPayload = (buffered as unknown as Record<string, unknown>)[descriptor.field];
  const incomingPayload = (incoming as unknown as Record<string, unknown>)[descriptor.field];

  return {
    ...(incoming as object),
    [descriptor.field]: `${typeof bufferedPayload === 'string' ? bufferedPayload : ''}${
      typeof incomingPayload === 'string' ? incomingPayload : ''
    }`,
  } as StreamPart;
}

export interface CoalesceStreamDeltasOptions {
  /** Flush the buffered delta once it holds this many characters. */
  flushLength?: number;
}

/**
 * `experimental_transform` for `streamText`, applied before the model stream is converted
 * into UI message chunks. Ordering is preserved: the buffer is flushed before any other
 * part (for example `text-end` or `tool-input-available`) is forwarded.
 */
export function coalesceStreamDeltas<TOOLS extends ToolSet = ToolSet>({
  flushLength = DEFAULT_COALESCE_FLUSH_LENGTH,
}: CoalesceStreamDeltasOptions = {}): StreamTextTransform<TOOLS> {
  return () => {
    let buffered: StreamPart | null = null;
    let bufferedKey = '';
    let bufferedLength = 0;

    const flushBuffered = (controller: TransformStreamDefaultController<StreamPart>) => {
      if (buffered) {
        controller.enqueue(buffered);
        buffered = null;
      }
      bufferedKey = '';
      bufferedLength = 0;
    };

    return new TransformStream<StreamPart, StreamPart>({
      transform(part, controller) {
        const descriptor = describeDelta(part);

        if (!descriptor) {
          flushBuffered(controller);
          controller.enqueue(part);
          return;
        }

        if (buffered && bufferedKey === descriptor.key) {
          buffered = mergeStreamDeltas(buffered, part);
          bufferedLength += descriptor.length;
        } else {
          flushBuffered(controller);
          buffered = part;
          bufferedKey = descriptor.key;
          bufferedLength = descriptor.length;
        }

        if (bufferedLength >= flushLength) {
          flushBuffered(controller);
        }
      },
      flush(controller) {
        flushBuffered(controller);
      },
    }) as unknown as TransformStream<TextStreamPart<TOOLS>, TextStreamPart<TOOLS>>;
  };
}
