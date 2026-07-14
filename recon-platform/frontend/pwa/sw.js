// Service Worker for Recon Platform PWA
const CACHE_NAME = 'recon-platform-v2.0.0';
const RUNTIME_CACHE = 'recon-runtime-v2.0.0';
const DATA_CACHE = 'recon-data-v2.0.0';

const STATIC_FILES = [
  '/',
  '/index.html',
  '/dashboard',
  '/scans',
  '/lab',
  '/admin/',
  '/static/css/main.css',
  '/static/js/main.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  'https://cdn.tailwindcss.com',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap'
];

const API_CACHEABLE = [
  '/api/v1/auth/me',
  '/api/v1/scans/my',
  '/api/v1/lab/functions',
  '/api/v1/subscription'
];

// Install
self.addEventListener('install', (event) => {
  console.log('[SW] Installing v2.0.0');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_FILES).catch((err) => console.warn('[SW] Cache miss:', err));
    })
  );
  self.skipWaiting();
});

// Activate
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating v2.0.0');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME && name !== RUNTIME_CACHE && name !== DATA_CACHE)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch - Network First, fallback to Cache
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== 'GET') return;
  // API calls - Network first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request, DATA_CACHE));
    return;
  }
  // Static files - Cache first
  if (STATIC_FILES.some((f) => url.pathname === f || request.url === f)) {
    event.respondWith(cacheFirst(request, CACHE_NAME));
    return;
  }
  // Other - Network first with cache fallback
  event.respondWith(networkFirst(request, RUNTIME_CACHE));
});

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (e) {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: 'Offline', cached: false }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (e) {
    return new Response('Offline', { status: 503 });
  }
}

// Push notifications
self.addEventListener('push', (event) => {
  let data = { title: 'Recon Platform', body: 'New notification', icon: '/static/icons/icon-192x192.png' };
  if (event.data) {
    try { data = { ...data, ...event.data.json() }; } catch (e) {}
  }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon,
      badge: '/static/icons/badge-72x72.png',
      vibrate: [200, 100, 200],
      tag: data.tag || 'recon-notification',
      data: data.url || '/',
      actions: data.actions || [
        { action: 'open', title: 'Open' },
        { action: 'dismiss', title: 'Dismiss' }
      ]
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  event.waitUntil(clients.openWindow(event.notification.data || '/'));
});

// Background sync
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-scans') {
    event.waitUntil(syncOfflineScans());
  }
});

async function syncOfflineScans() {
  const db = await openDB();
  const tx = db.transaction('pending_scans', 'readonly');
  const store = tx.objectStore('pending_scans');
  const scans = await store.getAll();
  for (const scan of scans) {
    try {
      await fetch('/api/v1/scans', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${scan.token}` },
        body: JSON.stringify(scan.data)
      });
      const delTx = db.transaction('pending_scans', 'readwrite');
      delTx.objectStore('pending_scans').delete(scan.id);
    } catch (e) { console.error('[SW] Sync failed:', e); }
  }
}

function openDB() {
  return new Promise((resolve) => {
    const req = indexedDB.open('recon-offline', 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains('pending_scans')) {
        db.createObjectStore('pending_scans', { keyPath: 'id', autoIncrement: true });
      }
    };
    req.onsuccess = () => resolve(req.result);
  });
}
