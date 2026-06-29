'use client';

import { motion } from 'motion/react';
import { useState } from 'react';
import {
  Database, HardDrive, Shield, Activity,
  CheckCircle2, AlertTriangle, Clock, RefreshCw,
  Layers,
} from 'lucide-react';

export function SystemPage() {
  const [tier, setTier] = useState(3);
  const [backupStatus, setBackupStatus] = useState<'ok' | 'running' | 'never_run'>('ok');
  const [lastBackup, setLastBackup] = useState('2026-07-01 08:00:03');

  const auditEntries = [
    { id: 1, at: '2026-07-01 10:30:12', actor: 'system', action: 'approved:rfq_send', entity: 'approval_request' },
    { id: 2, at: '2026-07-01 10:28:45', actor: 'learning_loop', action: 'contract_close_calibration', entity: 'contract' },
    { id: 3, at: '2026-07-01 09:15:00', actor: 'chat_brain', action: 'estimate_edit', entity: 'estimate' },
    { id: 4, at: '2026-07-01 09:01:45', actor: 'system', action: 'approved:plan_dispatch', entity: 'approval_request' },
    { id: 5, at: '2026-06-30 16:00:00', actor: 'system', action: 'rejected', entity: 'approval_request' },
  ];

  const tierFeatures = [
    { tier: 1, label: 'Zwiad BZP', features: ['Ingest', 'Match CPV/Geo', 'Dokumenty', 'Analiza'] },
    { tier: 2, label: 'Silnik', features: ['Engine L1 (Clingo)', 'Engine L2 (Monte Carlo)', 'Kosztorys', 'RFQ', 'Chat-brain'] },
    { tier: 3, label: 'Mózg', features: ['Logistyka (OR-Tools)', 'Plany dzienne', 'Mobile', 'Pipeline', 'Learning loop'] },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="p-8 space-y-6"
    >
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-earth-50">System</h1>
        <p className="text-earth-400 mt-1">
          Backup, observability, tier flags, audit log
        </p>
      </div>

      {/* Status cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-earth-900/60 border border-earth-800">
          <div className="flex items-center gap-2 mb-2">
            <Database className="w-4 h-4 text-green-400" />
            <span className="text-earth-400 text-sm">PostgreSQL</span>
          </div>
          <p className="text-earth-100 font-mono text-lg">OK</p>
          <p className="text-earth-500 text-xs">pgvector + pgcrypto</p>
        </div>
        <div className="p-4 rounded-xl bg-earth-900/60 border border-earth-800">
          <div className="flex items-center gap-2 mb-2">
            <HardDrive className="w-4 h-4 text-green-400" />
            <span className="text-earth-400 text-sm">Backup</span>
          </div>
          <p className="text-earth-100 font-mono text-lg">{backupStatus}</p>
          <p className="text-earth-500 text-xs">{lastBackup}</p>
        </div>
        <div className="p-4 rounded-xl bg-earth-900/60 border border-earth-800">
          <div className="flex items-center gap-2 mb-2">
            <Layers className="w-4 h-4 text-amber-400" />
            <span className="text-earth-400 text-sm">Tier</span>
          </div>
          <p className="text-amber-400 font-mono text-lg">TIER={tier}</p>
          <p className="text-earth-500 text-xs">Pełna funkcjonalność</p>
        </div>
        <div className="p-4 rounded-xl bg-earth-900/60 border border-earth-800">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-green-400" />
            <span className="text-earth-400 text-sm">Testy</span>
          </div>
          <p className="text-green-400 font-mono text-lg">230/230</p>
          <p className="text-earth-500 text-xs">All green ✓</p>
        </div>
      </div>

      {/* Tier flags */}
      <div className="p-5 rounded-xl bg-earth-900/60 border border-earth-800">
        <h2 className="text-earth-200 font-medium mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4" />
          Feature Flags (TIER={tier})
        </h2>
        <div className="grid grid-cols-3 gap-4">
          {tierFeatures.map(t => (
            <div
              key={t.tier}
              className={`p-4 rounded-lg border ${
                t.tier <= tier
                  ? 'bg-green-500/5 border-green-500/30'
                  : 'bg-earth-800/30 border-earth-700/30 opacity-50'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                {t.tier <= tier ? (
                  <CheckCircle2 className="w-4 h-4 text-green-400" />
                ) : (
                  <Clock className="w-4 h-4 text-earth-500" />
                )}
                <span className="text-earth-200 font-medium">
                  Tier {t.tier} — {t.label}
                </span>
              </div>
              <ul className="space-y-1">
                {t.features.map(f => (
                  <li key={f} className="text-earth-400 text-xs flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      t.tier <= tier ? 'bg-green-400' : 'bg-earth-600'
                    }`} />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Backup controls */}
      <div className="p-5 rounded-xl bg-earth-900/60 border border-earth-800">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-earth-200 font-medium flex items-center gap-2">
            <HardDrive className="w-4 h-4" />
            Backup / Disaster Recovery
          </h2>
          <button
            onClick={() => {
              setBackupStatus('running');
              setTimeout(() => {
                setBackupStatus('ok');
                setLastBackup(new Date().toISOString().slice(0, 19).replace('T', ' '));
              }, 2000);
            }}
            className="px-3 py-1.5 rounded-lg bg-earth-800 text-earth-200 hover:bg-earth-700 text-sm flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${backupStatus === 'running' ? 'animate-spin' : ''}`} />
            Wykonaj backup
          </button>
        </div>
        <div className="text-earth-400 text-sm space-y-1">
          <p>Format: <span className="font-mono text-earth-300">pg_dump --format=custom --compress=9</span></p>
          <p>Lokalizacja: <span className="font-mono text-earth-300">/tmp/terra_backups/</span></p>
          <p>Ostatni backup: <span className="font-mono text-earth-300">{lastBackup}</span></p>
        </div>
      </div>

      {/* Audit log */}
      <div className="p-5 rounded-xl bg-earth-900/60 border border-earth-800">
        <h2 className="text-earth-200 font-medium mb-4 flex items-center gap-2">
          <Shield className="w-4 h-4" />
          Audit Log (ostatnie wpisy)
        </h2>
        <div className="overflow-hidden rounded-lg border border-earth-700/50">
          <table className="w-full text-sm">
            <thead className="bg-earth-800/50">
              <tr>
                <th className="px-3 py-2 text-left text-earth-400 font-medium">Czas</th>
                <th className="px-3 py-2 text-left text-earth-400 font-medium">Aktor</th>
                <th className="px-3 py-2 text-left text-earth-400 font-medium">Akcja</th>
                <th className="px-3 py-2 text-left text-earth-400 font-medium">Encja</th>
              </tr>
            </thead>
            <tbody>
              {auditEntries.map(e => (
                <tr key={e.id} className="border-t border-earth-800/50 hover:bg-earth-800/30">
                  <td className="px-3 py-2 text-earth-300 font-mono text-xs">{e.at}</td>
                  <td className="px-3 py-2 text-earth-300">{e.actor}</td>
                  <td className="px-3 py-2">
                    <span className={`px-1.5 py-0.5 rounded text-xs font-mono ${
                      e.action.includes('approved') ? 'bg-green-500/20 text-green-400' :
                      e.action.includes('rejected') ? 'bg-red-500/20 text-red-400' :
                      'bg-earth-700 text-earth-300'
                    }`}>
                      {e.action}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-earth-400 text-xs">{e.entity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  );
}
