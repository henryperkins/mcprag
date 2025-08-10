/**
 * Service Worker: cache strategy tuned for Cloudflare Workers + Vite
 * - Do NOT serve cached index.html by default (prevents stale UI after deploys)
 * - Network-first for navigations (HTML) with offline fallback to a cached index.html
 * - Network-first for API requests
 * - Cache-first for versioned static assets (hashed filenames)
 */
const CACHE_NAME = 'claude-code-static-v2';

// Precache only what's safe and useful for offline fallback
const PRECACHE_URLS = [
  '/index.html',            // offline fallback only (not used for normal loads)
  '/manifest.webmanifest',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) =>
        Promise.all(cacheNames.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
      )
      .then(() => self.clients.claim())
  );
});

// Cache-first helper for static assets
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  // Only cache successful same-origin responses
  if (
    response &&
    response.ok &&
    (request.url.startsWith('http://') || request.url.startsWith('https://'))
  ) {
    try {
      const cache = await caches.open(CACHE_NAME);
      await cache.put(request, response.clone());
    } catch (err) {
      console.warn('Cache put failed:', err);
    }
  }
  return response;
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Only handle GETs
  if (request.method !== 'GET') {
    return;
  }

  // API: always network-first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(
        () =>
          new Response(JSON.stringify({ error: 'Offline' }), {
            headers: { 'Content-Type': 'application/json' },
            status: 503,
          })
      )
    );
    return;
  }

  // Navigations (HTML): network-first with offline fallback to cached index.html
  const acceptsHTML =
    request.mode === 'navigate' ||
    (request.headers.get('accept') || '').includes('text/html');

  if (acceptsHTML) {
    event.respondWith(
      (async () => {
        try {
          // Ensure we bypass caches to pick up latest deploy
          const fresh = await fetch(request, { cache: 'no-store' });
          return fresh;
        } catch {
          const cache = await caches.open(CACHE_NAME);
          const fallback = await cache.match('/index.html');
          return (
            fallback ||
            new Response('Offline', {
              status: 503,
              headers: { 'content-type': 'text/plain' },
            })
          );
        }
      })()
    );
    return;
  }

  // Versioned static assets (safe to cache forever due to hashing)
  const isAsset =
    url.pathname.startsWith('/assets/') ||
    /\.(?:js|css|png|svg|jpg|jpeg|gif|webp|ico|woff2?|ttf|otf|map)$/.test(url.pathname);

  if (isAsset || url.pathname.startsWith('/icons/') || url.pathname === '/manifest.webmanifest') {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Default: cache-first as a conservative fallback
  event.respondWith(cacheFirst(request));
});