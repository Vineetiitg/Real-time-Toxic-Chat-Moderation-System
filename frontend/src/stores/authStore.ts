/**
 * SafeChat Frontend — Authentication State (Zustand)
 *
 * Manages JWT access tokens, authenticated user profile,
 * developer PIN unlocks, and public guest mode.
 */

import { create } from 'zustand';
import { API_BASE_URL } from '../config/env';

export interface UserProfile {
  id: string;
  email: string;
  displayName: string;
  role: 'DEVELOPER' | 'ADMIN' | 'USER' | 'GUEST';
}

interface AuthState {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  isDeveloper: () => boolean;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string, displayName: string) => Promise<boolean>;
  unlockWithPin: (pin: string) => boolean;
  logout: () => void;
  setDemoUser: (displayName: string) => void;
}

const TOKEN_KEY = 'safechat_jwt_token';
const USER_KEY = 'safechat_user_profile';

const GUEST_USER: UserProfile = {
  id: 'guest-' + Math.floor(1000 + Math.random() * 9000),
  email: 'guest@safechat.ai',
  displayName: 'Guest Visitor',
  role: 'GUEST',
};

const loadSavedAuth = (): { token: string | null; user: UserProfile | null } => {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const userStr = localStorage.getItem(USER_KEY);
    const user = userStr ? JSON.parse(userStr) : null;
    if (user && (user.role === 'DEVELOPER' || user.role === 'ADMIN')) {
      return { token, user };
    }
    if (token && user && user.role !== 'GUEST') {
      return { token, user };
    }
    return { token: null, user: GUEST_USER };
  } catch {
    return { token: null, user: GUEST_USER };
  }
};

const initialAuth = loadSavedAuth();

export const useAuthStore = create<AuthState>((set, get) => ({
  user: initialAuth.user || GUEST_USER,
  token: initialAuth.token,
  isAuthenticated: !!initialAuth.token && initialAuth.user?.role !== 'GUEST',
  isLoading: false,
  error: null,

  isDeveloper: (): boolean => {
    const u = get().user;
    if (!u) return false;
    return (
      u.role === 'DEVELOPER' ||
      u.role === 'ADMIN' ||
      u.email.toLowerCase() === 'vineettiwari971@gmail.com'
    );
  },

  unlockWithPin: (pin: string): boolean => {
    const cleanPin = pin.trim().toLowerCase();
    // Valid developer PINs for Vineet
    if (cleanPin === 'vineet2026' || cleanPin === 'vineet' || cleanPin === 'admin2026') {
      const devProfile: UserProfile = {
        id: 'c609aff0-f9c7-46e9-806c-7f4e3331d3dc',
        email: 'vineettiwari971@gmail.com',
        displayName: 'Vineet Tiwari',
        role: 'DEVELOPER',
      };
      const devToken = 'dev-verified-' + Date.now();
      localStorage.setItem(TOKEN_KEY, devToken);
      localStorage.setItem(USER_KEY, JSON.stringify(devProfile));
      set({
        user: devProfile,
        token: devToken,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      return true;
    }
    set({ error: 'Incorrect Developer PIN. Access restricted to Vineet.' });
    return false;
  },

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
      const isVineet = email.toLowerCase().includes('vineet');

      if (profileRes.ok) {
        const u = await profileRes.json();
        userProfile = {
          id: u.id,
          email: u.email,
          displayName: u.display_name,
          role: isVineet ? 'DEVELOPER' : (u.role || 'USER'),
        };
      } else {
        userProfile = {
          id: `user-${Date.now()}`,
          email,
          displayName: email.split('@')[0],
          role: isVineet ? 'DEVELOPER' : 'USER',
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
        const isVineet = email.toLowerCase().includes('vineet');
        const userProfile: UserProfile = {
          id: `user-${Date.now()}`,
          email,
          displayName,
          role: isVineet ? 'DEVELOPER' : 'USER',
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
      user: GUEST_USER,
      isAuthenticated: false,
      error: null,
    });
  },

  setDemoUser: (displayName: string) => {
    // Only allows switching to Guest profiles; never elevates to developer
    const guestUser: UserProfile = {
      id: `guest-${Math.floor(Math.random() * 1000)}`,
      email: `${displayName.toLowerCase().replace(/\s+/g, '')}@guest.safechat`,
      displayName,
      role: 'GUEST',
    };
    localStorage.setItem(USER_KEY, JSON.stringify(guestUser));
    set({ user: guestUser, isAuthenticated: false });
  },
}));
