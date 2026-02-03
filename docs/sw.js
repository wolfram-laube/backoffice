// CRM Dashboard Service Worker - Offline Support
const CACHE_NAME = 'crm-dashboard-v1';
const OFFLINE_URLS = [
  '/ops/backoffice/crm-dashboard.html',
  '/ops/backoffice/manifest.json'
];

// Install - cache essential files
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('📦 Caching offline resources');
      return cache.addAll(OFFLINE_URLS);
    })
  );
  self.skipWaiting();
});

// Activate - clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

// Fetch - network first, fallback to cache
self.addEventListener('fetch', event => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') return;
  
  // Skip GitLab API calls (need fresh data)
  if (event.request.url.includes('gitlab.com/api')) {
    return;
  }
  
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Clone and cache successful responses
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => {
        // Network failed - try cache
        return caches.match(event.request).then(cached => {
          if (cached) return cached;
          
          // Return offline page for navigation
          if (event.request.mode === 'navigate') {
            return caches.match('/ops/backoffice/crm-dashboard.html');
          }
        });
      })
  );
});
