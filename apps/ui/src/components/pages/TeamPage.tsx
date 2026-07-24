'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Users, Shield, Mail, MoreHorizontal, Plus, Crown, UserCog, Eye, X, Loader2 } from 'lucide-react';
import { PageShell } from '@/components/PageShell';
import { useAuthFetch } from '@/lib/api-v2';
import { showToast } from '@/components/Toast';

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: 'owner' | 'admin' | 'manager' | 'viewer';
  avatar_initials: string;
  last_active: string;
  projects: number;
}

// No more DEMO data — fetched from /api/v1/resources/employees

const ROLE_META: Record<string, { label: string; icon: React.ReactNode; bg: string }> = {
  owner:    { label: 'Właściciel',    icon: <Crown   className="w-3 h-3" />, bg: 'bg-warning/10 text-warning border-warning/20' },
  admin:    { label: 'Administrator', icon: <Shield  className="w-3 h-3" />, bg: 'bg-violet/10 text-violet border-violet/20' },
  manager:  { label: 'Kierownik',     icon: <UserCog className="w-3 h-3" />, bg: 'bg-info/10 text-info border-info/20' },
  operator: { label: 'Operator',      icon: <UserCog className="w-3 h-3" />, bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  editor:   { label: 'Redaktor',      icon: <UserCog className="w-3 h-3" />, bg: 'bg-sky-500/10 text-sky-400 border-sky-500/20' },
  viewer:   { label: 'Podgląd',       icon: <Eye     className="w-3 h-3" />, bg: 'bg-ink-700/30 text-slate-400 border-ink-700/40' },
};
const DEFAULT_ROLE_META = { label: 'Członek', icon: <Eye className="w-3 h-3" />, bg: 'bg-ink-700/30 text-slate-400 border-ink-700/40' };

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item      = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: { duration: 0.3 } } };

