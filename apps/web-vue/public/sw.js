// Nova ERP PWA Service Worker
const CACHE_NAME = 'nova-erp-v2';

const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/manifest.json',
  '/favicon.svg',
  '/icons.svg',
  '/logo-icon.svg',
  '/logo-wordmark.svg',
  '/icons/icon-192.png',
  '/icons/icon-512.png'
];

// Install event: Pre-cache application shell and static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return Promise.allSettled(
        PRECACHE_ASSETS.map((asset) =>
          cache.add(asset).catch((err) => {
            console.warn(`[SW] Pre-cache failed for ${asset}:`, err);
          })
        )
      );
    }).then(() => self.skipWaiting())
  );
});

// Activate event: Clean up previous cache versions and claim clients
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event: Network-first for navigation, Cache-first / Stale-while-revalidate for static assets
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // Bypass service worker cache for API requests (handled dynamically by IndexedDB / SyncManager)
  if (url.pathname.startsWith('/api') || url.pathname.startsWith('/mcp')) {
    return;
  }

  // Handle SPA navigation requests: Network-first falling back to cached index.html shell
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put('/', responseClone));
          }
          return networkResponse;
        })
        .catch(async () => {
          const cachedIndex = await caches.match('/index.html') || await caches.match('/');
          if (cachedIndex) return cachedIndex;
          return new Response('Nova ERP is currently offline. Please reconnect.', {
            headers: { 'Content-Type': 'text/html' }
          });
        })
    );
    return;
  }

  // Handle static assets (scripts, styles, fonts, images)
  const isGoogleFont = url.hostname.includes('fonts.googleapis.com') || url.hostname.includes('fonts.gstatic.com');
  const isSameOrigin = url.origin === location.origin;

  if (isSameOrigin || isGoogleFont) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        if (cachedResponse) {
          // Stale-while-revalidate: return cached response immediately and revalidate in background
          fetch(event.request)
            .then((networkResponse) => {
              if (networkResponse && (networkResponse.status === 200 || networkResponse.type === 'opaque')) {
                caches.open(CACHE_NAME).then((cache) => cache.put(event.request, networkResponse));
              }
            })
            .catch(() => {});
          return cachedResponse;
        }

        // Cache miss: fetch from network and store in cache
        return fetch(event.request)
          .then((networkResponse) => {
            if (!networkResponse || (networkResponse.status !== 200 && networkResponse.type !== 'opaque')) {
              return networkResponse;
            }
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
            return networkResponse;
          })
          .catch(() => {
            if (event.request.destination === 'image') {
              return caches.match('/favicon.svg');
            }
            return new Response('', { status: 408, statusText: 'Offline' });
          });
      })
    );
  }
});
