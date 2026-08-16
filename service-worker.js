var CACHE_NAME = 'ptg-cache-v1';
var CORE_ASSETS = ['./', './index.html', './manual.html'];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(CORE_ASSETS.map(function (url) { return new Request(url, { cache: 'reload' }); }));
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE_NAME; }).map(function (k) { return caches.delete(k); }));
    })
  );
  self.clients.claim();
});

// network-first：優先拿最新內容，離線或連線失敗時才退回快取；GitHub Pages 對回應下
// Cache-Control 導致「network-first」名不符實的坑已知（見 ai-image-prompt-studio 的踩坑記錄），
// 這裡從一開始就用 {cache:'reload'} 強制略過瀏覽器 HTTP 快取，不要拿掉
self.addEventListener('fetch', function (event) {
  var req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  event.respondWith(
    fetch(req, { cache: 'reload' }).then(function (resp) {
      var copy = resp.clone();
      caches.open(CACHE_NAME).then(function (cache) { cache.put(req, copy); });
      return resp;
    }).catch(function () {
      return caches.match(req);
    })
  );
});
