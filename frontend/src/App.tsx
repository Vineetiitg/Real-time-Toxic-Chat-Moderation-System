import React, { useState, useEffect } from 'react';
import ChatWindow from './components/chat/ChatWindow';
import AdminDashboard from './components/dashboard/AdminDashboard';
import AuthModal from './components/auth/AuthModal';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import Sidebar, { MobileMenuButton } from './components/layout/Sidebar';
import { useAuthStore } from './stores/authStore';
import { useChatStore } from './stores/chatStore';

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'dashboard'>('chat');
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const { user } = useAuthStore();
  const { currentChannel, fetchChannels } = useChatStore();

  useEffect(() => {
    fetchChannels();
  }, []);

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-slate-100 flex items-center justify-center p-0 sm:p-3 font-sans text-slate-800">
        <div className="w-full max-w-7xl bg-white rounded-none sm:rounded-2xl shadow-2xl border-0 sm:border border-slate-200/80 overflow-hidden flex flex-col md:flex-row h-screen sm:h-[95vh]">
          {/* Mobile menu button */}
          <MobileMenuButton onClick={() => setIsMobileMenuOpen(true)} />

          {/* Sidebar */}
          <Sidebar
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            onOpenAuth={() => setIsAuthModalOpen(true)}
            isMobileOpen={isMobileMenuOpen}
            setMobileOpen={setIsMobileMenuOpen}
          />

          {/* Main Content */}
          <div className="flex-1 flex flex-col bg-white overflow-hidden relative">
            {activeTab === 'chat' ? (
              <ChatWindow
                channelId={currentChannel}
                currentUserId={user?.id || 'demo-user'}
                currentUserName={user?.displayName || 'Vineet'}
              />
            ) : (
              <AdminDashboard />
            )}
          </div>
        </div>

        {/* Auth Modal */}
        <AuthModal
          isOpen={isAuthModalOpen}
          onClose={() => setIsAuthModalOpen(false)}
        />
      </div>
    </ErrorBoundary>
  );
}

export default App;
