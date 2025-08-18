// Service Worker for AMuS Dataset Explorer
const CACHE_NAME = 'amus-v3';
const urlsToCache = [
  '/',
  '/explorer.html',
  '/benchmarks.html',
  '/assets/js/explorer.js',
  'https://fonts.googleapis.com/icon?family=Material+Icons',
  'https://code.getmdl.io/1.3.0/material.indigo-purple.min.css',
  'https://code.getmdl.io/1.3.0/material.min.js',
  'https://unpkg.com/vue@3/dist/vue.global.prod.js',
  'https://unpkg.com/lunr/lunr.js'
];

// Install Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        // Try to cache each URL individually to handle failures gracefully
        const cachePromises = urlsToCache.map(url => {
          return cache.add(url).catch(err => {
            console.warn('Failed to cache:', url, err);
            // Continue even if individual URLs fail
          });
        });
        return Promise.all(cachePromises);
      })
  );
});

// Cache and return requests
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }

        // Clone the request
        const fetchRequest = event.request.clone();

        return fetch(fetchRequest).then(response => {
          // Check if valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response
          const responseToCache = response.clone();

          // Don't cache data files larger than 5MB
          const contentLength = response.headers.get('content-length');
          if (contentLength && parseInt(contentLength) > 5 * 1024 * 1024) {
            return response;
          }

          // Cache JSON data files from _data directory
          if (event.request.url.includes('/_data/') && event.request.url.endsWith('.json')) {
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
          }

          return response;
        });
      })
  );
});

// Update Service Worker
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];

  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});