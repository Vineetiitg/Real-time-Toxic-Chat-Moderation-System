import React from 'react';
import { Hash, Users, Search } from 'lucide-react';

interface HeaderProps {
  channelId: string;
  wsStatus: 'connecting' | 'connected' | 'disconnected';
}

export default function Header({ channelId, wsStatus }: HeaderProps) {
  const statusConfig = {
    connected: { color: 'bg-emerald-500', ring: 'ring-emerald-500/20', text: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'Online' },
    connecting: { color: 'bg-amber-500', ring: 'ring-amber-500/20', text: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Connecting...' },
    disconnected: { color: 'bg-slate-400', ring: 'ring-slate-400/20', text: 'text-slate-600', bg: 'bg-slate-100', border: 'border-slate-200', label: 'Offline' },
  }[wsStatus];

  return (
    <div className="px-5 py-3 border-b border-slate-200/80 flex items-center justify-between bg-white/80 backdrop-blur-sm z-10">
      <div>
        <h2 className="text-[15px] font-bold text-slate-800 flex items-center gap-1.5">
          <Hash className="w-4 h-4 text-slate-400" />
          {channelId}
        </h2>
        <p className="text-[11px] text-slate-400 mt-0.5">
          Protected by Hing-RoBERTa + Gemini 2.5 Flash Intent-Preserving Style Transfer
        </p>
      </div>
      <div className="flex items-center gap-2">
        <div className={`flex items-center gap-1.5 text-[11px] ${statusConfig.text} ${statusConfig.bg} px-2.5 py-1 rounded-full font-semibold border ${statusConfig.border}`}>
          <span className={`w-2 h-2 rounded-full ${statusConfig.color} ${wsStatus === 'connected' ? 'animate-pulse' : ''}`} />
          {statusConfig.label}
        </div>
      </div>
    </div>
  );
}

