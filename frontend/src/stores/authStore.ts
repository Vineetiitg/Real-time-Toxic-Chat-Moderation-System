/**
 * SafeChat Frontend — Authentication State (Zustand)
 *
 * Manages JWT access tokens, authenticated user profile,
 * and quick guest demo sessions.
 */

import { create } from 'zustand';
import { API_BASE_URL } from '../config/env';

export interface UserProfile {
  id: string;
  email: string;
  displayName: string;
  role: string;
}

interface AuthState {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string, displayName: string) => Promise<boolean>;
  logout: () => void;
  setDemoUser: (displayName: string) => void;
}

const TOKEN_KEY = 'safechat_jwt_token';
const USER_KEY = 'safechat_user_profile';

const loadSavedAuth = (): { token: string | null; user: UserProfile | null } => {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const userStr = localStorage.getItem(USER_KEY);
    const user = userStr ? JSON.parse(userStr) : null;
    return { token, user };
  } catch {
    return { token: null, user: null };
  }
};

const initialAuth = loadSavedAuth();

export const useAuthStore = create<AuthState>((set) => ({
  user: initialAuth.user || {
    id: 'user-demo-123',
    email: 'vineet@safechat.ai',
    displayName: 'Vineet (Demo)',
    role: 'USER',
  },
  token: initialAuth.token,
  isAuthenticated: !!initialAuth.token,
  isLoading: false,
  error: null,

  login: async (email: string, password: string): Promise<boolean> => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Login failed. Please check your credentials.');
      }

      const tokenData = await res.json();
      const token = tokenData.access_token;

      // Fetch user profile
      const profileRes = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      let userProfile: UserProfile;
      if (profileRes.ok) {
        const u = await profileRes.json();
        userProfile = {
          id: u.id,
          email: u.email,
          displayName: u.display_name,
          role: u.role,
        };
      } else {
        userProfile = {
          id: `user-${Date.now()}`,
          email,
          displayName: email.split('@')[0],
          role: 'USER',
        };
      }

      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(userProfile));

      set({
        token,
        user: userProfile,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      return true;
    } catch (err: any) {
      set({ isLoading: false, error: err.message || 'Login failed' });
      return false;
    }
  },

  register: async (email: string, password: string, displayName: string): Promise<boolean> => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, display_name: displayName }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Registration failed.');
      }

      // Automatically log in after registration
      const loginRes = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (loginRes.ok) {
        const tokenData = await loginRes.json();
        const token = tokenData.access_token;
        const userProfile: UserProfile = {
          id: `user-${Date.now()}`,
          email,
          displayName,
          role: 'USER',
        };
        localStorage.setItem(TOKEN_KEY, token);
        localStorage.setItem(USER_KEY, JSON.stringify(userProfile));
        set({
          token,
          user: userProfile,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
        return true;
      }

      set({ isLoading: false, error: null });
      return true;
    } catch (err: any) {
      set({ isLoading: false, error: err.message || 'Registration failed' });
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    set({
      token: null,
      user: {
        id: `guest-${Math.floor(Math.random() * 1000)}`,
        email: 'guest@safechat.ai',
        displayName: 'Guest User',
        role: 'USER',
      },
      isAuthenticated: false,
      error: null,
    });
  },

  setDemoUser: (displayName: string) => {
    const demoUser: UserProfile = {
      id: `demo-${Math.floor(Math.random() * 1000)}`,
      email: `${displayName.toLowerCase().replace(/\s+/g, '')}@safechat.demo`,
      displayName,
      role: 'USER',
    };
    localStorage.setItem(USER_KEY, JSON.stringify(demoUser));
    set({ user: demoUser });
  },
}));

