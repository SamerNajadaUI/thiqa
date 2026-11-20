// تعليلة: تشغيل كتطبيق، وسريع حتى لو النت ضعيف.
// - الصفحات والكود (html/js/css): من النت أول، وإذا النت بطيء (أكثر من ثانية ونص) أو مقطوع بنفتح المحفوظ.
// - البيانات (json): المحفوظ فوراً، وبنحدّثه بالخلفية للمرة الجاية.
// - الصور والخطوط: المحفوظ دايماً (بتنمسح لما يتغير VERSION).
const VERSION = "abu-odeh-v32";
const DATA = "abu-odeh-data-v1";   // البيانات ما بتنمسح مع كل نشر، بتتحدّث لحالها
const SHELL = ["./", "index.html", "home.html", "login.html", "rewards.html", "settings.html", "theme.js", "shell.css", "shell.js", "ds/ds.css", "app/core.js", "app/ui.js", "app/firebase-config.js", "manifest.webmanifest", "icons/icon.svg", "icons/wordmark-dark.svg", "ds/ui.css", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png", "games/index.html"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION && k !== DATA).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

async function networkFirst(req) {
  const cache = await caches.open(VERSION);
  const net = fetch(req, { cache: "no-cache" }).then((res) => { if (res.ok) cache.put(req, res.clone()); return res; });
  const hit = await cache.match(req, { ignoreSearch: true });
  if (!hit) return net;
  // إذا النت بطيء، المحفوظ بيفتح والجديد بيتخزّن للمرة الجاية
  return Promise.race([net.catch(() => hit), new Promise((r) => setTimeout(() => r(hit), 1500))]);
}

// البيانات: المفتاح بدون ?t= عشان نلاقيها، وبنرجّع المحفوظ فوراً ونحدّث بالخلفية
async function staleWhileRevalidate(req, e) {
  const cache = await caches.open(DATA);
  const url = new URL(req.url); url.search = "";
  const key = url.href;
  const hit = await cache.match(key);
  const net = fetch(req, { cache: "no-cache" }).then((res) => { if (res.ok) cache.put(key, res.clone()); return res; });
  if (hit) { e.waitUntil(net.catch(() => {})); return hit; }
  return net;
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
  // الأصوات والفيديو: من النت مباشرة (Safari بيطلبها على قطع Range والكاش بيخربها)
  if (req.destination === "audio" || req.destination === "video" || req.headers.has("range") || /\/transcoded\/|\.(mp3|ogg|oga|wav|webm|m4a|mp4)(\?|$)/i.test(url.pathname)) return;
  if (url.origin === location.origin) {
    // data/ (القسائم والنتائج) لازم تكون طازة: من النت أول
    if (/\.json$/i.test(url.pathname) && !url.pathname.includes("/data/")) e.respondWith(staleWhileRevalidate(req, e));
    else if (/\.(webp|png|jpg|jpeg|svg|gif)$/i.test(url.pathname)) e.respondWith(cacheFirst(req));
    else e.respondWith(networkFirst(req));
  } else if (url.hostname.endsWith("fonts.gstatic.com") || url.hostname.endsWith("fonts.googleapis.com") || url.hostname === "a.espncdn.com" || url.hostname.endsWith("wikimedia.org") || url.hostname === "flagcdn.com" || url.hostname === "cdn.jsdelivr.net") {
    e.respondWith(cacheFirst(req));    // الخطوط والشعارات والمكتبات ما بتتغير
  }
  // النتائج المباشرة (ESPN) وغيرها: من النت مباشرة
});
