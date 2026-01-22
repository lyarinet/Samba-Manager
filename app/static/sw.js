// Service Worker for Samba Manager PWA
const CACHE_NAME = 'samba-manager-v1.0.0';

// Only cache local resources that we know will work
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/icon-192.svg',
  '/static/icon-512.svg'
];

// Install Service Worker
self.addEventListener('install', event => {
  console.log('Service Worker installing.');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Service Worker caching app shell');
        // Cache each resource individually to handle failures gracefully
        return Promise.allSettled(
          urlsToCache.map(url => {
            return fetch(url, { cache: 'no-cache' })
              .then(response => {
                if (response.ok) {
                  return cache.put(url, response);
                } else {
                  console.warn(`Failed to cache ${url}: ${response.status}`);
                }
              })
              .catch(error => {
                console.warn(`Failed to fetch ${url}:`, error);
              });
          })
        );
      })
      .then(() => {
        console.log('Service Worker installation completed');
        return self.skipWaiting();
      })
  );
});

// Fetch Event - Network first, then cache
self.addEventListener('fetch', event => {
  // Only handle GET requests
  if (event.request.method !== 'GET') return;

  // Handle different types of requests
  const url = new URL(event.request.url);

  // For API calls, try network first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Cache successful API responses for a short time
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // If network fails, try cache
          return caches.match(event.request);
        })
    );
    return;
  }

  // For static assets, try cache first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request)
        .then(response => {
          if (response) {
            return response;
          }
          // If not in cache, fetch from network
          return fetch(event.request).then(networkResponse => {
            // Cache the response for future use
            if (networkResponse.ok) {
              const responseClone = networkResponse.clone();
              caches.open(CACHE_NAME).then(cache => {
                cache.put(event.request, responseClone);
              });
            }
            return networkResponse;
          });
        })
    );
    return;
  }

  // For all other requests, try network first, then cache
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Don't cache error responses
        if (response.ok) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // If network fails, try cache
        return caches.match(event.request);
      })
  );
});

// Activate Event
self.addEventListener('activate', event => {
  console.log('Service Worker activating.');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('Service Worker activated');
      return self.clients.claim();
    })
  );
});

// Handle messages from the main thread
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});