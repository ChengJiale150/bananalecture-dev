import type { Dialogue } from '@/features/projects/types';

export * from './preview-cache';

export function createClientId() {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function getEmotionDisplay(emotion?: string) {
  switch (emotion) {
    case '开心的':
      return { emoji: '😊', label: '开心的' };
    case '悲伤的':
      return { emoji: '😢', label: '悲伤的' };
    case '生气的':
      return { emoji: '😠', label: '生气的' };
    case '害怕的':
      return { emoji: '😨', label: '害怕的' };
    case '惊讶的':
      return { emoji: '😲', label: '惊讶的' };
    default:
      return { emoji: '😐', label: '无明显情感' };
  }
}

export function getSpeedDisplay(speed?: string) {
  switch (speed) {
    case '慢速':
      return { label: '慢速', className: 'bg-blue-50 text-blue-700 border-blue-200' };
    case '快速':
      return { label: '快速', className: 'bg-orange-50 text-orange-700 border-orange-200' };
    default:
      return { label: '中速', className: 'bg-green-50 text-green-700 border-green-200' };
  }
}

export function normalizeDialogues(dialogues: any[]): Dialogue[] {
  return dialogues.map((dialogue, idx) => ({
    id: dialogue?.id || `${Date.now()}-${idx}`,
    role: dialogue?.role || '旁白',
    content: dialogue?.content || '',
    emotion: dialogue?.emotion || '无明显情感',
    speed: dialogue?.speed || '中速',
    audioPath: dialogue?.audioPath,
  }));
}

export function reorderDialoguesLocally(
  dialogues: Dialogue[],
  dialogueId: string,
  direction: -1 | 1
) {
  const index = dialogues.findIndex(dialogue => dialogue.id === dialogueId);
  const targetIndex = index + direction;
  if (index < 0 || targetIndex < 0 || targetIndex >= dialogues.length) {
    return dialogues;
  }

  const next = [...dialogues];
  const current = next[index];
  next[index] = next[targetIndex];
  next[targetIndex] = current;
  return next;
}

export function upsertDialogue(dialogues: Dialogue[], nextDialogue: Dialogue) {
  const index = dialogues.findIndex(dialogue => dialogue.id === nextDialogue.id);
  if (index < 0) {
    return [...dialogues, nextDialogue];
  }

  return dialogues.map(dialogue => (dialogue.id === nextDialogue.id ? nextDialogue : dialogue));
}

export function removeDialogueById(dialogues: Dialogue[], dialogueId: string) {
  return dialogues.filter(dialogue => dialogue.id !== dialogueId);
}
