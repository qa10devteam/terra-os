'use client';

import { useState } from 'react';
import { Building2, Users, GitBranch, Bell, Key, Plus, Save, Loader2 } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { useStore } from '@/store/useStore';
import { showToast } from '@/components/Toast';

type TabId = 'profile' | 'team' | 'pipeline' | 'notifications' | 'api';

const TABS: { id: TabId; label: string; icon: typeof Building2 }[] = [
  { id: 'profile', label: 'Profil firmy', icon: Building2 },
  { id: 'team', label: 'Zespół', icon: Users },
  { id: 'pipeline', label: 'Pipeline', icon: GitBranch },
  { id: 'notifications', label: 'Powiadomienia', icon: Bell },
  { id: 'api', label: 'API', icon: Key },
];

const CPV_OPTIONS = [
  { code: '45000000', label: 'Roboty budowlane' },
  { code: '45200000', label: 'Roboty obiektów budowlanych' },
  { code: '45300000', label: 'Roboty instalacyjne' },
  { code: '45400000', label: 'Roboty wykończeniowe' },
  { code: '71000000', label: 'Usługi inżynieryjne' },
];

const VOIVODESHIPS = [
  'dolnośląskie', 'kujawsko-pomorskie', 'lubelskie', 'lubuskie',
  'łódzkie', 'małopolskie', 'mazowieckie', 'opolskie',
  'podkarpackie', 'podlaskie', 'pomorskie', 'śląskie',
  'świętokrzyskie', 'warmińsko-mazurskie', 'wielkopolskie', 'zachodniopomorskie',
];

const PIPELINE_STAGES_DEFAULT = [
  'MONITORING', 'ANALIZA', 'GO/NO-GO', 'KOSZTORYS', 'WERYFIKACJA', 'ZŁOŻENIE', 'WYNIK',
];

const MOCK_USERS = [
  { id: '1', name: 'Jan Kowalski', email: 'jan@firma.pl', role: 'admin' },
  { id: '2', name: 'Anna Nowak', email: 'anna@firma.pl', role: 'user' },
];

