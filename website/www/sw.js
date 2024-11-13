/*
 Copyright 2014 Google Inc. All Rights Reserved.
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
 http://www.apache.org/licenses/LICENSE-2.0
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 */

// While overkill for this specific sample in which there is only one cache,
// this is one best practice that can be followed in general to keep track of
// multiple caches used by a given service worker, and keep them all versioned.
// It maps a shorthand identifier for a cache to a specific, versioned cache name.

// Note that since global state is discarded in between service worker restarts, these
// variables will be reinitialized each time the service worker handles an event, and you
// should not attempt to change their values inside an event handler. (Treat them as constants.)

// If at any point you want to force pages that use this service worker to start using a fresh
// cache, then increment the CACHE_VERSION value. It will kick off the service worker update
// flow and the old cache(s) will be purged as part of the activate event handler when the
// updated service worker is activated.
let CACHE_VERSION = 2;
let CURRENT_CACHES = {
  prefetch: 'prefetch-cache-v' + CACHE_VERSION
};

let DOMAIN = "https://watch-together-emw4.5276.online";

const putInCache = async (request, response) => {
  const cache = await caches.open(CURRENT_CACHES["prefetch"]);
  await cache.put(request, response);
  console.log(`Cached "${request.url}"`);
};

self.addEventListener('install', function(event) {
  let urlsToPrefetch = [
    '/'
  ];

  // All of these logging statements should be visible via the "Inspect" interface
  // for the relevant SW accessed via chrome://serviceworker-internals
  console.log('Handling install event. Resources to prefetch:', urlsToPrefetch);

  self.skipWaiting();

  event.waitUntil(
    caches.open(CURRENT_CACHES.prefetch).then(function(cache) {
      return cache.addAll(urlsToPrefetch);
    })
  );
});

self.addEventListener('activate', function(event) {
  let expectedCacheNames = Object.keys(CURRENT_CACHES).map(function(key) {
    return CURRENT_CACHES[key];
  });

  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (expectedCacheNames.indexOf(cacheName) === -1) {
            console.log('Deleting out of date cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
        );
    })
    );
});

/*async function getCacheStoragesAssetTotalSize() {
    // Note: opaque (i.e. cross-domain, without CORS) responses in the cache will return a size of 0.
    const cacheNames = await caches.keys();

    let total = 0;

    const sizePromises = cacheNames.map(async cacheName => {
      const cache = await caches.open(cacheName);
      const keys = await cache.keys();
      let cacheSize = 0;

      await Promise.all(keys.map(async key => {
        const response = await cache.match(key);
        const blob = await response.blob();
        total += blob.size;
        cacheSize += blob.size;
      }));

      console.log(`Cache ${cacheName}: ${cacheSize} bytes`);
    });

    await Promise.all(sizePromises);

    return `Total Cache Storage: ${total} bytes`;
}*/

async function fetch_from_network(event) {
    return fetch(event.request).then((response) => {
        // console.log('Response from network is:', response);
        return response;
    }).catch(function(error) {
        console.error('Fetching failed:', error);
        throw error;
    });
}

async function fetch_url(event) {
    let requestURL = event.request.url;

    if (requestURL.startsWith(DOMAIN)) {
        const urlObject = new URL(requestURL);
        requestURL = urlObject.pathname;
    }

    if (event.request.url.startsWith(`${DOMAIN}/videos`) &&
        event.request.url.endsWith(".m4s")
    ) {
        console.log(`Requested cacheable url "${requestURL}"`);
        return caches.match(event.request).then(async (response) => {
            if (response) {
                console.log('Found response in cache:', response);
                return response;
            }

            console.log('No response found in cache. About to fetch from network...');

            let network_response = await fetch_from_network(event);

            const new_headers = new Headers(network_response.headers);
            new_headers.append('Cached-By-Worker', '1');

            const new_response = new Response(network_response.body, {
                status: network_response.status,
                statusText: network_response.statusText,
                headers: new_headers
            });

            putInCache(event.request, new_response.clone());

            return new_response.clone();
        })
    } else {
        // console.log(`Requested non-cacheable url "${requestURL}"`);
        return fetch_from_network(event);
    }
}

self.addEventListener('fetch', function(event) {
    event.respondWith(fetch_url(event));
});
