import React from 'react';

export default function TypingIndicator({ name }: { name?: string }) {
  return (
    <div className="flex items-start gap-2 animate-fade-in px-1">
      <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-500 shrink-0">
        {name ? name[0].toUpperCase() : '?'}
      </div>
      <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
        <div className="flex items-center gap-1">
          <span
            className="w-2 h-2 rounded-full bg-slate-400 animate-typing-dot"
            style={{ animationDelay: '0ms' }}
          />
          <span
            className="w-2 h-2 rounded-full bg-slate-400 animate-typing-dot"
            style={{ animationDelay: '200ms' }}
          />
          <span
            className="w-2 h-2 rounded-full bg-slate-400 animate-typing-dot"
            style={{ animationDelay: '400ms' }}
          />
        </div>
      </div>
    </div>
  );
}

