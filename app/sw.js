// Service worker: app bisa dibuka offline, dan dokumen yang pernah dibuka tersimpan di HP.
const VERSI = "v2";
const CANGKANG = `daging-cangkang-${VERSI}`;
const DOKUMEN = "daging-dokumen";   // dipakai juga oleh app.js (tombol "simpan semua")

const FILE_CANGKANG = [
  "./", "index.html", "app.css", "app.js", "manifest.webmanifest",
  "ikon/ikon.svg", "ikon/ikon-192.png",
];
const FILE_PDFJS = ["vendor/pdf.min.mjs", "vendor/pdf.worker.min.mjs"];

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CANGKANG);
    await c.addAll(FILE_CANGKANG);
    await c.addAll(FILE_PDFJS).catch(() => {});
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) {
      if (k.startsWith("daging-cangkang-") && k !== CANGKANG) await caches.delete(k);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;

  if (url.pathname.endsWith("/output/index.json") || url.pathname.endsWith("/output/rahasia/brankas.json")) {
    e.respondWith(jaringanDulu(e.request));
  } else if (url.pathname.includes("/output/")) {
    // URL dokumen memuat ?v=<ukuran>, jadi dokumen yang dirender ulang dapat URL baru.
    e.respondWith(simpananDulu(e.request, DOKUMEN));
  } else if (url.pathname.includes("/vendor/")) {
    e.respondWith(simpananDulu(e.request, CANGKANG));
  } else {
    e.respondWith(simpananSambilPerbarui(e, CANGKANG));
  }
});

async function jaringanDulu(req) {
  const c = await caches.open(CANGKANG);
  try {
    const res = await fetch(req, { cache: "no-store" });
    if (res.ok) c.put(req, res.clone());
    return res;
  } catch (err) {
    return (await c.match(req)) || Response.error();
  }
}

async function simpananDulu(req, nama) {
  const c = await caches.open(nama);
  const ada = await c.match(req);
  if (ada) return ada;
  const res = await fetch(req);
  if (res.ok) c.put(req, res.clone());
  return res;
}

async function simpananSambilPerbarui(e, nama) {
  const c = await caches.open(nama);
  const ada = await c.match(e.request, { ignoreSearch: true });
  const segar = fetch(e.request).then((res) => {
    if (res.ok) c.put(e.request, res.clone());
    return res;
  });
  if (ada) {
    e.waitUntil(segar.catch(() => {}));
    return ada;
  }
  return segar;
}
