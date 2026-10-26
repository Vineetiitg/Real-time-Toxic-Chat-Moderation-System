/**
 * SafeChat Frontend — Environment & Dynamic Configuration
 *
 * Automatically resolves API and WebSocket URLs from the current browser origin.
 * Works seamlessly whether hosted on localhost, EC2 public IP, custom domain, or behind a reverse proxy.
 */

// If running in browser, dynamically use current window location origin & host
export const API_BASE_URL: string = (
  typeof window !== 'undefined'
    ? window.location.origin
    : (import.meta.env.VITE_API_URL || 'http://localhost:8000')
);

export const WS_BASE_URL: string = (
  typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
    : (import.meta.env.VITE_WS_URL || 'ws://localhost:8000')
);

export const getWsChatUrl = (
  channelId: string = 'general',
  token?: string | null,
  userId?: string,
  userName?: string
): string => {
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
