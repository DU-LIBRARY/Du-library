// Darul Uloom Library: keeps the catalogue on the device so it opens and searches with no signal.
// When a new catalogue is uploaded, bump VERSION so phones fetch it on their next visit online.
const VERSION = '2026-10-12a';
const CACHE = 'du-library-' + VERSION;
const FONT_CACHE = 'du-library-fonts';
const CORE = ['./', './index.html', './manifest.webmanifest',
  './icons/icon-192.png', './icons/icon-512.png', './icons/icon-maskable-512.png', './icons/apple-touch-icon.png'];
const FONT_CSS = 'https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=IBM+Plex+Sans+Arabic:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap';

async function cacheFonts() {
  // Fonts are a nicety: if they can't be fetched, the app still works with the phone's own fonts.
  try {
    const fc = await caches.open(FONT_CACHE);
    if (await fc.match(FONT_CSS)) return;
    const res = await fetch(FONT_CSS, { mode: 'cors' });
    if (!res.ok) return;
    const css = await res.clone().text();
    await fc.put(FONT_CSS, res);
    const urls = [...css.matchAll(/url\((https:\/\/fonts\.gstatic\.com\/[^)]+)\)/g)].map(m => m[1]);
    await Promise.all(urls.map(u => fetch(u, { mode: 'cors' }).then(r => r.ok && fc.put(u, r)).catch(() => {})));
  } catch (e) {}
}

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const c = await caches.open(CACHE);
    await c.addAll(CORE.map(u => new Request(u, { cache: 'reload' })));
    await cacheFonts();
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE && k !== FONT_CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Google Fonts: from the device first, the internet only if missing.
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    event.respondWith((async () => {
      const fc = await caches.open(FONT_CACHE);
      const hit = await fc.match(req, { ignoreVary: true }) || await fc.match(req.url);
      if (hit) return hit;
      try { const res = await fetch(req); if (res.ok || res.type === 'opaque') fc.put(req, res.clone()); return res; }
      catch (e) { return new Response('', { status: 504 }); }
    })());
    return;
  }
  if (url.origin !== self.location.origin) return;

  // The page itself: try the internet briefly for a newer catalogue, otherwise open the saved copy at once.
  if (req.mode === 'navigate') {
    event.respondWith((async () => {
      const c = await caches.open(CACHE);
      const saved = await c.match('./index.html');
      try {
        const net = fetch(req, { cache: 'no-cache' }).then(async res => { if (res.ok) await c.put('./index.html', res.clone()); return res; });
        event.waitUntil(net.catch(() => {}));
        if (!saved) return await net;
        const quick = await Promise.race([net, new Promise(r => setTimeout(() => r(null), 2500))]);
        return quick || saved;
      } catch (e) { return saved || new Response('Offline and not saved yet. Open the app once with signal.', { status: 503, headers: { 'Content-Type': 'text/plain' } }); }
    })());
    return;
  }

  // Icons, manifest and the rest: saved copy first.
  event.respondWith((async () => {
    const hit = await caches.match(req, { ignoreSearch: true });
    if (hit) return hit;
    try { const res = await fetch(req); if (res.ok) (await caches.open(CACHE)).put(req, res.clone()); return res; }
    catch (e) { return new Response('', { status: 504 }); }
  })());
});
