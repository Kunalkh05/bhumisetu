const CACHE_NAME = "bhumisetu-citizen-v1";
const OFFLINE_URL = "/c/offline";
const RETRY_DELAYS_MS = [1000, 2000, 4000];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.add(OFFLINE_URL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithRetry(request) {
  try {
    return await fetch(request);
  } catch (error) {
    for (const ms of RETRY_DELAYS_MS) {
      await delay(ms);
      try {
        return await fetch(request);
      } catch (nextError) {
        error = nextError;
      }
    }
    throw error;
  }
}

async function staleResponse(response) {
  const html = await response.text();
  const staleAt = new Date().toISOString();
  return new Response(
    html.replace("<!--STALE-->", `<div class="panel" data-stale-at="${staleAt}"></div>`),
    {
      headers: {
        "content-type": "text/html; charset=utf-8",
        "x-bhumisetu-cache": "stale",
      },
    },
  );
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || !request.headers.get("accept")?.includes("text/html")) {
    return;
  }

  event.respondWith(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      try {
        const response = await fetchWithRetry(request);
        if (response.ok) {
          await cache.put(request, response.clone());
        }
        return response;
      } catch {
        const cached = await cache.match(request);
        if (cached) {
          return staleResponse(cached);
        }
        return cache.match(OFFLINE_URL);
      }
    })(),
  );
});
