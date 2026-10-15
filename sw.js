// Darul Uloom Library: keeps the catalogue, the shelf map and the 3D library on the device
// so they open with no signal. Fonts and the 3D engine are part of the app, so nothing comes
// from outside. build.py stamps VERSION on every update, so phones fetch the new pages on
// their next visit online; fonts and the 3D engine never change and are carried over.
const VERSION = '202610151727';
const CACHE = 'du-library-' + VERSION;
const PAGES = ['./index.html', './shelves.html', './3d.html'];
const OTHER = ['./manifest.webmanifest', './icon-192.png', './icon-512.png', './icon-maskable-512.png', './apple-touch-icon.png',
  './lib/three.module.js', './lib/controls/OrbitControls.js',
  './fonts/amiri-400.woff', './fonts/amiri-700.woff', './fonts/plexarabic-400.woff', './fonts/plexarabic-500.woff',
  './fonts/plexarabic-600.woff', './fonts/plexsans-400.woff', './fonts/plexsans-500.woff', './fonts/plexsans-600.woff'];
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const c = await caches.open(CACHE);
    // the search page must be saved; the rest are saved if they can be and never block the app
    await c.add(new Request('./index.html', { cache: 'reload' }));
    await Promise.all([...PAGES.slice(1), ...OTHER].map(async u => {
      try {
        if (/^\.\/(lib|fonts)\//.test(u)) { const old = await caches.match(u); if (old) return c.put(u, old); }
        const r = await fetch(new Request(u, { cache: 'reload' })); if (r.ok) await c.put(u, r);
      } catch (e) {}
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

function pageKey(url) {
  const name = url.pathname.split('/').pop();
  return './' + (name && name.endsWith('.html') ? name : 'index.html');
}

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  if (url.origin !== self.location.origin) return;

  // a page: try the internet briefly for a newer version, otherwise open the saved copy at once
  if (req.mode === 'navigate') {
    const key = pageKey(url);
    event.respondWith((async () => {
      const c = await caches.open(CACHE);
      const saved = await c.match(key);
      try {
        const net = fetch(req, { cache: 'no-cache' }).then(async res => { if (res.ok) await c.put(key, res.clone()); return res; });
        event.waitUntil(net.catch(() => {}));
        if (!saved) return await net;
        const quick = await Promise.race([net, new Promise(r => setTimeout(() => r(null), 2500))]);
        return quick || saved;
      } catch (e) {
        return saved || (await c.match('./index.html')) ||
          new Response('Offline and not saved yet. Open the app once with signal.', { status: 503, headers: { 'Content-Type': 'text/plain' } });
      }
    })());
    return;
  }

  // icons, manifest and the rest: saved copy first
  event.respondWith((async () => {
    const hit = await caches.match(req, { ignoreSearch: true });
    if (hit) return hit;
    try { const res = await fetch(req); if (res.ok) (await caches.open(CACHE)).put(req, res.clone()); return res; }
    catch (e) { return new Response('', { status: 504 }); }
  })());
});
