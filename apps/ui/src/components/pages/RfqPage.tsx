'use client';

import { motion } from 'motion/react';
import { useState } from 'react';
import {
  Mail, CheckCircle, XCircle, Clock, Send,
  FileText, AlertTriangle, Shield,
} from 'lucide-react';

// Mock approval requests
type Approval = {
  id: string;
  action: string;
  status: 'pending' | 'approved' | 'rejected';
  requested_at: string;
  payload: Record<string, any>;
};

const mockApprovals: Approval[] = [
  {
    id: 'ap-001',
    action: 'rfq_send',
    status: 'pending' as const,
    requested_at: '2026-07-01 09:23',
    payload: {
      scope_desc: 'Usługi odwodnienia wykopu — Kontrakt A46/GDDKiA',
      counterparties: ['hydro-tech@example.com', 'odwodnienia24@example.com'],
    },
  },
  {
    id: 'ap-002',
    action: 'plan_dispatch',
    status: 'pending' as const,
    requested_at: '2026-07-01 10:05',
    payload: { plan_id: 'plan-x', day: '2026-07-02' },
  },
  {
    id: 'ap-003',
    action: 'rfq_send',
    status: 'approved' as const,
    requested_at: '2026-06-30 14:00',
    payload: {
      scope_desc: 'Dostawa kruszywa 0-31.5 — 400 ton',
      counterparties: ['kruszywa-pl@example.com'],
    },
  },
  {
    id: 'ap-004',
    action: 'autofill_submit',
    status: 'rejected' as const,
    requested_at: '2026-06-29 16:45',
    payload: { tender_id: 'tender-y', note: 'Autofill draft' },
  },
];

const mockRfqs = [
  {
    id: 'rfq-001',
    scope_desc: 'Dostawa kruszywa 0-31.5 — 400 ton',
    status: 'received',
    messages: 3,
    offers: [
      { counterparty: 'Kruszywa Nowak', price_net_pln: 38500, lead_time_days: 14 },
      { counterparty: 'HydroTech Sp. z o.o.', price_net_pln: 42000, lead_time_days: 10 },
    ],
  },
  {
    id: 'rfq-002',
    scope_desc: 'Usługi odwodnienia wykopu',
    status: 'sent',
    messages: 2,
    offers: [],
  },
];

export function RfqPage() {
  const [tab, setTab] = useState<'approvals' | 'rfq'>('approvals');
  const [approvals, setApprovals] = useState<Approval[]>(mockApprovals);

  const handleApprove = (id: string) => {
    setApprovals(prev =>
      prev.map(a => a.id === id ? { ...a, status: 'approved' as const } : a)
    );
  };

  const handleReject = (id: string) => {
    setApprovals(prev =>
      prev.map(a => a.id === id ? { ...a, status: 'rejected' as const } : a)
    );
  };

  const pending = approvals.filter(a => a.status === 'pending');

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="p-8 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-earth-50">RFQ & Zatwierdzenia</h1>
          <p className="text-earth-400 mt-1">
            Zapytania ofertowe i bramka zatwierdzania — każda akcja zewnętrzna wymaga Twojej decyzji
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-amber-400" />
          <span className="text-amber-400 font-mono text-sm">
            {pending.length} oczekujących
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-earth-900 p-1 rounded-lg w-fit">
        <button
          onClick={() => setTab('approvals')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === 'approvals'
              ? 'bg-amber-500/20 text-amber-400'
              : 'text-earth-400 hover:text-earth-200'
          }`}
        >
          <Shield className="w-4 h-4 inline mr-2" />
          Zatwierdzenia ({pending.length})
        </button>
        <button
          onClick={() => setTab('rfq')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === 'rfq'
              ? 'bg-amber-500/20 text-amber-400'
              : 'text-earth-400 hover:text-earth-200'
          }`}
        >
          <Mail className="w-4 h-4 inline mr-2" />
          Zapytania ofertowe
        </button>
      </div>

      {/* Content */}
      {tab === 'approvals' && (
        <div className="space-y-3">
          {approvals.map(a => (
            <motion.div
              key={a.id}
              layout
              className={`p-4 rounded-xl border ${
                a.status === 'pending'
                  ? 'bg-earth-900/80 border-amber-500/30'
                  : a.status === 'approved'
                  ? 'bg-earth-900/40 border-green-500/20'
                  : 'bg-earth-900/40 border-red-500/20'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {a.action === 'rfq_send' && <Send className="w-5 h-5 text-blue-400" />}
                  {a.action === 'plan_dispatch' && <FileText className="w-5 h-5 text-teal-400" />}
                  {a.action === 'autofill_submit' && <AlertTriangle className="w-5 h-5 text-orange-400" />}
                  <div>
                    <p className="text-earth-100 font-medium">
                      {a.action === 'rfq_send' && 'Wysyłka zapytania ofertowego'}
                      {a.action === 'plan_dispatch' && 'Rozsyłka planu dziennego'}
                      {a.action === 'autofill_submit' && 'Auto-fill formularza'}
                    </p>
                    <p className="text-earth-400 text-sm mt-0.5">
                      {a.payload.scope_desc || `Plan: ${a.payload.day || a.payload.plan_id}`}
                    </p>
                    {a.payload.counterparties && (
                      <p className="text-earth-500 text-xs mt-1">
                        → {a.payload.counterparties.join(', ')}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-earth-500 text-xs">{a.requested_at}</span>
                  {a.status === 'pending' ? (
                    <>
                      <button
                        onClick={() => handleApprove(a.id)}
                        className="p-2 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors"
                      >
                        <CheckCircle className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleReject(a.id)}
                        className="p-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
                      >
                        <XCircle className="w-5 h-5" />
                      </button>
                    </>
                  ) : (
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      a.status === 'approved'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {a.status === 'approved' ? 'Zatwierdzone' : 'Odrzucone'}
                    </span>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {tab === 'rfq' && (
        <div className="space-y-4">
          {mockRfqs.map(rfq => (
            <div key={rfq.id} className="p-5 rounded-xl bg-earth-900/60 border border-earth-800">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-earth-100 font-medium">{rfq.scope_desc}</h3>
                <span className={`px-2 py-1 rounded text-xs font-mono ${
                  rfq.status === 'received'
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-blue-500/20 text-blue-400'
                }`}>
                  {rfq.status}
                </span>
              </div>
              <p className="text-earth-400 text-sm mb-3">
                {rfq.messages} wiadomości · {rfq.offers.length} ofert
              </p>
              {rfq.offers.length > 0 && (
                <div className="grid grid-cols-2 gap-2">
                  {rfq.offers.map((o, i) => (
                    <div key={i} className="p-3 rounded-lg bg-earth-800/50 border border-earth-700/50">
                      <p className="text-earth-200 text-sm font-medium">{o.counterparty}</p>
                      <div className="flex justify-between mt-1">
                        <span className="text-amber-400 font-mono text-sm">
                          {o.price_net_pln.toLocaleString('pl-PL')} PLN
                        </span>
                        <span className="text-earth-400 text-xs">{o.lead_time_days} dni</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
