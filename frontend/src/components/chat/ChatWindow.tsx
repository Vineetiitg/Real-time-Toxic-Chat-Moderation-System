import React, { useEffect, useState, useRef } from 'react';
import { useChatStore, ChatMessage } from '../../stores/chatStore';
import { useAuthStore } from '../../stores/authStore';
import { getWsChatUrl, API_BASE_URL } from '../../config/env';
import MessageBubble from './MessageBubble';
import Header from '../layout/Header';
import {
  Send,
  AlertTriangle,
  Sparkles,
  RefreshCw,
  X,
  ArrowDown,
  ShieldCheck,
  MessageSquare,
} from 'lucide-react';
import { SeverityBadge } from '../common/Badge';

interface ChatWindowProps {
  channelId: string;
  currentUserId: string;
  currentUserName: string;
}

export default function ChatWindow({ channelId, currentUserId, currentUserName }: ChatWindowProps) {
  const { messages, addMessage, updateMessageStatus, appendSuggestionChunk, fetchMessages, isLoadingHistory } = useChatStore();
  const token = useAuthStore(state => state.token);
  const [inputText, setInputText] = useState('');
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [isChecking, setIsChecking] = useState(false);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const [interceptedModal, setInterceptedModal] = useState<{
    originalText: string;
    isToxic: boolean;
    severity: string;
    categories?: Record<string, number>;
    detectedLanguage?: string;
    suggestion: string;
    isStreamingSuggestion: boolean;
  } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingTextRef = useRef<string>('');

  // Initial history load for this channel
  useEffect(() => {
    fetchMessages(channelId);
  }, [channelId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, interceptedModal]);

  // Track scroll position for "scroll to bottom" button
  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const onScroll = () => {
      const fromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      setShowScrollBtn(fromBottom > 200);
    };
    el.addEventListener('scroll', onScroll);
    return () => el.removeEventListener('scroll', onScroll);
  }, []);

  // Connect to WebSocket with token and channel query params
  useEffect(() => {
    let isCancelled = false;

    const connectWs = () => {
      if (isCancelled) return;
      setWsStatus('connecting');

      const wsUrl = getWsChatUrl(channelId, token, currentUserId, currentUserName);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (isCancelled) {
          ws.close();
          return;
        }
        setWsStatus('connected');
        console.log(`Connected to SafeChat WebSocket (${channelId})`);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);

          if (payload.type === 'classification') {
            setIsChecking(false);
            const data = payload.data;
            if (pendingTextRef.current) {
              if (data.is_toxic || data.severity === 'HIGH' || data.severity === 'MEDIUM') {
                // Intercept toxic message
                setInterceptedModal({
                  originalText: pendingTextRef.current,
                  isToxic: true,
                  severity: data.severity,
                  categories: data.categories,
                  detectedLanguage: data.detected_language,
                  suggestion: data.suggestion || '',
                  isStreamingSuggestion: true,
                });
              } else {
                // Clean message -> deliver immediately
                addMessage({
                  id: Date.now().toString(),
                  channelId,
                  senderId: currentUserId,
                  senderName: currentUserName,
                  content: pendingTextRef.current,
                  status: 'DELIVERED',
                  createdAt: new Date().toISOString(),
                  moderation: {
                    isToxic: false,
                    severity: 'SAFE',
                    detectedLanguage: data.detected_language,
                  },
                });
                pendingTextRef.current = '';
                setIsChecking(false);
              }
            }
          } else if (payload.type === 'detox_start') {
            setInterceptedModal(prev => prev ? { ...prev, isStreamingSuggestion: true } : null);
          } else if (payload.type === 'detox_chunk') {
            setInterceptedModal(prev => prev ? { ...prev, suggestion: prev.suggestion + payload.data.chunk } : null);
          } else if (payload.type === 'detox_end') {
            setIsChecking(false);
            setInterceptedModal(prev =>
              prev ? { ...prev, suggestion: payload.data.full_text, isStreamingSuggestion: false } : null
            );
          } else if (payload.type === 'new_message') {
            const msgData = payload.data;
            const isDup = useChatStore.getState().messages.some(
              m => m.content === msgData.content &&
                   m.senderId === msgData.sender_id &&
                   Math.abs(new Date(m.createdAt).getTime() - new Date(msgData.created_at || Date.now()).getTime()) < 3000
            );

            if (!isDup) {
              const mod = msgData.moderation || msgData.moderation_data;
              addMessage({
                id: msgData.id || msgData.message_id || Date.now().toString(),
                channelId: msgData.channel_id || channelId,
                senderId: msgData.sender_id,
                senderName: msgData.sender_name,
                content: msgData.content,
                status: msgData.status || 'DELIVERED',
                createdAt: msgData.created_at || new Date().toISOString(),
                moderation: mod
                  ? {
                      isToxic: mod.is_toxic,
                      severity: mod.severity,
                      detectedLanguage: mod.detected_language,
                      categories: mod.categories,
                      suggestion: mod.suggestion,
                    }
                  : undefined,
              });
            }
          }
        } catch (err) {
          console.error('WebSocket message parsing error:', err);
        }
      };

      ws.onclose = () => {
        if (!isCancelled) {
          setWsStatus('disconnected');
          setIsChecking(false);
          setTimeout(connectWs, 3000);
        }
      };

      ws.onerror = () => {
        if (!isCancelled) {
          setWsStatus('disconnected');
          setIsChecking(false);
        }
      };

      wsRef.current = ws;
    };

    connectWs();

    return () => {
      isCancelled = true;
      wsRef.current?.close();
    };
  }, [channelId, token, currentUserId, currentUserName]);

  // Handle message send
  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isChecking) return;

    const sentText = inputText.trim();
    pendingTextRef.current = sentText;
    if (interceptedModal) setInterceptedModal(null);
    setIsChecking(true);
    setInputText('');

    // Send through WebSocket if connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', text: sentText }));
    } else {
      // Fallback: REST moderation endpoint
      try {
        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE_URL}/api/v1/moderate`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            text: sentText,
            channel_id: channelId,
            user_id: currentUserId,
          }),
        });

        const mlResult = await res.json();
        setIsChecking(false);

        if (mlResult.is_toxic || mlResult.severity === 'HIGH' || mlResult.severity === 'MEDIUM') {
          setInterceptedModal({
            originalText: sentText,
            isToxic: true,
            severity: mlResult.severity,
            categories: mlResult.categories,
            detectedLanguage: mlResult.detected_language,
            suggestion: mlResult.suggestion || 'Let us keep the discussion respectful.',
            isStreamingSuggestion: false,
          });
        } else {
          addMessage({
            id: Date.now().toString(),
            channelId,
            senderId: currentUserId,
            senderName: currentUserName,
            content: sentText,
            status: 'DELIVERED',
            createdAt: new Date().toISOString(),
            moderation: {
              isToxic: false,
              severity: 'SAFE',
              detectedLanguage: mlResult.detected_language,
            },
          });
          pendingTextRef.current = '';
        }
      } catch (err) {
        console.error('REST moderation fallback failed:', err);
        setIsChecking(false);
      }
    }
  };

  const channelMessages = messages.filter(m => m.channelId === channelId || !m.channelId);

  return (
    <div className="flex flex-col h-full relative">
      {/* Channel Header */}
      <Header channelId={channelId} wsStatus={wsStatus} />

      {/* Messages Feed */}
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50/50">
        {isLoadingHistory && (
          <div className="text-center py-4">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow-sm border border-slate-200 text-xs text-slate-500">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-500" />
              Loading message history...
            </div>
          </div>
        )}

        {/* Empty state */}
        {channelMessages.length === 0 && !isLoadingHistory && (
          <div className="flex flex-col items-center justify-center h-full text-center py-16 animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-indigo-50 flex items-center justify-center mb-4">
              <MessageSquare className="w-8 h-8 text-indigo-400" />
            </div>
            <h3 className="text-base font-bold text-slate-700 mb-1">No messages yet</h3>
            <p className="text-sm text-slate-400 max-w-sm">
              Start the conversation! Messages are analyzed in real-time for toxicity across English, Hindi, and Hinglish.
            </p>
          </div>
        )}

        {channelMessages.map((msg) => (
          <MessageBubble
            key={msg.id}
            msg={msg}
            isMe={msg.senderId === currentUserId}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Scroll to bottom button */}
      {showScrollBtn && (
        <button
          onClick={() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })}
          className="absolute bottom-24 right-6 z-20 w-9 h-9 bg-white border border-slate-200 shadow-lg rounded-full flex items-center justify-center text-slate-500 hover:text-indigo-600 hover:border-indigo-300 transition-all animate-bounce-in"
        >
          <ArrowDown className="w-4 h-4" />
        </button>
      )}

      {/* Pre-Send Safety Interception Modal */}
      {interceptedModal && (
        <div className="absolute bottom-20 left-4 right-4 max-w-xl mx-auto z-30 animate-slide-up">
          <div className="bg-white border border-amber-200 shadow-2xl rounded-2xl overflow-hidden">
            {/* Modal header */}
            <div className="px-5 py-3.5 bg-gradient-to-r from-amber-50 to-orange-50 border-b border-amber-200 flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center text-amber-600 shadow-sm">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-800">
                    Content Safety Alert
                  </h3>
                  <div className="flex items-center gap-2 mt-0.5">
                    <SeverityBadge severity={interceptedModal.severity} />
                    {interceptedModal.detectedLanguage && (
                      <span className="text-[10px] text-slate-500">
                        Detected in {interceptedModal.detectedLanguage}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <button
                onClick={() => {
                  setInterceptedModal(null);
                  pendingTextRef.current = '';
                  setIsChecking(false);
                }}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-white/50 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-3">
              {/* Original message */}
              <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200">
                <span className="font-bold text-slate-400 text-[10px] uppercase tracking-wider">Your message</span>
                <p className="mt-1 italic text-slate-700">"{interceptedModal.originalText}"</p>
              </div>

              {/* AI Rewrite */}
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-700 mb-2">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
                  Intent-Preserving Polite Alternative
                </div>
                <p className="text-sm font-medium text-emerald-900 leading-relaxed">
                  {interceptedModal.suggestion || (
                    <span className="text-emerald-600 flex items-center gap-2 animate-pulse">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Generating rewrite via Gemini 2.5 Flash...
                    </span>
                  )}
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  onClick={() => {
                    setInterceptedModal(null);
                    pendingTextRef.current = '';
                    setIsChecking(false);
                  }}
                  className="px-4 py-2 text-xs text-slate-600 hover:bg-slate-100 rounded-xl font-semibold transition-all"
                >
                  Discard
                </button>
                <button
                  disabled={!interceptedModal.suggestion || interceptedModal.isStreamingSuggestion}
                  onClick={() => {
                    const safeRewrite = interceptedModal.suggestion;
                    setInterceptedModal(null);
                    pendingTextRef.current = '';
                    setIsChecking(false);

                    addMessage({
                      id: Date.now().toString(),
                      channelId,
                      senderId: currentUserId,
                      senderName: currentUserName,
                      content: safeRewrite,
                      status: 'DELIVERED',
                      createdAt: new Date().toISOString(),
                      moderation: { isToxic: false, severity: 'SAFE', suggestion: safeRewrite },
                    });

                    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                      wsRef.current.send(
                        JSON.stringify({
                          type: 'safe_message',
                          text: safeRewrite,
                          skip_moderation: true,
                        })
                      );
                    }
                  }}
                  className="flex items-center gap-1.5 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-600/20 transition-all active:scale-[0.97]"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Send Safe Version
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Input Bar */}
      <div className="p-4 bg-white border-t border-slate-200/80">
        <form onSubmit={handleSend} className="flex items-center gap-2.5 max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isChecking}
              placeholder={
                isChecking
                  ? '⚡ Evaluating message safety...'
                  : 'Type in English, Hinglish, or Hindi...'
              }
              className="w-full py-3 pl-4 pr-4 bg-slate-100 border border-slate-200 focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-2xl text-sm outline-none transition-all disabled:opacity-60"
            />
          </div>
          <button
            type="submit"
            disabled={!inputText.trim() || isChecking}
            className="p-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white rounded-2xl transition-all shadow-md shadow-indigo-600/20 active:scale-95"
          >
            {isChecking ? (
              <RefreshCw className="w-4.5 h-4.5 animate-spin" />
            ) : (
              <Send className="w-4.5 h-4.5" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
