import { useState, useRef, useEffect } from 'react';
import { Send, Square, Layers, Users, Palette } from 'lucide-react';

export interface ChatOptions {
  pageCount: string;
  audience: string;
  style: string;
}

export default function ChatInput({
  status,
  onSubmit,
  stop,
  isCentered = false,
}: {
  status: string;
  onSubmit: (text: string, options?: ChatOptions) => void;
  stop?: () => void;
  isCentered?: boolean;
}) {
  const [text, setText] = useState('');
  const [pageCount, setPageCount] = useState('5-10');
  const [audience, setAudience] = useState('beginner');
  const [style, setStyle] = useState('multi_panel');
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const minRows = isCentered ? 8 : 2;
  const maxHeight = isCentered ? 400 : 200;

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, maxHeight)}px`;
    }
  }, [text, maxHeight]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (text.trim() === '') return;
    
    if (isCentered) {
      onSubmit(text, {
        pageCount,
        audience,
        style
      });
    } else {
      onSubmit(text);
    }
    
    setText('');
    if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !isCentered) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const containerClassName = isCentered
    ? 'w-full'
    : 'w-full pt-4 pb-6 px-4 bg-[#F0F8FF]';

  const selectClassName = "appearance-none bg-white border-2 border-gray-900 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2 pr-8 font-medium cursor-pointer hover:bg-gray-50 transition-colors shadow-[2px_2px_0px_rgba(0,0,0,1)] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none";

  return (
    <div className={containerClassName}>
      <div className={`max-w-3xl mx-auto relative border-2 border-gray-900 rounded-2xl bg-white shadow-[4px_4px_0px_rgba(0,0,0,1)] focus-within:translate-x-[-1px] focus-within:translate-y-[-1px] focus-within:shadow-[6px_6px_0px_rgba(0,0,0,1)] transition-all p-3 ${isCentered ? 'flex flex-col gap-3' : 'flex items-end gap-3'}`}>
        
        {isCentered && (
          <div className="flex flex-wrap gap-3 pb-2 border-b-2 border-dashed border-gray-200 w-full">
            <div className="relative">
              <Layers className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500 pointer-events-none" />
              <select 
                value={pageCount}
                onChange={(e) => setPageCount(e.target.value)}
                className={`${selectClassName} pl-9`}
              >
                <option value="5-10">5-10页</option>
                <option value="10-15">10-15页</option>
                <option value="15+">15页以上</option>
              </select>
            </div>

            <div className="relative">
              <Users className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500 pointer-events-none" />
              <select 
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
                className={`${selectClassName} pl-9`}
              >
                <option value="beginner">初学者</option>
                <option value="intermediate">有基础</option>
                <option value="expert">精通</option>
              </select>
            </div>

            <div className="relative">
              <Palette className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500 pointer-events-none" />
              <select 
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                className={`${selectClassName} pl-9`}
              >
                <option value="multi_panel">多格动漫</option>
                <option value="colorful_comic">彩色漫画</option>
                <option value="flat">扁平插画</option>
              </select>
            </div>
          </div>
        )}

        <div className={`flex items-end gap-3 w-full ${isCentered ? '' : 'flex-1'}`}>
          <textarea
            ref={textareaRef}
            style={{ maxHeight: `${maxHeight}px` }}
            className="flex-1 bg-transparent outline-none resize-none py-2 px-2 text-sm md:text-base font-medium text-gray-800 placeholder-gray-400 overflow-y-auto"
            placeholder={isCentered ? "Describe the topic you want to learn about..." : "Ask Doraemon something..."}
            disabled={status !== 'ready' && status !== 'submitted'} 
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={minRows}
          />
          
          {status === 'streaming' || status === 'submitted' ? (
            <button
              onClick={stop}
              className="p-3 rounded-xl bg-[var(--doraemon-red)] text-white border-2 border-gray-900 hover:brightness-110 active:scale-95 transition-all shadow-[2px_2px_0px_rgba(0,0,0,1)]"
              title="Stop generating"
            >
              <Square size={20} fill="currentColor" />
            </button>
          ) : (
            <button
              onClick={() => handleSubmit()}
              disabled={!text.trim() || status !== 'ready'}
              className="p-3 rounded-xl bg-[var(--doraemon-blue)] text-white border-2 border-gray-900 hover:brightness-110 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-[2px_2px_0px_rgba(0,0,0,1)]"
              title="Send message"
            >
              <Send size={20} strokeWidth={3} />
            </button>
          )}
        </div>
      </div>

      {!isCentered && (
        <div className="text-center text-xs font-bold text-gray-400 mt-3 uppercase tracking-wider">
          Doraemon Agent can make mistakes. Check important info!
        </div>
      )}
    </div>
  );
}
