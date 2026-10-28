import React, { useState } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { X, Lock, Mail, User, Shield, Eye, EyeOff, KeyRound, CheckCircle2 } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const { login, register, unlockWithPin, isLoading, error } = useAuthStore();
  const [authMode, setAuthMode] = useState<'pin' | 'account'>('pin');
  const [isRegisterMode, setIsRegisterMode] = useState(false);

  // PIN state
  const [pin, setPin] = useState('');
  const [pinError, setPinError] = useState<string | null>(null);

  // Account state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  if (!isOpen) return null;

  const handlePinSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPinError(null);
    if (!pin.trim()) {
      setPinError('Please enter the Developer PIN.');
      return;
    }
    const success = unlockWithPin(pin);
    if (success) {
      setPin('');
      onClose();
    } else {
      setPinError('Incorrect Developer PIN. Access restricted to Vineet.');
    }
  };

  const handleAccountSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isRegisterMode) {
      const ok = await register(email, password, displayName);
      if (ok) onClose();
    } else {
      const ok = await login(email, password);
      if (ok) onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden">
        {/* Header */}
        <div className="p-6 bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white relative overflow-hidden">
          <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full bg-indigo-500/10" />
          <div className="absolute -bottom-4 -left-4 w-20 h-20 rounded-full bg-emerald-500/10" />
          <div className="relative flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-indigo-500/20 border border-indigo-400/20 flex items-center justify-center">
                <Shield className="w-5 h-5 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-base font-bold">
                  {authMode === 'pin' ? 'Developer Access Gate' : isRegisterMode ? 'Create Account' : 'Account Sign In'}
                </h2>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  SafeChat Real-Time Platform
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="grid grid-cols-2 gap-1.5 mt-5 bg-white/10 p-1 rounded-xl">
            <button
              type="button"
              onClick={() => { setAuthMode('pin'); setPinError(null); }}
              className={`py-1.5 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                authMode === 'pin'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              Developer PIN
            </button>
            <button
              type="button"
              onClick={() => { setAuthMode('account'); setPinError(null); }}
              className={`py-1.5 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                authMode === 'account'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <Mail className="w-3.5 h-3.5" />
              Email & Password
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* PIN Mode */}
          {authMode === 'pin' && (
            <form onSubmit={handlePinSubmit} className="space-y-4">
              <div className="p-3 bg-indigo-50/70 border border-indigo-100 rounded-xl text-xs text-indigo-900 leading-relaxed">
                <p className="font-semibold text-slate-800">Vineet (Developer Authentication)</p>
                <p className="text-slate-600 mt-0.5">
                  Enter the developer passcode to unlock the <strong>Live Moderated Chat</strong> and <strong>Admin Dashboard</strong>.
                </p>
              </div>

              {pinError && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />
                  {pinError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Developer Passcode / PIN
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type="password"
                    autoFocus
                    required
                    value={pin}
                    onChange={(e) => setPin(e.target.value)}
                    placeholder="Enter Developer PIN (e.g. vineet2026)"
                    className="input-field pl-10"
                  />
                </div>
              </div>

              <button type="submit" className="btn-primary w-full py-2.5">
                Unlock Developer Session
              </button>

              <p className="text-[11px] text-center text-slate-400 pt-1">
                Other visitors can use the public <strong className="text-slate-600">Model Sandbox</strong> without authentication.
              </p>
            </form>
          )}

          {/* Account Mode */}
          {authMode === 'account' && (
            <form onSubmit={handleAccountSubmit} className="space-y-3.5">
              {error && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />
                  {error}
                </div>
              )}

              {isRegisterMode && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">Display Name</label>
                  <div className="relative">
                    <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                    <input
                      type="text"
                      required
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="e.g. Vineet Tiwari"
                      className="input-field pl-10"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Email</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="vineettiwari971@gmail.com"
                    className="input-field pl-10"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Password</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="input-field pl-10 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-3 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="btn-primary w-full mt-1 py-2.5"
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Authenticating...
                  </span>
                ) : (
                  isRegisterMode ? 'Create Account' : 'Sign In'
                )}
              </button>

              <div className="mt-3 text-center">
                <button
                  type="button"
                  onClick={() => setIsRegisterMode(!isRegisterMode)}
                  className="text-xs text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
                >
                  {isRegisterMode ? 'Already have an account? Sign In' : "Don't have an account? Register"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
