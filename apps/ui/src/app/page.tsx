'use client';

import { Component, ReactNode, useState, useEffect } from 'react';
import { LoginForm } from '@/components/LoginForm';
import { AnalyticsPage } from '@/components/pages/AnalyticsPage';
import { DashboardPage } from '@/components/pages/DashboardPage';
import { ZwiadPage } from '@/components/pages/ZwiadPage';
import { KosztorysPage } from '@/components/pages/KosztorysPage';
import { SilnikPage } from '@/components/pages/SilnikPage';
import { DecyzjaPage } from '@/components/pages/DecyzjaPage';
import { LogistykaPage } from '@/components/pages/LogistykaPage';
import { RfqPage } from '@/components/pages/RfqPage';
import { PipelinePage } from '@/components/pages/PipelinePage';
import { SystemPage } from '@/components/pages/SystemPage';
import { SettingsPage } from '@/components/pages/SettingsPage';
import { ImportPage } from '@/components/pages/ImportPage';
import { PogodaPage } from '@/components/pages/PogodaPage';
import { MarketIntelPage } from '@/components/pages/MarketIntelPage';
import { CompetitorPage } from '@/components/pages/CompetitorPage';
import { BookmarksBoardPage } from '@/components/pages/BookmarksBoardPage';
import { BuyerCRMPage } from '@/components/pages/BuyerCRMPage';
import { NotificationsPage } from '@/components/pages/NotificationsPage';
import ExportPage from '@/components/pages/ExportPage';
import { OfertaPage } from '@/components/pages/OfertaPage';
import AutomationPage from '@/components/pages/AutomationPage';
import { Sidebar } from '@/components/Sidebar';
import { MarketBar } from '@/components/widgets/MarketBar';
import { ChatWidget } from '@/components/ChatWidget';
import { CommandMenu } from '@/components/CommandMenu';
import { ToastContainer } from '@/components/Toast';
import { OnboardingWizard } from '@/components/OnboardingWizard';
import { useStore } from '@/store/useStore';

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean; error?: Error }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-earth-950 flex items-center justify-center text-earth-100 p-8">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 rounded-2xl bg-red-500/20 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">⚠️</span>
            </div>
            <h1 className="text-xl font-bold mb-2">Błąd aplikacji</h1>
            <p className="text-earth-400 mb-4 text-sm">
              {this.state.error?.message || 'Wystąpił nieoczekiwany błąd'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2 bg-accent-primary text-earth-950 rounded-lg font-semibold hover:bg-emerald-400 transition-colors"
            >
              Odśwież stronę
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function ActivePage() {
  const { currentModule } = useStore();
  switch (currentModule) {
    case 'dashboard':     return <DashboardPage />;
    case 'zwiad':         return <ZwiadPage />;
    case 'kosztorys':     return <KosztorysPage />;
    case 'silnik':        return <SilnikPage />;
    case 'decyzja':       return <DecyzjaPage />;
    case 'analytics':     return <AnalyticsPage />;
    case 'logistyka':     return <LogistykaPage />;
    case 'rfq':           return <RfqPage />;
    case 'pipeline':      return <PipelinePage />;
    case 'system':        return <SystemPage />;
    case 'settings':      return <SettingsPage />;
    case 'pogoda':        return <PogodaPage />;
    case 'market-intel':  return <MarketIntelPage />;
    case 'competitors':   return <CompetitorPage />;
    case 'bookmarks':     return <BookmarksBoardPage />;
    case 'buyer-crm':     return <BuyerCRMPage />;
    case 'notifications': return <NotificationsPage />;
    case 'export':        return <ExportPage />;
    case 'oferta':        return <OfertaPage />;
    case 'automations':   return <AutomationPage />;
    default:              return <DashboardPage />;
  }
}

export default function Home() {
  const { user, accessToken } = useStore();
  const isAuthenticated = !!(user && accessToken);
  const [commandOpen, setCommandOpen] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

  // Show onboarding if user has no org_id
  useEffect(() => {
    if (isAuthenticated && user && !user.org_id) {
      const dismissed = localStorage.getItem('terra-onboarding-dismissed');
      if (!dismissed) setShowOnboarding(true);
    }
  }, [isAuthenticated, user]);

  // Global keyboard shortcuts
  useEffect(() => {
    if (!isAuthenticated) return;
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        setCommandOpen(true);
        e.preventDefault();
      }
      if (e.key === 'Escape') setCommandOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <ErrorBoundary>
        <LoginForm onSuccess={() => {}} />
        <ToastContainer />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <div className="flex min-h-[100dvh] bg-earth-950">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <MarketBar />
          <main className="flex-1 overflow-auto bg-earth-950">
            <ActivePage />
          </main>
        </div>
        <ChatWidget />
      </div>
      <CommandMenu open={commandOpen} onClose={() => setCommandOpen(false)} />
      <ToastContainer />
      {showOnboarding && (
        <OnboardingWizard onComplete={() => {
          setShowOnboarding(false);
          localStorage.setItem('terra-onboarding-dismissed', '1');
        }} />
      )}
    </ErrorBoundary>
  );
}
