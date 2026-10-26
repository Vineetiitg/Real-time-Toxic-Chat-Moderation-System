import React from 'react';
import { ChatMessage } from '../../stores/chatStore';
import { SeverityBadge } from '../common/Badge';
import {
  ShieldAlert,
  AlertTriangle,
  Sparkles,
  Globe,
} from 'lucide-react';

interface MessageBubbleProps {
  msg: ChatMessage;
  isMe: boolean;
}

const avatarGradients = [
  'from-indigo-500 to-purple-600',
  'from-emerald-500 to-teal-600',
  'from-amber-500 to-orange-600',
  'from-rose-500 to-pink-600',
  'from-cyan-500 to-blue-600',
];

function getAvatarGradient(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarGradients[Math.abs(hash) % avatarGradients.length];
}

export default function MessageBubble({ msg, isMe }: MessageBubbleProps) {
  const isBlocked = msg.status === 'BLOCKED';
  const isFlagged = msg.status === 'FLAGGED';
  const wasRewritten = msg.moderation?.suggestion && msg.content === msg.moderation.suggestion;
  const grad = getAvatarGradient(msg.senderName);

  return (
    <div className={`flex gap-2.5 animate-msg-enter ${isMe ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full bg-gradient-to-br ${grad} text-white flex items-center justify-center text-xs font-bold shrink-0 shadow-sm`}
      >
        {msg.senderName[0]?.toUpperCase() || '?'}
      </div>

      {/* Content */}
      <div className={`max-w-[72%] ${isMe ? 'items-end' : 'items-start'} flex flex-col`}>
        {/* Meta row */}
        <div className={`flex items-center gap-2 mb-1 px-1 ${isMe ? 'flex-row-reverse' : ''}`}>
          <span className="text-xs font-semibold text-slate-600">{msg.senderName}</span>
          <span className="text-[10px] text-slate-400">
            {new Date(msg.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          {msg.moderation?.detectedLanguage && (
            <span className="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded-md border border-slate-200">
              <Globe className="w-2.5 h-2.5" />
              {msg.moderation.detectedLanguage}
            </span>
          )}
          {wasRewritten && (
            <span className="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded-md border border-indigo-200">
              <Sparkles className="w-2.5 h-2.5" />
              AI Rewritten
            </span>
          )}
        </div>

        {/* Bubble */}
        {isBlocked ? (
          <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 shadow-sm">
            <div className="flex items-start gap-2">
              <div className="w-7 h-7 rounded-full bg-rose-100 flex items-center justify-center shrink-0">
                <ShieldAlert className="w-4 h-4 text-rose-500" />
              </div>
              <div>
                <p className="font-semibold text-xs text-rose-700">Message Blocked by Safety Policy</p>
                <p className="text-[11px] text-rose-500 mt-0.5">
                  Content was classified as severely toxic and cannot be displayed.
                </p>
                {msg.moderation?.severity && (
                  <div className="mt-2">
                    <SeverityBadge severity={msg.moderation.severity} />
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div
            className={`p-3.5 rounded-2xl text-sm shadow-sm relative group transition-shadow duration-200 hover:shadow-md ${
              isFlagged
                ? 'bg-amber-50 border border-amber-200 text-amber-900'
                : isMe
                ? 'bg-indigo-600 text-white rounded-br-sm'
                : 'bg-white border border-slate-200/80 text-slate-800 rounded-bl-sm'
            }`}
          >
            <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

            {isFlagged && (
              <div className="mt-2.5 pt-2 border-t border-amber-200 flex items-center gap-1.5 text-xs text-amber-700 font-medium">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                Flagged for moderator review
                {msg.moderation?.severity && (
                  <span className="ml-auto">
                    <SeverityBadge severity={msg.moderation.severity} />
                  </span>
                )}
              </div>
            )}

            {/* Hover tooltip with categories */}
            {msg.moderation?.categories && Object.keys(msg.moderation.categories).length > 0 && (
              <div className="absolute bottom-full left-0 mb-1 hidden group-hover:block z-20 animate-scale-in">
                <div className="bg-slate-900 text-white text-[10px] rounded-lg px-3 py-2 shadow-lg whitespace-nowrap">
                  <p className="font-bold mb-1 text-slate-300">Moderation Scores</p>
                  {Object.entries(msg.moderation.categories).map(([cat, score]) => (
                    <div key={cat} className="flex justify-between gap-4">
                      <span className="text-slate-400">{cat}:</span>
                      <span className="font-mono">{(score as number).toFixed(3)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

