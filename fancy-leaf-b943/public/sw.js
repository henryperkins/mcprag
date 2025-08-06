const CACHE_NAME = 'claude-code-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
];

// Install event - pre-cache critical resources
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames
            .filter(name => name !== CACHE_NAME)
            .map(name => caches.delete(name))
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - network-first for API, cache-first for static
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Network-first for API requests
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .catch(() => new Response(
          JSON.stringify({ error: 'Offline' }),
          { headers: { 'Content-Type': 'application/json' } }
        ))
    );
    return;
  }
  
  // Cache-first for static assets
  event.respondWith(
    caches.match(request)
      .then(response => {
        if (response) return response;
        
        return fetch(request).then(response => {
          // Don't cache non-successful responses
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }
          
          // Clone the response
          const responseToCache = response.clone();
          
          caches.open(CACHE_NAME)
            .then(cache => {
              // Cache with short TTL for HTML
              if (request.url.endsWith('.html') || request.url === '/') {
                // Skip caching HTML to avoid staleness
                return;
              }
              // Only cache supported schemes (http/https)
              if (request.url.startsWith('http://') || request.url.startsWith('https://')) {
                cache.put(request, responseToCache).catch(err => {
                  console.warn('Cache put failed:', err);
                });
              }
            });
          
          return response;
        });
      })
  );
});