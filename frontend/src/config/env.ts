/**
 * SafeChat Frontend — Environment & Configuration
 *
 * Automatically resolves API and WebSocket URLs:
 * 1. From Vite env variables (VITE_API_URL, VITE_WS_URL)
 * 2. Or dynamically inferred from the browser host location
 */

const envApiUrl = import.meta.env.VITE_API_URL;
const envWsUrl = import.meta.env.VITE_WS_URL;

// Base HTTP API URL
export const API_BASE_URL: string = (
  envApiUrl && envApiUrl.trim()
    ? envApiUrl.replace(/\/+$/, '')
    : (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000')
);

// Base WebSocket URL
export const WS_BASE_URL: string = (
  envWsUrl && envWsUrl.trim()
    ? envWsUrl.replace(/\/+$/, '')
    : API_BASE_URL.replace(/^http/, 'ws')
);

export const getWsChatUrl = (channelId: string = 'general', token?: string | null, userId?: string, userName?: string): string => {
  const url = new URL(`${WS_BASE_URL}/ws/chat`);
  url.searchParams.set('channel', channelId);
  if (token) {
    url.searchParams.set('token', token);
  }
  if (userId) {
    url.searchParams.set('user_id', userId);
  }
  if (userName) {
    url.searchParams.set('user_name', userName);
  }
  return url.toString();
};

