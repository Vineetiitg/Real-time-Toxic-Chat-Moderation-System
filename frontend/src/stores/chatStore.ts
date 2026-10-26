/**
 * SafeChat Frontend — Chat & Channel State (Zustand)
 *
 * Manages active channel, message list, streaming token appends,
 * and background history fetching.
 */

import { create } from 'zustand';
import { API_BASE_URL } from '../config/env';

export interface ChatMessage {
  id: string;
  channelId: string;
  senderId: string;
  senderName: string;
  content: string;
  status: 'PENDING' | 'DELIVERED' | 'BLOCKED' | 'FLAGGED';
  moderation?: {
    isToxic: boolean;
    severity: string;
    suggestion?: string;
    isStreamingSuggestion?: boolean;
    detectedLanguage?: string;
    categories?: Record<string, number>;
  };
  createdAt: string;
}

export interface ChannelItem {
  id: string;
  name: string;
  description?: string;
}

interface ChatState {
  currentChannel: string;
  channels: ChannelItem[];
  messages: ChatMessage[];
  isLoadingHistory: boolean;
  setChannel: (channelId: string) => void;
  fetchChannels: () => Promise<void>;
  fetchMessages: (channelId: string) => Promise<void>;
  addMessage: (msg: ChatMessage) => void;
  updateMessageStatus: (id: string, status: 'PENDING' | 'DELIVERED' | 'BLOCKED' | 'FLAGGED', moderation?: any) => void;
  appendSuggestionChunk: (id: string, chunk: string) => void;
  setMessages: (msgs: ChatMessage[]) => void;
}

const DEFAULT_CHANNELS: ChannelItem[] = [
  { id: 'general', name: 'general', description: 'Public discussion & live moderation' },
  { id: 'announcements', name: 'announcements', description: 'Important team updates' },
  { id: 'random', name: 'random', description: 'Casual conversations' },
];

export const useChatStore = create<ChatState>((set, get) => ({
  currentChannel: 'general',
  channels: DEFAULT_CHANNELS,
  messages: [
    {
      id: 'welcome-1',
      channelId: 'general',
      senderId: 'system-bot',
      senderName: 'SafeChat Safety Bot',
      content: 'Welcome! Messages in this room are protected by real-time multi-lingual moderation and intent-preserving style transfer. Try typing in English, Hinglish, or Hindi!',
      status: 'DELIVERED',
      createdAt: new Date(Date.now() - 60000).toISOString(),
      moderation: { isToxic: false, severity: 'SAFE', detectedLanguage: 'en' },
    },
  ],
  isLoadingHistory: false,

  setChannel: (channelId: string) => {
    set({ currentChannel: channelId });
    get().fetchMessages(channelId);
  },

  fetchChannels: async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/channels`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          set({
            channels: data.map((c: any) => ({
              id: c.name || c.id,
              name: c.name,
              description: c.description,
            })),
          });
        }
      }
    } catch {
      // Keep default channels if API is offline
    }
  },

  fetchMessages: async (channelId: string) => {
    set({ isLoadingHistory: true });
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/chat/messages/${channelId}?limit=50`);
      if (res.ok) {
        const docs = await res.json();
        if (Array.isArray(docs) && docs.length > 0) {
          const loaded: ChatMessage[] = docs.map((d: any) => {
            const mod = d.moderation;
            return {
              id: d.id || d.message_id || `msg-${Math.random()}`,
              channelId: d.channel_id || channelId,
              senderId: d.sender_id || 'unknown',
              senderName: d.sender_name || 'Anonymous',
              content: d.content,
              status: d.status || 'DELIVERED',
              createdAt: d.created_at || new Date().toISOString(),
              moderation: mod
                ? {
                    isToxic: mod.is_toxic,
                    severity: mod.severity,
                    detectedLanguage: mod.detected_language,
                    categories: mod.categories,
                    suggestion: mod.suggestion,
                  }
                : undefined,
            };
          });
          set({ messages: loaded, isLoadingHistory: false });
          return;
        }
      }
    } catch {
      // Fallback: keep existing messages
    }
    set({ isLoadingHistory: false });
  },

  addMessage: (msg: ChatMessage) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  setMessages: (msgs: ChatMessage[]) => set({ messages: msgs }),

  updateMessageStatus: (id, status, moderation) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, status, moderation: { ...m.moderation, ...moderation } } : m
      ),
    })),

  appendSuggestionChunk: (id: string, chunk: string) =>
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== id) return m;
        const currentSuggestion = m.moderation?.suggestion || '';
        return {
          ...m,
          moderation: {
            ...m.moderation!,
            suggestion: currentSuggestion + chunk,
            isStreamingSuggestion: true,
          },
        };
      }),
    })),
}));
