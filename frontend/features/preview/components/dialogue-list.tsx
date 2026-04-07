import { useEffect, useMemo, useState } from 'react';
import {
  DIALOGUE_EMOTIONS,
  DIALOGUE_ROLES,
  DIALOGUE_SPEEDS,
  type Dialogue,
} from '@/features/projects/types';
import { Trash2, ChevronUp, ChevronDown, Plus, X, Edit2, Check } from 'lucide-react';
import { getEmotionDisplay, getSpeedDisplay } from '../utils';

interface DialogueListProps {
  dialogues: Dialogue[];
  isBusy: boolean;
  onAdd: () => Promise<Dialogue | null>;
  onUpdate: (dialogue: Dialogue) => Promise<boolean>;
  onDelete: (dialogueId: string) => Promise<boolean>;
  onMove: (dialogueId: string, direction: -1 | 1) => Promise<boolean>;
}

export function DialogueList({
  dialogues,
  isBusy,
  onAdd,
  onUpdate,
  onDelete,
  onMove,
}: DialogueListProps) {
  const [editingDialogueId, setEditingDialogueId] = useState<string | null>(null);
  const [draftDialogue, setDraftDialogue] = useState<Dialogue | null>(null);

  useEffect(() => {
    if (!editingDialogueId) {
      return;
    }

    const current = dialogues.find(dialogue => dialogue.id === editingDialogueId);
    if (!current) {
      setEditingDialogueId(null);
      setDraftDialogue(null);
      return;
    }

    setDraftDialogue(current);
  }, [dialogues, editingDialogueId]);

  const canSave = useMemo(() => {
    return Boolean(draftDialogue?.content.trim()) && !isBusy;
  }, [draftDialogue, isBusy]);

  const startEdit = (dialogue: Dialogue) => {
    setEditingDialogueId(dialogue.id);
    setDraftDialogue(dialogue);
  };

  const cancelEdit = () => {
    setEditingDialogueId(null);
    setDraftDialogue(null);
  };

  const handleSave = async () => {
    if (!draftDialogue) {
      return;
    }

    const success = await onUpdate(draftDialogue);
    if (success) {
      cancelEdit();
    }
  };

  const handleAdd = async () => {
    const createdDialogue = await onAdd();
    if (createdDialogue) {
      startEdit(createdDialogue);
    }
  };

  return (
    <aside className="min-h-0 rounded-[28px] border-4 border-gray-900 bg-white shadow-[8px_8px_0px_rgba(0,0,0,1)]">
      <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-[24px]">
        <div className="border-b-2 border-gray-900 bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-black text-gray-900">对话展示框</h3>
            </div>
            <button
              onClick={() => void handleAdd()}
              disabled={isBusy}
              className="flex items-center gap-2 rounded-2xl border-2 border-[var(--banana-blue)] px-3 py-2 text-sm font-bold text-[var(--banana-blue)] hover:bg-blue-50 disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400"
            >
              <Plus size={16} />
              添加对话
            </button>
          </div>
        </div>
        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto bg-[#F8FBFF] p-4">
          {dialogues.map((dialogue, index) => {
            const isEditing = editingDialogueId === dialogue.id;
            const activeDialogue = isEditing && draftDialogue ? draftDialogue : dialogue;
            const emotion = getEmotionDisplay(activeDialogue.emotion);
            const speed = getSpeedDisplay(activeDialogue.speed);

            return (
              <div
                key={dialogue.id}
                className="rounded-2xl border-2 border-gray-200 bg-white p-4 shadow-sm transition-colors hover:border-gray-300"
              >
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    {isEditing ? (
                      <>
                        <select
                          value={activeDialogue.role}
                          onChange={event =>
                            setDraftDialogue(prev =>
                              prev
                                ? { ...prev, role: event.target.value as Dialogue['role'] }
                                : prev
                            )
                          }
                          className="text-sm font-bold text-[var(--banana-blue)] border border-gray-300 rounded-lg px-2 py-1"
                        >
                          {DIALOGUE_ROLES.map(role => (
                            <option key={role} value={role}>
                              {role}
                            </option>
                          ))}
                        </select>
                        <select
                          value={activeDialogue.emotion || '无明显情感'}
                          onChange={event =>
                            setDraftDialogue(prev =>
                              prev
                                ? { ...prev, emotion: event.target.value as Dialogue['emotion'] }
                                : prev
                            )
                          }
                          className="text-xs border border-gray-300 rounded-full px-2 py-1 text-gray-700"
                        >
                          {DIALOGUE_EMOTIONS.map(item => (
                            <option key={item} value={item}>
                              {getEmotionDisplay(item).emoji} {item}
                            </option>
                          ))}
                        </select>
                        <select
                          value={activeDialogue.speed || '中速'}
                          onChange={event =>
                            setDraftDialogue(prev =>
                              prev
                                ? { ...prev, speed: event.target.value as Dialogue['speed'] }
                                : prev
                            )
                          }
                          className="text-xs border border-gray-300 rounded-full px-2 py-1 text-gray-700"
                        >
                          {DIALOGUE_SPEEDS.map(item => (
                            <option key={item} value={item}>
                              {item}
                            </option>
                          ))}
                        </select>
                      </>
                    ) : (
                      <>
                        <span className="rounded-lg border border-gray-300 px-2 py-1 text-sm font-bold text-[var(--banana-blue)]">
                          {activeDialogue.role}
                        </span>
                        <span className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded-full border border-gray-200 flex items-center gap-1">
                          {emotion.emoji} {emotion.label}
                        </span>
                        <span
                          className={`text-xs px-2 py-1 rounded-full border ${speed.className} flex items-center gap-1`}
                        >
                          {speed.label}
                        </span>
                      </>
                    )}
                  </div>
                  <div className="flex items-center gap-1 self-start text-gray-400">
                    <button
                      onClick={() => void onMove(dialogue.id, -1)}
                      className="p-1 hover:text-gray-700 rounded hover:bg-gray-100"
                      disabled={index === 0 || isBusy}
                      title="上移"
                    >
                      <ChevronUp size={16} />
                    </button>
                    <button
                      onClick={() => void onMove(dialogue.id, 1)}
                      className="p-1 hover:text-gray-700 rounded hover:bg-gray-100"
                      disabled={index === dialogues.length - 1 || isBusy}
                      title="下移"
                    >
                      <ChevronDown size={16} />
                    </button>
                    {isEditing ? (
                      <>
                        <button
                          onClick={() => void handleSave()}
                          disabled={!canSave}
                          className="p-1 rounded hover:bg-green-100 text-green-600 disabled:text-gray-300 disabled:cursor-not-allowed"
                          title="保存"
                        >
                          <Check size={16} />
                        </button>
                        <button
                          onClick={cancelEdit}
                          disabled={isBusy}
                          className="p-1 rounded hover:bg-gray-100 text-gray-600 disabled:text-gray-300 disabled:cursor-not-allowed"
                          title="取消"
                        >
                          <X size={16} />
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => startEdit(dialogue)}
                        disabled={isBusy}
                        className="p-1 hover:text-gray-700 rounded hover:bg-gray-100 disabled:text-gray-300 disabled:cursor-not-allowed"
                        title="编辑"
                      >
                        <Edit2 size={16} />
                      </button>
                    )}
                    <button
                      onClick={() => void onDelete(dialogue.id)}
                      className="p-1 hover:text-[var(--banana-red)] rounded hover:bg-red-50"
                      disabled={isBusy}
                      title="删除"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                {isEditing ? (
                  <textarea
                    value={activeDialogue.content}
                    onChange={event =>
                      setDraftDialogue(prev =>
                        prev ? { ...prev, content: event.target.value } : prev
                      )
                    }
                    rows={4}
                    className="w-full resize-none rounded-lg border border-gray-300 p-2 text-sm leading-relaxed text-gray-800"
                    placeholder="请输入对话内容"
                  />
                ) : (
                  <div className="rounded-xl border border-gray-200 bg-gray-50 p-3 text-sm leading-6 text-gray-800">
                    {dialogue.content || '当前对话暂无内容'}
                  </div>
                )}
              </div>
            );
          })}

          {dialogues.length === 0 && (
            <div className="rounded-2xl border-2 border-dashed border-gray-300 bg-white p-6 text-center text-gray-500">
              当前页暂无对话，请点击“生成对话”或“添加对话”开始编辑。
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
