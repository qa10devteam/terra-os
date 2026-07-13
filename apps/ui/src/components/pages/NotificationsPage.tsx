'use client';
import { useEffect, useState, useCallback } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import { GlassCard } from '@/components/ui/GlassCard';
import { motion } from 'motion/react';
import { Bell, Check, CheckCheck, Filter, X } from 'lucide-react';
import { useRealtime } from '@/hooks/useRealtime';

interface Notification {
  id: string;
  event_type: string;
  title: string;
  body: string;
  link?: string;
  read: boolean;
  created_at: string;
}

export function NotificationsPage() {
  const authFetch = useAuthFetch();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  // SSE: live notifications
  useRealtime({
    eventTypes: ['alert.deadline', 'tender.new', 'agent.done'],
    onEvent: () => fetchNotifs(),
  });

  const fetchNotifs = useCallback(async () => {
    try {
      const data = await authFetch(`/api/v2/notifications?limit=50&unread_only=${filter === 'unread'}`);
      setNotifications(Array.isArray(data) ? data : []);
    } catch {}
  }, [authFetch, filter]);

  useEffect(() => { fetchNotifs(); }, [fetchNotifs]);

  const markAllRead = async () => {
    await authFetch('/api/v2/notifications/mark-read', { method: 'POST', body: JSON.stringify([]) });
    fetchNotifs();
  };

  const markRead = async (id: string) => {
    await authFetch('/api/v2/notifications/mark-read', { method: 'POST', body: JSON.stringify([id]) });
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  const eventIcons: Record<string, string> = {
    'alert.deadline': '⏰',
    'tender.new': '📋',
    'agent.done': '🤖',
  };

  const eventColors: Record<string, string> = {
    'alert.deadline': 'border-l-yellow-500',
    'tender.new': 'border-l-blue-500',
    'agent.done': 'border-l-green-500',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-earth-100">Powiadomienia</h1>
          <p className="text-earth-400 text-sm mt-1">{unreadCount} nieprzeczytanych</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-1 bg-earth-900/60 rounded-lg p-1">
            <button
              onClick={() => setFilter('all')}
              className={`px-3 py-1 rounded text-xs ${filter === 'all' ? 'bg-blue-600 text-white' : 'text-earth-400'}`}
            >Wszystkie</button>
            <button
              onClick={() => setFilter('unread')}
              className={`px-3 py-1 rounded text-xs ${filter === 'unread' ? 'bg-blue-600 text-white' : 'text-earth-400'}`}
            >Nieprzeczytane</button>
          </div>
          {unreadCount > 0 && (
            <button onClick={markAllRead} className="px-3 py-1.5 bg-earth-800 hover:bg-earth-700 text-earth-300 rounded-lg text-xs flex items-center gap-1">
              <CheckCheck size={14} /> Oznacz wszystkie
            </button>
          )}
        </div>
      </div>

      <div className="space-y-2">
        {notifications.map((n, i) => (
          <motion.div
            key={n.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.03 }}
            className={`border-l-4 ${eventColors[n.event_type] || 'border-l-earth-600'} ${
              n.read ? 'opacity-60' : ''
            }`}
          >
            <div className="flex items-start gap-3 p-3 bg-earth-900/40 rounded-r-lg hover:bg-earth-800/50 transition-colors">
              <span className="text-lg mt-0.5">{eventIcons[n.event_type] || '📌'}</span>
              <div className="flex-1 min-w-0">
                <div className="text-earth-200 text-sm font-medium">{n.title}</div>
                {n.body && <div className="text-earth-400 text-xs mt-0.5">{n.body}</div>}
                <div className="text-earth-600 text-xs mt-1">
                  {new Date(n.created_at).toLocaleString('pl-PL')}
                </div>
              </div>
              {!n.read && (
                <button onClick={() => markRead(n.id)} className="text-earth-500 hover:text-green-400 p-1">
                  <Check size={14} />
                </button>
              )}
            </div>
          </motion.div>
        ))}
        {notifications.length === 0 && (
          <GlassCard className="p-8 text-center">
            <Bell size={32} className="mx-auto text-earth-600 mb-2" />
            <p className="text-earth-400 text-sm">Brak powiadomień</p>
          </GlassCard>
        )}
      </div>
    </div>
  );
}
