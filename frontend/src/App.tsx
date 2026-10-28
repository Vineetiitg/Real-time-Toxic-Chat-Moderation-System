import React, { useState, useEffect } from 'react';
import ChatWindow from './components/chat/ChatWindow';
import AdminDashboard from './components/dashboard/AdminDashboard';
import ModelSandbox from './components/sandbox/ModelSandbox';
import DeveloperLockGate from './components/auth/DeveloperLockGate';
import AuthModal from './components/auth/AuthModal';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import Sidebar, { MobileMenuButton } from './components/layout/Sidebar';
import { useAuthStore } from './stores/authStore';
import { useChatStore } from './stores/chatStore';

function App() {
  const { user, isDeveloper } = useAuthStore();
  const devAccess = isDeveloper();

  // Non-developer visitors default to Model Sandbox; Vineet defaults to Chat
  const [activeTab, setActiveTab] = useState<'sandbox' | 'chat' | 'dashboard'>(() => {
    return devAccess ? 'chat' : 'sandbox';
  });
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

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

          {/* Main Content Area */}
          <div className="flex-1 flex flex-col bg-white overflow-hidden relative">
            {activeTab === 'sandbox' && (
              <ModelSandbox onOpenAuth={() => setIsAuthModalOpen(true)} />
            )}

            {activeTab === 'chat' && (
              devAccess ? (
                <ChatWindow
                  channelId={currentChannel}
                  currentUserId={user?.id || 'dev-vineet'}
                  currentUserName={user?.displayName || 'Vineet Tiwari'}
                />
              ) : (
                <DeveloperLockGate
                  featureName="Live Moderated Chat"
                  onUnlock={() => setIsAuthModalOpen(true)}
                  onGoSandbox={() => setActiveTab('sandbox')}
                />
              )
            )}

            {activeTab === 'dashboard' && (
              devAccess ? (
                <AdminDashboard />
              ) : (
                <DeveloperLockGate
                  featureName="Admin Dashboard"
                  onUnlock={() => setIsAuthModalOpen(true)}
                  onGoSandbox={() => setActiveTab('sandbox')}
                />
              )
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