export function TeamPage() {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('viewer');
  const authFetch = useAuthFetch();

  const fetchMembers = useCallback(() => {
    authFetch('/api/v2/organizations/me/members')
      .then((data: any) => {
        const items = (data.items ?? data ?? []).map((e: any) => ({
          id: e.id,
          name: e.name ?? '—',
          email: e.email ?? '—',
          role: (e.role ?? 'viewer') as any,
          avatar_initials: (e.name ?? '??').split(' ').map((w: string) => w[0]).join('').slice(0, 2).toUpperCase(),
          last_active: e.is_active ? 'Aktywny' : 'Nieaktywny',
          projects: 0,
        }));
        setMembers(items);
      })
      .catch(() => {
        // Fallback to employees endpoint
        authFetch('/api/v1/resources/employees')
          .then((data: any) => {
            const items = (data.items ?? data ?? []).map((e: any) => ({
              id: e.id, name: e.name ?? '—', email: e.phone ?? '—',
              role: (e.role ?? 'viewer') as any,
              avatar_initials: (e.name ?? '??').split(' ').map((w: string) => w[0]).join('').slice(0, 2).toUpperCase(),
              last_active: e.active ? 'Aktywny' : 'Nieaktywny', projects: 0,
            }));
            setMembers(items);
          })
          .catch(() => {});
      })
      .finally(() => setLoading(false));
  }, [authFetch]);

  useEffect(() => { fetchMembers(); }, [fetchMembers]);

  const handleInvite = useCallback(async () => {
    const emailTrimmed = inviteEmail.trim();
    if (!emailTrimmed || !emailTrimmed.includes('@')) { showToast('error', 'Podaj poprawny adres email'); return; }
    setSaving(true);
    try {
      await authFetch('/api/v2/organizations/me/invite', {
        method: 'POST',
        body: JSON.stringify({ email: emailTrimmed, role: inviteRole }),
      });
      showToast('success', `Zaproszenie wysłane na ${emailTrimmed}`);
      setShowModal(false);
      setInviteEmail('');
      setInviteRole('viewer');
    } catch (e) {
      showToast('error', (e as Error).message || 'Błąd wysyłania zaproszenia');
    } finally {
      setSaving(false);
    }
  }, [authFetch, inviteEmail, inviteRole]);

  const actions = (
    <button type="button" onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
      <Plus className="w-4 h-4" /> Zaproś użytkownika
    </button>
  );

  return (
    <PageShell title="Zespół" subtitle="Zarządzanie użytkownikami i rolami" actions={actions}>
      <motion.div className="flex flex-col gap-6" variants={container} initial="hidden" animate="show">

        {/* Stats */}
        <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Członkowie',     value: members.length },
            { label: 'Administratorzy', value: members.filter(m => m.role === 'owner' || m.role === 'admin').length },
            { label: 'Kierownicy',     value: members.filter(m => m.role === 'manager').length },
            { label: 'Aktywni dziś',   value: members.filter(m => m.last_active.includes('min') || m.last_active.includes('h temu')).length },
          ].map(s => (
            <div key={s.label} className="card rounded-xl p-4 shadow-md-sm">
              <p className="text-slate-500 text-xs mb-1">{s.label}</p>
              <p className="text-2xl font-bold text-slate-200">{s.value}</p>
            </div>
          ))}
        </motion.div>

        {/* Roles legend */}
        <motion.div variants={item} className="flex items-center gap-4 text-xs text-slate-500">
          <span>Role:</span>
          {Object.entries(ROLE_META).map(([key, meta]) => (
            <span key={key} className={`flex items-center gap-1 px-2 py-0.5 rounded-full border ${meta.bg}`}>
              {meta.icon} {meta.label}
            </span>
          ))}
        </motion.div>

        {/* Members Table */}
        <motion.div variants={item} className="card rounded-xl overflow-hidden shadow-md-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink-800/60 text-slate-500 text-xs">
                <th className="text-left px-5 py-3 font-medium">Użytkownik</th>
                <th className="text-left px-4 py-3 font-medium">Rola</th>
                <th className="text-left px-4 py-3 font-medium">Projekty</th>
                <th className="text-left px-4 py-3 font-medium">Ostatnia aktywność</th>
                <th className="text-right px-4 py-3 font-medium w-12"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-800/30">
              {members.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-16 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <Users className="w-10 h-10 text-slate-600" />
                      <p className="text-slate-400 text-sm font-medium">Brak członków zespołu</p>
                      <p className="text-slate-600 text-xs">Zaproś pierwszego użytkownika</p>
                    </div>
                  </td>
                </tr>
              )}
              {members.map(m => {
                const meta = ROLE_META[m.role] ?? DEFAULT_ROLE_META;
                return (
                  <tr key={m.id} className="hover:bg-ink-800/20 transition-colors">
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-em/30 to-slate/30 flex items-center justify-center text-xs font-bold text-slate-200 border border-ink-700/40">
                          {m.avatar_initials}
                        </div>
                        <div>
                          <p className="text-slate-200 font-medium">{m.name}</p>
                          <p className="text-slate-500 text-xs flex items-center gap-1">
                            <Mail className="w-3 h-3" /> {m.email}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border font-medium ${meta.bg}`}>
                        {meta.icon} {meta.label}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-slate-400">{m.projects}</td>
                    <td className="px-4 py-4 text-slate-500 text-xs">{m.last_active}</td>
                    <td className="px-4 py-4 text-right">
                      <button type="button" className="p-1.5 rounded-md hover:bg-ink-800/60 text-slate-500 hover:text-slate-300 transition-colors">
                        <MoreHorizontal className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </motion.div>
      </motion.div>

      {/* Invite Modal */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={(e) => { if (e.target === e.currentTarget) setShowModal(false); }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}
              className="glass-card w-full max-w-sm mx-4 p-6 flex flex-col gap-4"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-slate-100">Zaproś użytkownika</h3>
                <button type="button" onClick={() => setShowModal(false)} className="p-1 rounded-md hover:bg-ink-700/60 text-slate-500 hover:text-slate-300 transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex flex-col gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Adres email *</label>
                  <input
                    type="email" value={inviteEmail}
                    onChange={e => setInviteEmail(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') handleInvite(); }}
                    placeholder="jan@firma.pl"
                    className="w-full bg-ink-800/60 border border-ink-700/60 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-em/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Rola</label>
                  <select value={inviteRole} onChange={e => setInviteRole(e.target.value)}
                    className="w-full bg-ink-800/60 border border-ink-700/60 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-em/50">
                    <option value="viewer">Podgląd</option>
                    <option value="manager">Kierownik</option>
                    <option value="admin">Administrator</option>
                  </select>
                </div>
                <p className="text-xs text-slate-500">Użytkownik otrzyma link aktywacyjny na podany adres.</p>
              </div>
              <div className="flex gap-2 pt-1">
                <button type="button" onClick={() => setShowModal(false)} className="btn-ghost flex-1 justify-center">Anuluj</button>
                <button type="button" onClick={handleInvite} disabled={saving} className="btn-primary flex-1 justify-center disabled:opacity-60">
                  {saving ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Wysyłam...</> : 'Wyślij zaproszenie'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </PageShell>
  );
}
