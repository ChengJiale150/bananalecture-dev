import test from 'node:test';
import assert from 'node:assert/strict';
import type { TextStreamPart, ToolSet } from 'ai';
import {
  DEFAULT_COALESCE_FLUSH_LENGTH,
  coalesceStreamDeltas,
  mergeStreamDeltas,
} from '@/server/planner/coalesce-stream-parts';

type StreamPart = TextStreamPart<ToolSet>;

async function runTransform(parts: StreamPart[], flushLength?: number) {
  const transform = coalesceStreamDeltas(flushLength === undefined ? {} : { flushLength })({
    tools: {},
    stopStream: () => {},
  });

  const writer = transform.writable.getWriter();
  const collected: StreamPart[] = [];

  const reading = (async () => {
    const reader = transform.readable.getReader();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        return;
      }
      collected.push(value);
    }
  })();

  for (const part of parts) {
    await writer.write(part);
  }
  await writer.close();
  await reading;

  return collected;
}

function textOf(parts: StreamPart[]) {
  return parts
    .map(part =>
      part.type === 'text-delta' || part.type === 'reasoning-delta'
        ? part.text
        : part.type === 'tool-input-delta'
          ? part.delta
          : ''
    )
    .join('');
}

test('coalesceStreamDeltas merges consecutive tool argument deltas without losing content', async () => {
  const json = JSON.stringify({ slides: [{ title: '标题', content: '内容'.repeat(40) }] });
  const deltas: StreamPart[] = [];
  for (let index = 0; index < json.length; index += 4) {
    deltas.push({
      type: 'tool-input-delta',
      id: 'call-1',
      delta: json.slice(index, index + 4),
    } as StreamPart);
  }

  const output = await runTransform([
    { type: 'tool-input-start', id: 'call-1', toolName: 'create_ppt_plan' } as StreamPart,
    ...deltas,
    { type: 'tool-input-end', id: 'call-1' } as StreamPart,
  ]);

  const merged = output.filter(part => part.type === 'tool-input-delta');
  assert.ok(merged.length > 1, 'expected the stream to stay incremental');
  assert.ok(
    merged.length < deltas.length,
    `expected fewer chunks than the ${deltas.length} raw deltas, got ${merged.length}`
  );
  assert.equal(textOf(output), json);

  const startIndex = output.findIndex(part => part.type === 'tool-input-start');
  const endIndex = output.findIndex(part => part.type === 'tool-input-end');
  assert.equal(startIndex, 0);
  assert.equal(endIndex, output.length - 1);
  assert.ok(
    merged.every((_, index) => output.indexOf(merged[index]) < endIndex),
    'merged deltas must be flushed before tool-input-end'
  );
});

test('coalesceStreamDeltas flushes around other parts and keeps ordering per id', async () => {
  const output = await runTransform([
    { type: 'text-start', id: 'a' } as StreamPart,
    { type: 'text-delta', id: 'a', text: 'hello ' } as StreamPart,
    { type: 'reasoning-start', id: 'r' } as StreamPart,
    { type: 'reasoning-delta', id: 'r', text: 'think ' } as StreamPart,
    { type: 'text-delta', id: 'a', text: 'world' } as StreamPart,
    { type: 'text-end', id: 'a' } as StreamPart,
  ]);

  assert.deepEqual(
    output.map(part => part.type),
    ['text-start', 'text-delta', 'reasoning-start', 'reasoning-delta', 'text-delta', 'text-end']
  );
  assert.equal(
    (output[1] as { text: string }).text,
    'hello ',
    'a pending delta must be flushed before another kind starts'
  );
  assert.equal((output[4] as { text: string }).text, 'world');
});

test('coalesceStreamDeltas flushes once the buffer reaches the configured length', async () => {
  const output = await runTransform(
    [
      { type: 'text-start', id: 'a' } as StreamPart,
      { type: 'text-delta', id: 'a', text: 'x'.repeat(4) } as StreamPart,
      { type: 'text-delta', id: 'a', text: 'y'.repeat(4) } as StreamPart,
      { type: 'text-delta', id: 'a', text: 'z'.repeat(4) } as StreamPart,
      { type: 'text-end', id: 'a' } as StreamPart,
    ],
    8
  );

  const deltas = output.filter(part => part.type === 'text-delta');
  assert.equal(deltas.length, 2);
  assert.equal((deltas[0] as { text: string }).text, 'xxxxyyyy');
  assert.equal((deltas[1] as { text: string }).text, 'zzzz');
});

test('coalesceStreamDeltas still merges everything when the payload stays under the threshold', async () => {
  assert.equal(DEFAULT_COALESCE_FLUSH_LENGTH, 60);

  const output = await runTransform([
    { type: 'text-start', id: 'a' } as StreamPart,
    { type: 'text-delta', id: 'a', text: 'one ' } as StreamPart,
    { type: 'text-delta', id: 'a', text: 'two ' } as StreamPart,
    { type: 'text-delta', id: 'a', text: 'three' } as StreamPart,
    { type: 'text-end', id: 'a' } as StreamPart,
  ]);

  const deltas = output.filter(part => part.type === 'text-delta');
  assert.equal(deltas.length, 1);
  assert.equal((deltas[0] as { text: string }).text, 'one two three');
});

test('mergeStreamDeltas keeps the incoming part fields and accumulates the payload', () => {
  const merged = mergeStreamDeltas(
    { type: 'text-delta', id: 'a', text: 'foo' } as StreamPart,
    {
      type: 'text-delta',
      id: 'a',
      text: 'bar',
      providerMetadata: { source: { step: 1 } },
    } as StreamPart
  );

  assert.deepEqual(merged, {
    type: 'text-delta',
    id: 'a',
    text: 'foobar',
    providerMetadata: { source: { step: 1 } },
  });

  const toolInput = mergeStreamDeltas(
    { type: 'tool-input-delta', id: 'call-1', delta: '{"a"' } as StreamPart,
    { type: 'tool-input-delta', id: 'call-1', delta: ':1}' } as StreamPart
  );
  assert.deepEqual(toolInput, { type: 'tool-input-delta', id: 'call-1', delta: '{"a":1}' });
});
