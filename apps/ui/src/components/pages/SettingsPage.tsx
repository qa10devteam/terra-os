'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Building2, Users, GitBranch, Bell, Key,
  Plus, Save, Loader2, Trash2, Shield, User, Eye, Crown,
  Mail, CheckCircle2, XCircle, RefreshCw,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { useStore } from '@/store/useStore';
import { showToast } from '@/components/Toast';

type TabId = 'profile' | 'team' | 'pipeline' | 'notifications' | 'api';

const TABS: { id: TabId; label: string; icon: typeof Building2 }[] = [
  { id: 'profile',       label: 'Profil firmy',     icon: Building2 },
  { id: 'team',          label: 'Zespół',           icon: Users     },
  { id: 'pipeline',      label: 'Pipeline',         icon: GitBranch },
  { id: 'notifications', label: 'Powiadomienia',    icon: Bell      },
  { id: 'api',           label: 'API',              icon: Key       },
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

const ROLE_LABELS: Record<string, { label: string; icon: typeof User; color: string }> = {
  owner:     { label: 'Właściciel', icon: Crown,   color: 'text-amber-400'   },
  admin:     { label: 'Admin',      icon: Shield,  color: 'text-accent-primary' },
  estimator: { label: 'Kosztorysant', icon: User,  color: 'text-earth-300'   },
  viewer:    { label: 'Przeglądający', icon: Eye,  color: 'text-earth-500'   },
};

// ─── API helpers ──────────────────────────────────────────────────────────────

async function apiFetch(url: string, token: string, opts?: RequestInit) {
  const res = await fetch(url, {
    ...opts,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...(opts?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ─── Main component ───────────────────────────────────────────────────────────

export function SettingsPage() {
  const { user, accessToken } = useStore();
  const [tab, setTab] = useState<TabId>('profile');

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-6 py-4 border-b border-earth-800/60 shrink-0">
        <h2 className="text-lg font-semibold text-earth-100">Ustawienia</h2>
        <p className="text-earth-500 text-xs mt-0.5">Konfiguracja systemu i profilu firmy</p>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-48 border-r border-earth-800/60 py-3 px-2 space-y-0.5 shrink-0">
          {TABS.map(t => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  tab === t.id
                    ? 'bg-accent-primary/15 text-accent-primary'
                    : 'text-earth-400 hover:text-earth-200 hover:bg-earth-800/60'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {t.label}
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {tab === 'profile'       && <ProfileTab       token={accessToken ?? ''} />}
          {tab === 'team'          && <TeamTab          token={accessToken ?? ''} currentUserId={user?.id ?? ''} currentRole={user?.role ?? ''} />}
          {tab === 'pipeline'      && <PipelineTab />}
          {tab === 'notifications' && <NotificationsTab token={accessToken ?? ''} />}
          {tab === 'api'           && <ApiTab           token={accessToken ?? ''} />}
        </div>
      </div>
    </div>
  );
}

// ─── Profile tab ──────────────────────────────────────────────────────────────

function ProfileTab({ token }: { token: string }) {
  const [loading, setLoading]  = useState(true);
  const [saving, setSaving]    = useState(false);
  const [form, setForm]        = useState({ name: '', nip: '', cpv: [] as string[], regions: [] as string[] });

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiFetch('/api/v2/organizations/me', token);
      setForm({
        name:    data.name    ?? '',
        nip:     data.nip     ?? '',
        cpv:     data.settings?.default_cpv     ?? [],
        regions: data.settings?.default_regions ?? [],
      });
    } catch (e: any) {
      showToast('error', e.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  async function save() {
    setSaving(true);
    try {
      await apiFetch('/api/v2/organizations/me', token, {
        method: 'PUT',
        body: JSON.stringify({
          name: form.name || undefined,
          nip:  form.nip  || undefined,
          settings: { default_cpv: form.cpv, default_regions: form.regions },
        }),
      });
      showToast('success', 'Profil firmy zaktualizowany');
    } catch (e: any) {
      showToast('error', e.message);
    } finally {
      setSaving(false);
    }
  }

  function toggleCpv(code: string) {
    setForm(f => ({ ...f, cpv: f.cpv.includes(code) ? f.cpv.filter(c => c !== code) : [...f.cpv, code] }));
  }
  function toggleRegion(r: string) {
    setForm(f => ({ ...f, regions: f.regions.includes(r) ? f.regions.filter(x => x !== r) : [...f.regions, r] }));
  }

  if (loading) return <Spinner />;

  return (
    <div className="max-w-lg space-y-4">
      <h3 className="text-sm font-semibold text-earth-200">Profil firmy</h3>

      <Field label="Nazwa firmy">
        <input
          value={form.name}
          onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          placeholder="Kowalski Budownictwo Sp. z o.o."
          className={INPUT}
        />
      </Field>

      <Field label="NIP">
        <input
          value={form.nip}
          onChange={e => setForm(f => ({ ...f, nip: e.target.value }))}
          placeholder="1234567890"
          className={INPUT}
        />
      </Field>

      <GlassCard className="p-4">
        <p className="text-xs font-semibold text-earth-400 uppercase tracking-wide mb-2">Domyślne kody CPV</p>
        <div className="space-y-1.5">
          {CPV_OPTIONS.map(c => (
            <label key={c.code} className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.cpv.includes(c.code)} onChange={() => toggleCpv(c.code)} className="accent-emerald-500" />
              <span className="text-xs text-earth-300">
                <span className="font-mono text-earth-600 mr-1">{c.code}</span>{c.label}
              </span>
            </label>
          ))}
        </div>
      </GlassCard>

      <GlassCard className="p-4">
        <p className="text-xs font-semibold text-earth-400 uppercase tracking-wide mb-2">Województwa</p>
        <div className="grid grid-cols-2 gap-1">
          {VOIVODESHIPS.map(v => (
            <label key={v} className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.regions.includes(v)} onChange={() => toggleRegion(v)} className="accent-emerald-500" />
              <span className="text-xs text-earth-300 capitalize">{v}</span>
            </label>
          ))}
        </div>
      </GlassCard>

      <Btn onClick={save} loading={saving} icon={<Save className="w-4 h-4" />}>
        Zapisz zmiany
      </Btn>
    </div>
  );
}

// ─── Team tab ─────────────────────────────────────────────────────────────────

function TeamTab({ token, currentUserId, currentRole }: { token: string; currentUserId: string; currentRole: string }) {
  const [loadingMembers, setLoadingMembers]  = useState(true);
  const [loadingInvites, setLoadingInvites]  = useState(true);
  const [members, setMembers]  = useState<any[]>([]);
  const [invites, setInvites]  = useState<any[]>([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole,  setInviteRole]  = useState('estimator');
  const [sending, setSending]   = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    if (!token) return;
    setLoadingMembers(true);
    setLoadingInvites(true);
    try {
      const [m, i] = await Promise.all([
        apiFetch('/api/v2/organizations/me/members', token),
        apiFetch('/api/v2/organizations/me/invites', token).catch(() => ({ items: [] })),
      ]);
      setMembers(m.items ?? []);
      setInvites(i.items ?? []);
    } catch (e: any) {
      showToast('error', e.message);
    } finally {
      setLoadingMembers(false);
      setLoadingInvites(false);
    }
  }, [token]);

  useEffect(() => { loadAll(); }, [loadAll]);

  async function sendInvite() {
    if (!inviteEmail.trim()) return;
    setSending(true);
    try {
      await apiFetch('/api/v2/organizations/me/invite', token, {
        method: 'POST',
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
      });
      showToast('success', `Zaproszenie wysłane do ${inviteEmail}`);
      setInviteEmail('');
      loadAll();
    } catch (e: any) {
      showToast('error', e.message);
    } finally {
      setSending(false);
    }
  }

  async function cancelInvite(id: string) {
    setRemoving(id);
    try {
      await apiFetch(`/api/v2/organizations/me/invites/${id}`, token, { method: 'DELETE' });
      setInvites(prev => prev.filter(i => i.id !== id));
      showToast('success', 'Zaproszenie anulowane');
    } catch (e: any) {
      showToast('error', e.message);
    } finally {
      setRemoving(null);
    }
  }

  async function changeRole(memberId: string, newRole: string) {
    try {
      await apiFetch(`/api/v2/organizations/me/members/${memberId}`, token, {
        method: 'PATCH',
        body: JSON.stringify({ role: newRole }),
      });
      setMembers(prev => prev.map(m => m.id === memberId ? { ...m, role: newRole } : m));
      showToast('success', 'Rola zaktualizowana');
    } catch (e: any) {
      showToast('error', e.message);
    }
  }

  async function removeMember(memberId: string) {
    if (!confirm('Czy na pewno chcesz usunąć tego użytkownika z organizacji?')) return;
    setRemoving(memberId);
    try {
      await apiFetch(`/api/v2/organizations/me/members/${memberId}`, token, { method: 'DELETE' });
      setMembers(prev => prev.filter(m => m.id !== memberId));
      showToast('success', 'Użytkownik usunięty z organizacji');
    } catch (e: any) {
      showToast('error', e.message);
    } finally {
      setRemoving(null);
    }
  }

  const canManage = ['owner', 'admin'].includes(currentRole);

  return (
    <div className="max-w-lg space-y-6">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-earth-200">Członkowie ({members.length})</h3>
          <button onClick={loadAll} className="p-1.5 text-earth-600 hover:text-earth-400 transition-colors">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        {loadingMembers ? <Spinner /> : (
          <div className="space-y-2">
            {members.map(m => {
              const rd = ROLE_LABELS[m.role] ?? ROLE_LABELS.viewer;
              const RoleIcon = rd.icon;
              return (
                <GlassCard key={m.id} className="p-3 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-accent-primary/15 flex items-center justify-center text-xs font-bold text-accent-primary shrink-0">
                    {(m.name ?? m.email).slice(0, 1).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-earth-200 truncate">
                      {m.name}
                      {m.is_me && <span className="ml-1 text-xs text-earth-600">(Ty)</span>}
                    </p>
                    <p className="text-xs text-earth-600 truncate">{m.email}</p>
                  </div>

                  {canManage && !m.is_me && currentRole === 'owner' ? (
                    <select
                      value={m.role}
                      onChange={e => changeRole(m.id, e.target.value)}
                      className="text-xs bg-earth-800 border border-earth-700/60 rounded-lg px-2 py-1 text-earth-300 focus:outline-none focus:border-accent-primary/60"
                    >
                      {Object.entries(ROLE_LABELS).map(([v, info]) => (
                        <option key={v} value={v}>{info.label}</option>
                      ))}
                    </select>
                  ) : (
                    <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-earth-800 ${rd.color}`}>
                      <RoleIcon className="w-3 h-3" /> {rd.label}
                    </span>
                  )}

                  {canManage && !m.is_me && currentRole === 'owner' && (
                    <button
                      onClick={() => removeMember(m.id)}
                      disabled={removing === m.id}
                      className="p-1.5 text-earth-700 hover:text-red-400 transition-colors disabled:opacity-40"
                      title="Usuń z organizacji"
                    >
                      {removing === m.id
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <Trash2 className="w-3.5 h-3.5" />}
                    </button>
                  )}
                </GlassCard>
              );
            })}
          </div>
        )}
      </div>

      {/* Pending invites */}
      {!loadingInvites && invites.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold text-earth-400 uppercase tracking-wide">Oczekujące zaproszenia</h3>
          {invites.map(inv => (
            <GlassCard key={inv.id} className="p-3 flex items-center gap-3">
              <Mail className="w-4 h-4 text-earth-600 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-earth-300 truncate">{inv.email}</p>
                <p className="text-xs text-earth-600">
                  {ROLE_LABELS[inv.role]?.label ?? inv.role} · wygasa {new Date(inv.expires_at).toLocaleDateString('pl-PL')}
                </p>
              </div>
              {canManage && (
                <button
                  onClick={() => cancelInvite(inv.id)}
                  disabled={removing === inv.id}
                  className="p-1.5 text-earth-700 hover:text-red-400 transition-colors disabled:opacity-40"
                  title="Anuluj zaproszenie"
                >
                  {removing === inv.id
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : <XCircle className="w-3.5 h-3.5" />}
                </button>
              )}
            </GlassCard>
          ))}
        </div>
      )}

      {/* Invite form */}
      {canManage && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold text-earth-400 uppercase tracking-wide">Zaproś nowego członka</h3>
          <div className="flex gap-2">
            <input
              value={inviteEmail}
              onChange={e => setInviteEmail(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendInvite()}
              placeholder="email@firma.pl"
              className={`flex-1 ${INPUT}`}
            />
            <select
              value={inviteRole}
              onChange={e => setInviteRole(e.target.value)}
              className="bg-earth-800/60 border border-earth-700/60 rounded-xl px-3 py-2.5 text-sm text-earth-300 focus:outline-none focus:border-accent-primary/60"
            >
              <option value="estimator">Kosztorysant</option>
              <option value="admin">Admin</option>
              <option value="viewer">Przeglądający</option>
            </select>
            <button
              onClick={sendInvite}
              disabled={sending || !inviteEmail.trim()}
              className="flex items-center gap-2 px-4 py-2.5 bg-accent-primary/20 text-accent-primary rounded-xl text-sm font-medium hover:bg-accent-primary/30 transition-colors disabled:opacity-50"
            >
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Zaproś
            </button>
          </div>
          <p className="text-xs text-earth-700">Zaproszony użytkownik otrzyma link aktywacyjny ważny 7 dni.</p>
        </div>
      )}
    </div>
  );
}

// ─── Pipeline tab ─────────────────────────────────────────────────────────────

function PipelineTab() {
  const [stages, setStages] = useState(PIPELINE_STAGES_DEFAULT);

  return (
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
      <Btn onClick={() => showToast('success', 'Etapy pipeline zaktualizowane')} icon={<Save className="w-4 h-4" />}>
        Zapisz etapy
      </Btn>
    </div>
  );
}

// ─── Notifications tab ────────────────────────────────────────────────────────

function NotificationsTab({ token }: { token: string }) {
  const [notifs, setNotifs] = useState({ deadline: true, new_match: true, status_change: true, mention: false });

  const ITEMS = [
    { key: 'deadline',      label: 'Zbliżający się termin',  desc: 'Alert gdy deadline < 3 dni'          },
    { key: 'new_match',     label: 'Nowe dopasowanie',       desc: 'Gdy AI znajdzie pasujący przetarg'   },
    { key: 'status_change', label: 'Zmiana statusu',         desc: 'Gdy przetarg zmienia etap'           },
    { key: 'mention',       label: 'Wzmianki (@)',           desc: 'Gdy ktoś oznaczy Cię w komentarzu'  },
  ];

  return (
    <div className="max-w-lg space-y-4">
      <h3 className="text-sm font-semibold text-earth-200">Powiadomienia</h3>
      <GlassCard className="p-4 space-y-4">
        {ITEMS.map(item => (
          <div key={item.key} className="flex items-center justify-between">
            <div>
              <p className="text-sm text-earth-200">{item.label}</p>
              <p className="text-xs text-earth-600">{item.desc}</p>
            </div>
            <button
              onClick={() => setNotifs(n => ({ ...n, [item.key]: !n[item.key as keyof typeof n] }))}
              className={`w-10 h-5 rounded-full transition-colors ${notifs[item.key as keyof typeof notifs] ? 'bg-accent-primary' : 'bg-earth-700'}`}
            >
              <div className={`w-4 h-4 rounded-full bg-white mt-0.5 mx-0.5 transition-transform ${notifs[item.key as keyof typeof notifs] ? 'translate-x-5' : 'translate-x-0'}`} />
            </button>
          </div>
        ))}
      </GlassCard>
      <Btn onClick={() => showToast('success', 'Ustawienia powiadomień zapisane')} icon={<Save className="w-4 h-4" />}>
        Zapisz
      </Btn>
    </div>
  );
}

// ─── API tab ──────────────────────────────────────────────────────────────────

function ApiTab({ token }: { token: string }) {
  const [keys, setKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiFetch('/api/v2/api-keys', token);
      setKeys(data.items ?? data ?? []);
    } catch {
      setKeys([]);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  async function createKey() {
    setCreating(true);
    try {
      const data = await apiFetch('/api/v2/api-keys', token, {
        method: 'POST',
        body: JSON.stringify({ name: 'Klucz ' + new Date().toLocaleDateString('pl-PL') }),
      });
      showToast('success', 'Klucz API utworzony');
      if (data?.key) {
        await navigator.clipboard.writeText(data.key).catch(() => {});
        showToast('info', 'Klucz skopiowany do schowka');
      }
      load();
    } catch (e: any) {
      showToast('error', e.message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="max-w-lg space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-earth-200">Klucze API</h3>
        <Btn onClick={createKey} loading={creating} icon={<Plus className="w-4 h-4" />} variant="ghost">
          Nowy klucz
        </Btn>
      </div>

      {loading ? <Spinner /> : keys.length === 0 ? (
        <GlassCard className="p-6 text-center">
          <Key className="w-8 h-8 text-earth-700 mx-auto mb-2" />
          <p className="text-sm text-earth-500">Brak kluczy API. Utwórz pierwszy klucz powyżej.</p>
        </GlassCard>
      ) : (
        <div className="space-y-2">
          {keys.map((k: any) => (
            <GlassCard key={k.id} className="p-3 flex items-center gap-3">
              <Key className="w-4 h-4 text-earth-600 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-earth-200">{k.name ?? 'Klucz API'}</p>
                <p className="text-xs text-earth-600 font-mono">
                  {k.prefix ?? k.key_prefix ?? 'tk_'}••••••••
                </p>
              </div>
              <span className="text-xs text-earth-600">
                {k.created_at ? new Date(k.created_at).toLocaleDateString('pl-PL') : ''}
              </span>
            </GlassCard>
          ))}
        </div>
      )}

      <GlassCard className="p-4">
        <p className="text-xs text-earth-500 mb-1">Dokumentacja API</p>
        <a href="/api/docs" target="_blank" rel="noopener noreferrer"
           className="text-accent-primary text-sm hover:underline">
          Otwórz Swagger UI →
        </a>
      </GlassCard>
    </div>
  );
}

// ─── Shared micro-components ──────────────────────────────────────────────────

const INPUT = 'w-full bg-earth-800/60 border border-earth-700/60 rounded-xl px-4 py-2.5 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-accent-primary/60';

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-earth-500 mb-1.5">{label}</label>
      {children}
    </div>
  );
}

function Spinner() {
  return (
    <div className="flex items-center gap-2 text-earth-600 text-sm py-4">
      <Loader2 className="w-4 h-4 animate-spin" /> Ładowanie...
    </div>
  );
}

function Btn({
  children, onClick, loading, icon, disabled, variant = 'primary',
}: {
  children: React.ReactNode;
  onClick: () => void;
  loading?: boolean;
  icon?: React.ReactNode;
  disabled?: boolean;
  variant?: 'primary' | 'ghost';
}) {
  const base = 'flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50';
  const styles = variant === 'primary'
    ? `${base} bg-accent-primary text-earth-950 hover:bg-emerald-400`
    : `${base} bg-accent-primary/15 text-accent-primary hover:bg-accent-primary/25`;
  return (
    <button onClick={onClick} disabled={loading || disabled} className={styles}>
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : icon}
      {children}
    </button>
  );
}
