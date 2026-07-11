/* JLC offline service worker.
   Network-first for everything: online behaviour is unchanged, but every
   successful GET is cached so the app shell, finished-goods stock, customers
   and order forms can still be viewed with no internet. Writes are queued
   separately in the app (localStorage) and synced when back online. */

const CACHE = "jlc-offline-v2";

// Card-scanner OCR engine + English language data (fixed names, served from
// our own /ocr folder) — cached up front so scanning works with no internet.
const OCR_ASSETS = [
  "/ocr/worker.min.js",
  "/ocr/tesseract-core-relaxedsimd-lstm.wasm.js",
  "/ocr/tesseract-core-simd-lstm.wasm.js",
  "/ocr/tesseract-core-lstm.wasm.js",
  "/ocr/eng.traineddata.gz",
];

// Pre-cache the app shell (index.html + its JS/CSS) at install time so the
// app opens offline even if the user never reloaded while online.
self.addEventListener("install", (e) => {
  self.skipWaiting();
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    const res = await fetch("/", { cache: "no-cache" });
    if (!res.ok) return;
    await c.put("/", res.clone());
    const html = await res.text();
    const assets = [...html.matchAll(/(?:src|href)="(\/[^"]+\.(?:js|css|png|svg|ico|woff2?))"/g)]
      .map((m) => m[1]);
    await Promise.all([...assets, ...OCR_ASSETS].map(async (u) => {
      try {
        const r = await fetch(u, { cache: "no-cache" });
        if (r.ok) await c.put(u, r);
      } catch { /* skip */ }
    }));
  })().catch(() => {}));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;               // writes queue in the app
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // same-origin only

  e.respondWith(
    fetch(req)
      .then((res) => {
        // Cache good responses (the auth header travels on the request, so
        // cached API data is only ever served back into the logged-in app).
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(async () => {
        const hit = await caches.match(req);
        if (hit) return hit;
        // Offline navigation (reload / direct URL) → serve the app shell;
        // the React router then shows the right page from cached data.
        if (req.mode === "navigate") {
          const shell = await caches.match("/");
          if (shell) return shell;
        }
        return new Response(JSON.stringify({ detail: "offline" }), {
          status: 503, headers: { "Content-Type": "application/json" },
        });
      })
  );
});
