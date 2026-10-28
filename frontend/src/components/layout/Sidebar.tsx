import React from 'react';
import { useChatStore, ChannelItem } from '../../stores/chatStore';
import { useAuthStore } from '../../stores/authStore';
import {
  MessageSquare,
  BarChart3,
  Hash,
  LogIn,
  LogOut,
  Shield,
  Menu,
  X,
  Sparkles,
  Lock,
  KeyRound,
} from 'lucide-react';

interface SidebarProps {
  activeTab: 'sandbox' | 'chat' | 'dashboard';
  setActiveTab: (tab: 'sandbox' | 'chat' | 'dashboard') => void;
  onOpenAuth: () => void;
  isMobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
}

export default function Sidebar({
  activeTab,
  setActiveTab,
  onOpenAuth,
  isMobileOpen,
  setMobileOpen,
}: SidebarProps) {
  const { user, isAuthenticated, logout, isDeveloper } = useAuthStore();
  const { currentChannel, channels, setChannel } = useChatStore();
  const devAccess = isDeveloper();

  const navAction = (tab: 'sandbox' | 'chat' | 'dashboard') => {
    setActiveTab(tab);
    setMobileOpen(false);
  };

  return (
    <>
      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 md:hidden animate-fade-in"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed md:relative z-50 md:z-auto w-64 h-full bg-slate-900 text-white flex flex-col justify-between shrink-0 transition-transform duration-300 ease-out ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div>
          {/* Brand */}
          <div className="p-4 border-b border-slate-800/80">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                  <Shield className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="font-extrabold text-[15px] tracking-tight flex items-center gap-1.5">
                    SafeChat
                    <span className="text-[9px] px-1.5 py-0.5 bg-emerald-500/20 text-emerald-400 font-bold rounded-md">
                      v3.0
                    </span>
                  </h1>
                  <p className="text-[10px] text-slate-500 font-medium">Real-Time Content Safety</p>
                </div>
              </div>
              <button
                onClick={() => setMobileOpen(false)}
                className="p-1 rounded-lg text-slate-500 hover:text-white hover:bg-slate-800 md:hidden transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Navigation */}
          <div className="p-3">
            <p className="px-3 mb-2 text-[10px] font-bold text-slate-500 uppercase tracking-[0.15em]">
              Navigation
            </p>
            <nav className="flex flex-col gap-1">
              {/* Public Model Sandbox */}
              <button
                onClick={() => navAction('sandbox')}
                className={activeTab === 'sandbox' ? 'nav-btn-active' : 'nav-btn-inactive'}
              >
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <span>Model Sandbox</span>
                <span className="ml-auto text-[9px] px-1.5 py-0.5 bg-emerald-500/20 text-emerald-300 font-bold rounded">
                  Public
                </span>
              </button>

              {/* Live Moderated Chat */}
              <button
                onClick={() => navAction('chat')}
                className={activeTab === 'chat' ? 'nav-btn-active' : 'nav-btn-inactive'}
              >
                <MessageSquare className="w-4 h-4" />
                <span>Live Moderated Chat</span>
                {!devAccess && (
                  <Lock className="w-3.5 h-3.5 text-slate-500 ml-auto" />
                )}
              </button>

              {/* Admin Dashboard */}
              <button
                onClick={() => navAction('dashboard')}
                className={activeTab === 'dashboard' ? 'nav-btn-active' : 'nav-btn-inactive'}
              >
                <BarChart3 className="w-4 h-4" />
                <span>Admin Dashboard</span>
                {!devAccess && (
                  <Lock className="w-3.5 h-3.5 text-slate-500 ml-auto" />
                )}
              </button>
            </nav>
          </div>

          {/* Channels (Only displayed when in chat tab and user is developer) */}
          {activeTab === 'chat' && devAccess && (
            <div className="px-3 pb-3 border-t border-slate-800/60 pt-3">
              <div className="flex items-center justify-between mb-2 px-3">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.15em]">
                  Channels
                </span>
                <span className="text-[10px] text-slate-600 font-mono">{channels.length}</span>
              </div>
              <ul className="space-y-0.5">
                {channels.map((chan: ChannelItem) => (
                  <li
                    key={chan.id}
                    onClick={() => {
                      setChannel(chan.id);
                      setMobileOpen(false);
                    }}
                    className={`px-3 py-2 rounded-xl text-[13px] cursor-pointer flex items-center gap-2 transition-all duration-150 ${
                      currentChannel === chan.id
                        ? 'bg-slate-800 text-white font-medium shadow-sm border-l-2 border-indigo-400'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                    }`}
                  >
                    <Hash className="w-3.5 h-3.5 text-slate-500" />
                    <span className="truncate">{chan.name}</span>
                    {currentChannel === chan.id && (
                      <span className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* User footer */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs shrink-0 shadow-sm ${
                  devAccess
                    ? 'bg-gradient-to-br from-indigo-500 to-emerald-400 text-white'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}
              >
                {devAccess ? 'V' : 'G'}
              </div>
              <div className="truncate text-left">
                <div className="text-xs font-semibold text-white truncate flex items-center gap-1.5">
                  {devAccess ? 'Vineet Tiwari' : 'Guest Visitor'}
                  {devAccess && (
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  )}
                </div>
                <div className="text-[10px] text-slate-400 truncate">
                  {devAccess ? (
                    <span className="text-emerald-400 font-medium">Developer Mode</span>
                  ) : (
                    'Public Sandbox Mode'
                  )}
                </div>
              </div>
            </div>

            {devAccess ? (
              <button
                onClick={logout}
                title="Lock / Sign Out"
                className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => {
                  onOpenAuth();
                  setMobileOpen(false);
                }}
                className="flex items-center gap-1 px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-[11px] font-bold shadow-sm transition-all active:scale-95"
              >
                <KeyRound className="w-3 h-3" /> Unlock
              </button>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}

export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="md:hidden fixed top-3 left-3 z-30 p-2 bg-slate-900 text-white rounded-xl shadow-lg hover:bg-slate-800 transition-colors"
    >
      <Menu className="w-5 h-5" />
    </button>
  );
}
