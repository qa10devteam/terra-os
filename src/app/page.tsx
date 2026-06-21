'use client';

import { Sidebar } from '@/components/Sidebar';
import { useStore } from '@/store/useStore';
import { ZwiadPage } from '@/components/pages/ZwiadPage';
import { KosztorysPage } from '@/components/pages/KosztorysPage';
import { SilnikPage } from '@/components/pages/SilnikPage';
import { DecyzjaPage } from '@/components/pages/DecyzjaPage';
import { LogistykaPage } from '@/components/pages/LogistykaPage';

export default function Home() {
  const { currentModule } = useStore();
  
  return (
    <div className="flex h-screen w-full overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-earth-950">
        {currentModule === 'zwiad' && <ZwiadPage />}
        {currentModule === 'kosztorys' && <KosztorysPage />}
        {currentModule === 'silnik' && <SilnikPage />}
        {currentModule === 'decyzja' && <DecyzjaPage />}
        {currentModule === 'logistyka' && <LogistykaPage />}
      </main>
    </div>
  );
}