export function SettingsPage() {
  const { user, accessToken } = useStore();
  const [tab, setTab] = useState<TabId>('profile');
  const [saving, setSaving] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [stages, setStages] = useState(PIPELINE_STAGES_DEFAULT);
  const [orgForm, setOrgForm] = useState({ name: '', nip: '', cpv: [] as string[], regions: [] as string[] });
  const [notifs, setNotifs] = useState({ deadline: true, new_match: true, status_change: true, mention: false });

  async function saveProfile() {
    setSaving(true);
    try {
      if (user?.org_id && accessToken) {
        const res = await fetch(`/api/v2/organizations/${user.org_id}`, {
          method: 'PATCH',
          headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
          body: JSON.stringify(orgForm),
        });
        if (!res.ok) throw new Error('Błąd zapisu');
      }
      showToast('success', 'Profil firmy zaktualizowany');
    } catch {
      showToast('error', 'Błąd podczas zapisywania');
    } finally {
      setSaving(false);
    }
  }

  async function inviteUser() {
    if (!inviteEmail.trim()) return;
    showToast('info', `Zaproszenie wysłane do ${inviteEmail}`);
    setInviteEmail('');
  }

  function toggleCpv(code: string) {
    setOrgForm(f => ({
      ...f,
      cpv: f.cpv.includes(code) ? f.cpv.filter(c => c !== code) : [...f.cpv, code],
    }));
  }

  function toggleRegion(r: string) {
    setOrgForm(f => ({
      ...f,
      regions: f.regions.includes(r) ? f.regions.filter(x => x !== r) : [...f.regions, r],
    }));
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-6 py-4 border-b border-earth-800/60 shrink-0">
        <h2 className="text-lg font-semibold text-earth-100">Ustawienia</h2>
        <p className="text-earth-500 text-xs mt-0.5">Konfiguracja systemu i profilu firmy</p>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar tabs */}
        <div className="w-48 border-r border-earth-800/60 py-3 px-2 space-y-0.5 shrink-0">
          {TABS.map(t => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${tab === t.id ? 'bg-accent-primary/15 text-accent-primary' : 'text-earth-400 hover:text-earth-200 hover:bg-earth-800/60'}`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {t.label}
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {tab === 'profile' && (
            <div className="max-w-lg space-y-4">
              <h3 className="text-sm font-semibold text-earth-200">Profil firmy</h3>
              <div>
                <label className="block text-xs text-earth-500 mb-1.5">Nazwa firmy</label>
                <input
                  value={orgForm.name}
                  onChange={e => setOrgForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="Kowalski Budownictwo Sp. z o.o."
                  className="w-full bg-earth-800/60 border border-earth-700/60 rounded-xl px-4 py-2.5 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-accent-primary/60"
                />
              </div>
              <div>
                <label className="block text-xs text-earth-500 mb-1.5">NIP</label>
                <input
                  value={orgForm.nip}
                  onChange={e => setOrgForm(f => ({ ...f, nip: e.target.value }))}
                  placeholder="1234567890"
                  className="w-full bg-earth-800/60 border border-earth-700/60 rounded-xl px-4 py-2.5 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-accent-primary/60"
                />
              </div>
              <div>
                <label className="block text-xs text-earth-500 mb-2">Logo firmy</label>
                <div className="w-20 h-20 rounded-xl bg-earth-800 border border-earth-700/60 flex items-center justify-center text-earth-600 text-xs cursor-pointer hover:bg-earth-700 transition-colors">
                  + Logo
                </div>
              </div>

              <GlassCard className="p-4">
                <p className="text-xs font-semibold text-earth-400 uppercase tracking-wide mb-2">Kody CPV</p>
                <div className="space-y-1.5">
                  {CPV_OPTIONS.map(c => (
                    <label key={c.code} className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={orgForm.cpv.includes(c.code)} onChange={() => toggleCpv(c.code)} className="accent-emerald-500" />
                      <span className="text-xs text-earth-300"><span className="font-mono text-earth-600 mr-1">{c.code}</span>{c.label}</span>
                    </label>
                  ))}
                </div>
              </GlassCard>

              <GlassCard className="p-4">
                <p className="text-xs font-semibold text-earth-400 uppercase tracking-wide mb-2">Województwa</p>
                <div className="grid grid-cols-2 gap-1">
                  {VOIVODESHIPS.map(v => (
                    <label key={v} className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={orgForm.regions.includes(v)} onChange={() => toggleRegion(v)} className="accent-emerald-500" />
                      <span className="text-xs text-earth-300 capitalize">{v}</span>
                    </label>
                  ))}
                </div>
              </GlassCard>

              <button
                onClick={saveProfile}
                disabled={saving}
                className="flex items-center gap-2 px-5 py-2.5 bg-accent-primary text-earth-950 rounded-xl text-sm font-semibold hover:bg-emerald-400 transition-colors disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Zapisz zmiany
              </button>
            </div>
          )}

          {tab === 'team' && (
            <div className="max-w-lg space-y-4">
              <h3 className="text-sm font-semibold text-earth-200">Zespół</h3>
              <div className="space-y-2">
                {MOCK_USERS.map(u => (
                  <GlassCard key={u.id} className="p-3 flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-accent-primary/15 flex items-center justify-center text-xs font-bold text-accent-primary">
                      {u.name.slice(0, 1)}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm text-earth-200">{u.name}</p>
                      <p className="text-xs text-earth-600">{u.email}</p>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-earth-800 text-earth-400 capitalize">{u.role}</span>
                  </GlassCard>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  value={inviteEmail}
                  onChange={e => setInviteEmail(e.target.value)}
                  placeholder="email@firma.pl"
                  className="flex-1 bg-earth-800/60 border border-earth-700/60 rounded-xl px-4 py-2.5 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-accent-primary/60"
                />
                <button
                  onClick={inviteUser}
                  className="flex items-center gap-2 px-4 py-2.5 bg-accent-primary/20 text-accent-primary rounded-xl text-sm font-medium hover:bg-accent-primary/30 transition-colors"
                >
                  <Plus className="w-4 h-4" /> Zaproś
                </button>
              </div>
            </div>
          )}

          {tab === 'pipeline' && (
            <div className="max-w-lg space-y-4">
              <h3 className="text-sm font-semibold text-earth-200">Etapy Pipeline</h3>
              <div className="space-y-2">
                {stages.map((s, i) => (
                  <GlassCard key={i} className="p-3 flex items-center gap-3">
                    <span className="text-xs text-earth-600 w-5 font-mono">{i + 1}</span>
                    <input
                      value={s}
                      onChange={e => setStages(arr => arr.map((x, j) => j === i ? e.target.value : x))}
                      className="flex-1 bg-transparent text-sm text-earth-200 outline-none border-b border-transparent focus:border-earth-700"
                    />
                  </GlassCard>
                ))}
              </div>
              <button
                onClick={() => showToast('success', 'Etapy pipeline zaktualizowane')}
                className="flex items-center gap-2 px-5 py-2.5 bg-accent-primary text-earth-950 rounded-xl text-sm font-semibold hover:bg-emerald-400 transition-colors"
              >
                <Save className="w-4 h-4" /> Zapisz etapy
              </button>
            </div>
          )}

          {tab === 'notifications' && (
            <div className="max-w-lg space-y-4">
              <h3 className="text-sm font-semibold text-earth-200">Powiadomienia</h3>
              <GlassCard className="p-4 space-y-3">
                {[
                  { key: 'deadline', label: 'Zbliżający się termin składania ofert', desc: 'Alerta gdy deadline < 3 dni' },
                  { key: 'new_match', label: 'Nowe dopasowanie', desc: 'Gdy AI znajdzie pasujący przetarg' },
                  { key: 'status_change', label: 'Zmiana statusu', desc: 'Gdy przetarg zmienia etap' },
                  { key: 'mention', label: 'Wzmianki (@)', desc: 'Gdy ktoś cię oznaczy w komentarzu' },
                ].map(item => (
                  <label key={item.key} className="flex items-center justify-between cursor-pointer group">
                    <div>
                      <p className="text-sm text-earth-200">{item.label}</p>
                      <p className="text-xs text-earth-600">{item.desc}</p>
                    </div>
                    <div
                      onClick={() => setNotifs(n => ({ ...n, [item.key]: !n[item.key as keyof typeof n] }))}
                      className={`w-10 h-5 rounded-full transition-colors cursor-pointer ${notifs[item.key as keyof typeof notifs] ? 'bg-accent-primary' : 'bg-earth-700'}`}
                    >
                      <div className={`w-4 h-4 rounded-full bg-white mt-0.5 transition-transform ${notifs[item.key as keyof typeof notifs] ? 'translate-x-5.5' : 'translate-x-0.5'}`} />
                    </div>
                  </label>
                ))}
              </GlassCard>
              <button
                onClick={() => showToast('success', 'Ustawienia powiadomień zapisane')}
                className="flex items-center gap-2 px-5 py-2.5 bg-accent-primary text-earth-950 rounded-xl text-sm font-semibold hover:bg-emerald-400 transition-colors"
              >
                <Save className="w-4 h-4" /> Zapisz
              </button>
            </div>
          )}

          {tab === 'api' && (
            <div className="max-w-lg space-y-4">
              <h3 className="text-sm font-semibold text-earth-200">API</h3>
              <GlassCard className="p-4">
                <p className="text-xs text-earth-500 mb-2">API Key</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-xs font-mono text-earth-400 bg-earth-800 rounded-lg px-3 py-2">tk_••••••••••••••••••••••••••••••••</code>
                  <button
                    onClick={() => showToast('info', 'Klucz API skopiowany')}
                    className="px-3 py-2 bg-earth-800 text-earth-400 rounded-lg text-xs hover:bg-earth-700 transition-colors"
                  >
                    Kopiuj
                  </button>
                </div>
              </GlassCard>
              <GlassCard className="p-4">
                <p className="text-xs text-earth-500 mb-1">Dokumentacja API</p>
                <a href="/api/docs" target="_blank" className="text-accent-primary text-sm hover:underline">
                  Otwórz Swagger UI →
                </a>
              </GlassCard>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
