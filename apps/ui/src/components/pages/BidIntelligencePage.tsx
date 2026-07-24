"use client";

import { useCallback, useState, useEffect } from "react";
import { useAuthFetch } from "@/lib/api-v2";
import { PageShell } from "@/components/PageShell";
import { GlassCard } from "@/components/ui/GlassCard";
import { TrendingUp, Target, BarChart2, FileText, Award } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface BidRecord {
  id: string;
  tender_id: string;
  title: string;
  our_price: number | null;
  winning_price: number | null;
  rank_position: number | null;
  won: boolean;
  markup_pct: number | null;
  bid_date: string | null;
}

interface BidStats {
  total_bids: number;
  win_rate_pct: number;
  avg_markup_pct: number;
  avg_rank: number;
  total_wins: number;
}

interface OptimalMarkup {
  sample_size: number;
  recommended_markup_pct: number;
  avg_winning_markup_pct: number;
  avg_losing_markup_pct: number;
  win_rate_pct: number;
  recommendation?: string;
}

interface LeaderboardItem {
  id: string;
  title: string;
  score_total: number | null;
  percentile_rank: number | null;
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function BidIntelligencePage() {
  const authFetch = useAuthFetch();
  const [bids, setBids] = useState<BidRecord[]>([]);
  const [stats, setStats] = useState<BidStats | null>(null);
  const [optimalMarkup, setOptimalMarkup] = useState<OptimalMarkup | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const silentGet = useCallback(
    async <T,>(url: string): Promise<T | null> => {
      try {
        return await authFetch(url) as T;
      } catch {
        return null;
      }
    },
    [authFetch],
  );

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      try {
        const [bidsRes, markupRes, statsRes, leaderboardRes] = await Promise.all([
          silentGet<BidRecord[]>('/api/v2/bid-intelligence?limit=20'),
          silentGet<OptimalMarkup>('/api/v2/bid-intelligence/optimal-markup'),
          silentGet<BidStats>('/api/v2/bid-intelligence/stats'),
          silentGet<{ items: LeaderboardItem[]; total: number }>('/api/v2/scoring/leaderboard?limit=10'),
        ]);

        if (cancelled) return;

        if (Array.isArray(bidsRes)) setBids(bidsRes);
        if (markupRes) setOptimalMarkup(markupRes);
        if (statsRes) setStats(statsRes);
        if (leaderboardRes?.items) setLeaderboard(leaderboardRes.items);
      } catch (e: unknown) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();
    return () => { cancelled = true; };
  }, [silentGet]);

  return (
    <PageShell
      title="Bid Intelligence"
      subtitle="Analiza historii ofertowania i rekomendacje"
    >
      {/* Loading skeletons */}
      {loading && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 rounded-xl bg-ink-900/50 animate-shimmer" />
            ))}
          </div>
          <div className="h-80 rounded-xl bg-ink-900/50 animate-shimmer" />
        </div>
      )}

      {error && !loading && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400 mb-4">
          Błąd ładowania danych: {error}
        </div>
      )}

      {/* Stats Cards */}
      {!loading && stats && (
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: 'Łącznie ofert',   value: String(stats.total_bids),                                    icon: FileText,   color: 'text-slate-100' },
            { label: 'Win Rate',         value: `${(stats.win_rate_pct ?? 0).toFixed(1)}%`,                 icon: TrendingUp, color: 'text-success'   },
            { label: 'Wygrane',          value: String(stats.total_wins ?? 0),                               icon: Award,      color: 'text-success'   },
            { label: 'Śr. rank',         value: stats.avg_rank ? stats.avg_rank.toFixed(1) : '—',           icon: BarChart2,  color: 'text-slate-100' },
          ].map(s => (
            <div key={s.label} className="card rounded-xl p-5 shadow-md-sm">
              <div className="flex items-center gap-2 text-slate-500 text-xs mb-2">
                <s.icon size={14} /> {s.label}
              </div>
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Optimal Markup Card */}
      {!loading && optimalMarkup && optimalMarkup.sample_size > 0 && (
        <div className="mb-6 card rounded-xl p-5 shadow-md-sm">
          <div className="flex items-center gap-2 mb-3">
            <Target size={16} className="text-em" />
            <h2 className="text-sm font-semibold text-slate-100">Optymalny Markup</h2>
            <span className="ml-auto text-xs text-slate-500">{optimalMarkup.sample_size} próbek</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Rekomendowany',    value: `${(optimalMarkup.recommended_markup_pct ?? 0).toFixed(1)}%`,   color: 'text-em' },
              { label: 'Śr. wygrywający',  value: `${(optimalMarkup.avg_winning_markup_pct ?? 0).toFixed(1)}%`,   color: 'text-success' },
              { label: 'Śr. przegrywający', value: `${(optimalMarkup.avg_losing_markup_pct ?? 0).toFixed(1)}%`,  color: 'text-danger' },
              { label: 'Win Rate',          value: `${(optimalMarkup.win_rate_pct ?? 0).toFixed(1)}%`,            color: 'text-info' },
            ].map(k => (
              <div key={k.label} className="bg-ink-900/60 rounded-lg p-3">
                <div className="text-xs text-slate-500 mb-1">{k.label}</div>
                <div className={`text-xl font-bold ${k.color}`}>{k.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scoring Leaderboard */}
      {!loading && leaderboard.length > 0 && (
        <div className="mb-6 card rounded-xl overflow-hidden shadow-md-sm">
          <div className="border-b border-ink-800/60 px-6 py-4 flex items-center gap-2">
            <Award size={15} className="text-em" />
            <h2 className="text-base font-semibold text-slate-100">Top Przetargi (Scoring)</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-800/60 text-left text-xs text-slate-500">
                  <th className="px-6 py-3 font-medium">#</th>
                  <th className="px-6 py-3 font-medium">Przetarg</th>
                  <th className="px-6 py-3 font-medium">Score</th>
                  <th className="px-6 py-3 font-medium">Percentyl</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((item, idx) => (
                  <tr key={item.id} className="border-b border-ink-900 last:border-0 hover:bg-ink-900/40 transition-colors">
                    <td className="px-6 py-3 text-slate-500 font-mono">{idx + 1}</td>
                    <td className="px-6 py-3 text-slate-200 max-w-xs truncate">{item.title || item.id}</td>
                    <td className="px-6 py-3 text-em font-bold font-mono">{(item.score_total ?? 0).toFixed(1)}</td>
                    <td className="px-6 py-3 text-slate-400 font-mono">
                      {item.percentile_rank != null ? `${item.percentile_rank.toFixed(0)}p` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Bid History Table */}
      {!loading && (
        <div className="card rounded-xl overflow-hidden shadow-md-sm">
          <div className="border-b border-ink-800/60 px-6 py-4">
            <h2 className="text-base font-semibold text-slate-100">Historia ofert</h2>
          </div>
          {bids.length === 0 ? (
            <GlassCard className="flex flex-col items-center justify-center py-16">
              <FileText size={48} className="text-slate-600 mb-3" />
              <p className="text-sm text-slate-400">Brak historii ofert</p>
              <p className="text-xs text-slate-500">Złóż oferty na przetargi, aby zobaczyć analitykę</p>
            </GlassCard>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-ink-800/60 text-left text-xs text-slate-500">
                    <th className="px-6 py-3 font-medium">Przetarg</th>
                    <th className="px-6 py-3 font-medium">Data</th>
                    <th className="px-6 py-3 font-medium">Markup</th>
                    <th className="px-6 py-3 font-medium">Nasza cena</th>
                    <th className="px-6 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {bids.map((bid) => (
                    <tr key={bid.id} className="border-b border-ink-900 last:border-0 hover:bg-ink-900/40 transition-colors">
                      <td className="px-6 py-3 text-slate-200 max-w-xs truncate">{bid.title || bid.tender_id}</td>
                      <td className="px-6 py-3 text-slate-400">
                        {bid.bid_date ? new Date(bid.bid_date).toLocaleDateString('pl-PL') : '—'}
                      </td>
                      <td className="px-6 py-3 text-slate-200 font-mono">
                        {bid.markup_pct != null ? `${bid.markup_pct}%` : '—'}
                      </td>
                      <td className="px-6 py-3 text-slate-200 font-mono">
                        {bid.our_price != null ? bid.our_price.toLocaleString('pl-PL') + ' PLN' : '—'}
                      </td>
                      <td className="px-6 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          bid.won ? 'text-success bg-success/10' : 'text-danger bg-danger/10'
                        }`}>
                          {bid.won ? 'Wygrana' : 'Przegrana'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </PageShell>
  );
}
