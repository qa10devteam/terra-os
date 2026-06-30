'use client';

import { useState } from 'react';
import { OpeningView } from '@/components/OpeningView';
import { DashboardPage } from '@/components/pages/DashboardPage';
import { ZwiadPage } from '@/components/pages/ZwiadPage';
import { KosztorysPage } from '@/components/pages/KosztorysPage';
import { SilnikPage } from '@/components/pages/SilnikPage';
import { DecyzjaPage } from '@/components/pages/DecyzjaPage';
import { LogistykaPage } from '@/components/pages/LogistykaPage';
import { RfqPage } from '@/components/pages/RfqPage';
import { PipelinePage } from '@/components/pages/PipelinePage';
import { SystemPage } from '@/components/pages/SystemPage';
import { PogodaPage } from '@/components/pages/PogodaPage';
import { Sidebar } from '@/components/Sidebar';
import { MarketBar } from '@/components/widgets/MarketBar';
import { ToastContainer } from '@/components/Toast';
import { ChatWidget } from '@/components/ChatWidget';
import { useStore } from '@/store/useStore';

function ActivePage() {
  const { currentModule } = useStore();
  switch (currentModule) {
    case 'dashboard':  return <DashboardPage />;
    case 'zwiad':      return <ZwiadPage />;
    case 'kosztorys':  return <KosztorysPage />;
    case 'silnik':     return <SilnikPage />;
    case 'decyzja':    return <DecyzjaPage />;
    case 'logistyka':  return <LogistykaPage />;
    case 'rfq':        return <RfqPage />;
    case 'pipeline':   return <PipelinePage />;
    case 'system':     return <SystemPage />;
    case 'pogoda':     return <PogodaPage />;
    default:           return <DashboardPage />;
  }
}

export default function Home() {
  const [showApp, setShowApp] = useState(false);

  if (!showApp) {
    return <OpeningView onStart={() => setShowApp(true)} />;
  }

  return (
    <div className="flex min-h-[100dvh] bg-earth-950">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <MarketBar />
        <main className="flex-1 overflow-auto bg-earth-950">
          <ActivePage />
        </main>
      </div>
      <ToastContainer />
      <ChatWidget />
    </div>
  );
}
