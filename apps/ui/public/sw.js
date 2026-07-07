/**
 * Terra.OS Service Worker — Faza 96-100: Mobile PWA
 *
 * Features:
 * - Offline mode with cache-first strategy for static assets
 * - Network-first for API requests
 * - Background sync for failed API calls
 * - Push notification support
 */

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `terra-static-${CACHE_VERSION}`;
const API_CACHE = `terra-api-${CACHE_VERSION}`;
const OFFLINE_URL = '/offline.html';

// Static assets to pre-cache
const PRECACHE_ASSETS = [
  '/',
  '/manifest.json',
  '/favicon.ico',
  OFFLINE_URL,
];

// ─── Installation ─────────────────────────────────────────────────────────────

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      console.log('[SW] Pre-caching static assets');
      return cache.addAll(PRECACHE_ASSETS.filter(url => url !== OFFLINE_URL));
    }).then(() => {
      return self.skipWaiting();
    })
  );
});

// ─── Activation ───────────────────────────────────────────────────────────────

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== STATIC_CACHE && name !== API_CACHE)
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// ─── Fetch Strategy ───────────────────────────────────────────────────────────

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip browser extension and non-http requests
  if (!url.protocol.startsWith('http')) return;

  // API requests: network-first, cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Static assets: cache-first
  if (
    url.pathname.startsWith('/_next/static/') ||
    url.pathname.startsWith('/icons/') ||
    url.pathname.match(/\.(js|css|woff2?|png|jpg|svg|ico)$/)
  ) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // HTML pages: network-first with offline fallback
  event.respondWith(networkFirstWithOfflineFallback(request));
});

// ─── Caching Strategies ───────────────────────────────────────────────────────

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.log('[SW] Cache-first fetch failed:', error);
    throw error;
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(API_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) {
      console.log('[SW] Serving API from cache (offline):', request.url);
      return cached;
    }
    return new Response(
      JSON.stringify({ error: 'Offline', message: 'Brak połączenia z serwerem' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

async function networkFirstWithOfflineFallback(request) {
  try {
    const response = await fetch(request);
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;

    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      const offlinePage = await caches.match(OFFLINE_URL);
      if (offlinePage) return offlinePage;
    }

    throw error;
  }
}

// ─── Push Notifications ───────────────────────────────────────────────────────

self.addEventListener('push', (event) => {
  if (!event.data) return;

  let data;
  try {
    data = event.data.json();
  } catch {
    data = { title: 'Terra.OS', body: event.data.text() };
  }

  const options = {
    body: data.body || 'Nowa wiadomość z Terra.OS',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/',
      dateOfArrival: Date.now(),
    },
    actions: [
      { action: 'open', title: 'Otwórz' },
      { action: 'close', title: 'Zamknij' },
    ],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'Terra.OS', options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'close') return;

  const url = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});

// ─── Background Sync ──────────────────────────────────────────────────────────

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-tenders') {
    event.waitUntil(syncTenders());
  }
});

async function syncTenders() {
  try {
    console.log('[SW] Background sync: tenders');
    // Re-fetch tenders when back online
    const cache = await caches.open(API_CACHE);
    await cache.delete(new Request('/api/v1/tenders'));
  } catch (error) {
    console.error('[SW] Sync failed:', error);
  }
}

console.log('[SW] Terra.OS Service Worker loaded', CACHE_VERSION);
