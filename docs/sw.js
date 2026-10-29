// أبو عودة: تشغيل كتطبيق، ويضل يفتح حتى لو النت ضعيف
const VERSION = "abu-odeh-v1";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icons/icon.svg", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

async function networkFirst(req) {
  const cache = await caches.open(VERSION);
  try {
    const res = await fetch(req);
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch {
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;
    throw new Error("offline");
  }
}

async function cacheFirst(req) {
  const cache = await caches.open(VERSION);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok || res.type === "opaque") cache.put(req, res.clone());
  return res;
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    e.respondWith(networkFirst(req));  // الصفحة والبيانات: الأحدث أول، والمحفوظ إذا ما في نت
  } else if (url.hostname.endsWith("fonts.gstatic.com") || url.hostname.endsWith("fonts.googleapis.com") || url.hostname === "a.espncdn.com") {
    e.respondWith(cacheFirst(req));    // الخطوط والشعارات ما بتتغير
  }
  // النتائج المباشرة (ESPN) وغيرها: من النت مباشرة
});
