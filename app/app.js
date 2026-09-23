// Daging — rak baca. Data: output/index.json (dibuat scripts/buat_indeks.py).
const CACHE_DOKUMEN = "daging-dokumen";   // sama dengan sw.js
const $ = (s) => document.querySelector(s);

const el = {
  rak: $("#rak"), daftar: $("#daftar"), kosong: $("#kosong"), lanjut: $("#lanjut"), cari: $("#cari"), chips: $("#chips"),
  pembaca: $("#pembaca"), naskah: $("#naskah"), pdf: $("#halaman-pdf"), memuat: $("#memuat"),
  bacaJudul: $("#baca-judul"), kepala: $(".baca-kepala"), kemajuan: $("#kemajuan-isi"),
  latar: $("#latar"), lembar: $("#lembar"), lembarIsi: $("#lembar-isi"), toast: $("#toast"),
};

let dokumen = [];          // publik + pribadi (bila brankas terbuka)
let dokPublik = [];
let dokPribadi = [];
let brankas = null;        // output/rahasia/brankas.json (terenkripsi), null bila tidak ada
let kunciBrankas = null;   // CryptoKey AES-GCM, ada hanya saat brankas terbuka
let saringan = "semua";
let dokAktif = null;       // dokumen yang sedang dibaca
let tutupPembaca = null;   // fungsi bersih-bersih pembaca (PDF, observer)
let isiDokumen = [];       // [{judul, sub, lompat()}] untuk lembar daftar isi
let gulirRak = 0;
let dariRak = false;

/* ---------- penyimpanan lokal (aman bila diblokir) ---------- */
function baca(kunci, awal) {
  try { return JSON.parse(localStorage.getItem("daging:" + kunci)) ?? awal; } catch { return awal; }
}
function simpan(kunci, nilai) {
  try { localStorage.setItem("daging:" + kunci, JSON.stringify(nilai)); } catch {}
}
const kemajuan = baca("kemajuan", {});   // { id: { p: 0..1, t: waktu terakhir dibuka } }
const setelan = Object.assign({ tema: "auto", huruf: 18 }, baca("setelan", {}));

function terapkanSetelan() {
  const r = document.documentElement;
  if (setelan.tema === "auto") delete r.dataset.theme; else r.dataset.theme = setelan.tema;
  r.style.setProperty("--ukuran-baca", setelan.huruf + "px");
  const warna = getComputedStyle(r).getPropertyValue("--kertas").trim();
  document.querySelectorAll('meta[name="theme-color"]').forEach((m) => m.setAttribute("content", warna));
  simpan("setelan", setelan);
}

/* ---------- utilitas ---------- */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const urlDok = (path, d) => encodeURI(path) + "?v=" + (d.v || d.ukuran);
const urlBaca = (d) => d.baca ? urlDok(d.baca, d) : urlDok(d.pdf, d);
const fmtTanggal = (iso) => {
  if (!iso) return "";
  return new Date(iso + "T00:00:00").toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
};
const namaJenis = (d) => ({ video: "Video", topik: "Riset" }[d.jenis] || "Dokumen");
const hariSejak = (iso) => (Date.now() - new Date(iso + "T00:00:00")) / 864e5;

let timerToast;
function toast(teks, lama = 2600) {
  el.toast.textContent = teks;
  el.toast.hidden = false;
  clearTimeout(timerToast);
  timerToast = setTimeout(() => (el.toast.hidden = true), lama);
}

/* ---------- brankas (dokumen pribadi terenkripsi; pasangan scripts/brankas.py) ---------- */
const dariB64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
const keB64 = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf)));
const CEK_BRANKAS = "daging-brankas-v1";

async function dekripsi(kunci, data) {
  return new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: data.slice(0, 12) }, kunci, data.slice(12)));
}

async function pakaiKunci(mentah) {
  const kunci = await crypto.subtle.importKey("raw", mentah, "AES-GCM", false, ["decrypt"]);
  const cek = new TextDecoder().decode(await dekripsi(kunci, dariB64(brankas.cek)));
  if (cek !== CEK_BRANKAS) throw new Error("sandi salah");
  dokPribadi = JSON.parse(new TextDecoder().decode(await dekripsi(kunci, dariB64(brankas.entri))));
  kunciBrankas = kunci;
  gabungDokumen();
}

async function bukaBrankas(sandi) {
  const bahan = await crypto.subtle.importKey("raw", new TextEncoder().encode(sandi), "PBKDF2", false, ["deriveBits"]);
  const mentah = await crypto.subtle.deriveBits(
    { name: "PBKDF2", hash: "SHA-256", salt: dariB64(brankas.salt), iterations: brankas.iterasi }, bahan, 256);
  await pakaiKunci(mentah);   // melempar galat bila sandi salah
  simpan("kunci", { salt: brankas.salt, k: keB64(mentah) });
}

function kunciKembali() {
  kunciBrankas = null;
  dokPribadi = [];
  try { localStorage.removeItem("daging:kunci"); } catch {}
  gabungDokumen();
}

function gabungDokumen() {
  dokumen = [...dokPribadi, ...dokPublik].sort((a, b) => (b.tanggal || "").localeCompare(a.tanggal || ""));
}

// Ambil isi dokumen; dokumen pribadi didekripsi (HTML-nya juga di-gzip).
async function ambilIsi(d, path, sebagai) {
  const res = await fetch(urlDok(path, d));
  if (!res.ok) throw new Error(res.status);
  if (!d.pribadi) return sebagai === "teks" ? res.text() : new Uint8Array(await res.arrayBuffer());
  const data = await dekripsi(kunciBrankas, new Uint8Array(await res.arrayBuffer()));
  if (sebagai !== "teks") return data;
  return new Response(new Blob([data]).stream().pipeThrough(new DecompressionStream("gzip"))).text();
}

/* ---------- data ---------- */
async function muatIndeks() {
  try {
    const res = await fetch("output/index.json");
    if (!res.ok) throw new Error(res.status);
    dokPublik = await res.json();
  } catch {
    dokPublik = [];
    el.kosong.textContent = "Daftar dokumen belum bisa dimuat. Periksa koneksi, lalu buka ulang app.";
  }
  try {
    const res = await fetch("output/rahasia/brankas.json");
    brankas = res.ok ? await res.json() : null;
  } catch { brankas = null; }

  const tersimpanKunci = baca("kunci", null);
  if (brankas && tersimpanKunci?.salt === brankas.salt) {
    try { await pakaiKunci(dariB64(tersimpanKunci.k)); } catch { kunciKembali(); }
  } else if (tersimpanKunci) {
    kunciKembali();   // sandi brankas diganti di laptop: minta sandi baru
  }
  gabungDokumen();
  bersihkanSimpananLama();
}

async function bersihkanSimpananLama() {
  if (!("caches" in window) || !dokumen.length) return;
  const berlaku = new Set(dokumen.flatMap((d) => [d.pdf, d.baca].filter(Boolean).map((p) => new URL(urlDok(p, d), location.href).href)));
  const c = await caches.open(CACHE_DOKUMEN);
  for (const req of await c.keys()) {
    if (!kunciBrankas && req.url.includes("/output/rahasia/")) continue;   // saat terkunci, daftarnya tak diketahui
    if (!berlaku.has(req.url)) c.delete(req);
  }
}

async function unduhPdf(d) {
  if (!d.pribadi) return;
  const data = await ambilIsi(d, d.pdf, "biner");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([data], { type: "application/pdf" }));
  a.download = d.judul.replace(/[\\/:*?"<>|]+/g, " ").trim() + ".pdf";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 60000);
}
const tombolPdf = (d, kelas = "") => d.pribadi
  ? `<button class="${kelas}" data-unduh-pdf>Unduh PDF</button>`
  : `<a class="${kelas}" href="${urlDok(d.pdf, d)}" download>Unduh PDF</a>`;
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-unduh-pdf]") && dokAktif) unduhPdf(dokAktif).catch(() => toast("PDF gagal dibuka."));
});

async function tersimpan() {
  if (!("caches" in window)) return new Set();
  const c = await caches.open(CACHE_DOKUMEN);
  return new Set((await c.keys()).map((r) => r.url));
}

async function simpanSemua() {
  const c = await caches.open(CACHE_DOKUMEN);
  const ada = await tersimpan();
  const perlu = dokumen.map((d) => new URL(urlBaca(d), location.href).href).filter((u) => !ada.has(u));
  if (!perlu.length) return toast("Semua dokumen sudah tersimpan di perangkat.");
  let n = 0;
  for (const u of perlu) {
    toast(`Menyimpan ${++n} dari ${perlu.length}…`, 60000);
    try { await c.add(u); } catch { toast("Gagal menyimpan sebagian dokumen. Coba lagi saat online."); return; }
  }
  toast("Selesai. Semua dokumen bisa dibaca offline.");
  renderRak();
}

/* ---------- rak ---------- */
async function renderRak() {
  const q = el.cari.value.trim().toLowerCase();
  const cocok = dokumen.filter((d) => {
    if (saringan === "video" && d.jenis !== "video") return false;
    if (saringan === "topik" && d.jenis === "video") return false;
    if (saringan === "belum" && (kemajuan[d.id]?.p ?? 0) >= 0.97) return false;
    if (!q) return true;
    return [d.judul, d.subjudul, d.channel].some((t) => t && t.toLowerCase().includes(q));
  });

  const offline = await tersimpan();
  el.daftar.innerHTML = cocok.map((d) => {
    const k = kemajuan[d.id];
    const p = k?.p ?? 0;
    const baru = !k && hariSejak(d.tanggal) < 4;
    const disimpan = offline.has(new URL(urlBaca(d), location.href).href);
    const ket = d.jenis === "video" ? [d.channel, d.durasi].filter(Boolean).join(" · ") : d.subjudul;
    const status = p >= 0.97 ? `<span class="selesai">Selesai</span>`
      : k ? `<div class="bar"><div style="width:${Math.max(3, p * 100).toFixed(0)}%"></div></div><span>${Math.round(p * 100)}%</span>`
      : `<span style="flex:1"></span>`;
    return `<li><a class="kartu" href="#/d/${encodeURIComponent(d.id)}">
      <div class="kartu-meta"><span class="label-jenis ${d.jenis ? "" : "dokumen"}">${namaJenis(d)}</span><span class="titik"></span><span>${fmtTanggal(d.tanggal)}</span></div>
      <h2>${esc(d.judul)}</h2>
      ${ket ? `<p>${esc(ket)}</p>` : ""}
      <div class="kartu-kaki">${status}
        ${baru ? `<span class="lencana baru">Baru</span>` : ""}
        ${d.pribadi ? `<span class="lencana pribadi"><svg viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>Pribadi</span>` : ""}
        ${d.baca ? "" : `<span class="lencana">PDF</span>`}
        ${disimpan ? `<svg class="offline-ikon" viewBox="0 0 24 24" aria-label="Tersimpan offline"><path d="M12 3v12m0 0-4-4m4 4 4-4M5 21h14"/></svg>` : ""}
      </div></a></li>`;
  }).join("");

  el.kosong.hidden = cocok.length > 0;
  if (!cocok.length && dokumen.length) el.kosong.textContent = q ? `Tidak ada judul yang cocok dengan “${el.cari.value}”.` : "Tidak ada dokumen di kategori ini.";

  const terakhir = dokumen
    .filter((d) => kemajuan[d.id] && kemajuan[d.id].p < 0.97)
    .sort((a, b) => kemajuan[b.id].t - kemajuan[a.id].t)[0];
  el.lanjut.hidden = !terakhir || !!q;
  if (terakhir) {
    const p = kemajuan[terakhir.id].p;
    el.lanjut.innerHTML = `<a class="lanjut-kartu" href="#/d/${encodeURIComponent(terakhir.id)}">
      <div class="lbl">Lanjutkan membaca</div>
      <div class="jdl">${esc(terakhir.judul)}</div>
      <div class="bar"><div style="width:${Math.max(3, p * 100).toFixed(0)}%"></div></div>
      <div class="ket">${Math.round(p * 100)}% dibaca</div></a>`;
  }
}

el.cari.addEventListener("input", renderRak);
el.chips.addEventListener("click", (e) => {
  const b = e.target.closest(".chip");
  if (!b) return;
  saringan = b.dataset.f;
  el.chips.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", c === b));
  renderRak();
});
el.daftar.addEventListener("click", () => { dariRak = true; gulirRak = scrollY; });
el.lanjut.addEventListener("click", () => { dariRak = true; gulirRak = scrollY; });

/* ---------- pembaca ---------- */
function catatKemajuan() {
  if (!dokAktif) return;
  const h = document.documentElement.scrollHeight - innerHeight;
  const p = h > 0 ? Math.min(1, Math.max(0, scrollY / h)) : 1;
  el.kemajuan.style.width = (p * 100).toFixed(1) + "%";
  kemajuan[dokAktif.id] = { p, t: Date.now() };
  simpan("kemajuan", kemajuan);
}

let yTerakhir = 0, rafGulir = 0;
addEventListener("scroll", () => {
  if (el.pembaca.hidden || rafGulir) return;
  rafGulir = requestAnimationFrame(() => {
    rafGulir = 0;
    const y = scrollY;
    el.kepala.classList.toggle("sembunyi", y > yTerakhir && y > 120);
    yTerakhir = y;
    catatKemajuan();
  });
}, { passive: true });

function pulihkanPosisi(d) {
  const p = kemajuan[d.id]?.p ?? 0;
  const h = document.documentElement.scrollHeight - innerHeight;
  scrollTo(0, p < 0.97 ? p * h : 0);
}

async function bukaDokumen(d) {
  dokAktif = null;
  el.rak.hidden = true;
  el.pembaca.hidden = false;
  el.naskah.innerHTML = "";
  el.naskah.hidden = false;
  el.pdf.hidden = true;
  el.pdf.innerHTML = "";
  el.memuat.hidden = false;
  el.memuat.textContent = "Memuat…";
  el.kepala.classList.remove("sembunyi");
  el.bacaJudul.textContent = d.judul;
  document.title = d.judul;
  isiDokumen = [];
  scrollTo(0, 0);

  try {
    if (d.baca) await tampilkanHtml(d); else await tampilkanPdf(d);
  } catch (err) {
    console.error(err);
    el.memuat.textContent = navigator.onLine
      ? "Dokumen gagal dimuat."
      : "Dokumen ini belum tersimpan di perangkat. Sambungkan internet sekali untuk membukanya.";
    return;
  }
  el.memuat.hidden = true;
  requestAnimationFrame(() => {
    pulihkanPosisi(d);
    dokAktif = d;
    catatKemajuan();
  });
}

async function tampilkanHtml(d) {
  el.naskah.innerHTML = await ambilIsi(d, d.baca, "teks");

  for (const t of el.naskah.querySelectorAll("table")) {
    if (t.closest(".cover")) continue;
    const w = document.createElement("div");
    w.className = "tabel-gulir";
    t.replaceWith(w);
    w.append(t);
  }
  for (const a of el.naskah.querySelectorAll('a[href^="http"]')) { a.target = "_blank"; a.rel = "noopener"; }

  const akhir = document.createElement("div");
  akhir.className = "akhir";
  akhir.innerHTML = `— Selesai —<br>${tombolPdf(d)}`;
  el.naskah.append(akhir);

  const judulIsi = [...el.naskah.querySelectorAll("h1[id], h2[id]")].filter((h) => !h.closest(".cover"));
  isiDokumen = judulIsi.map((h) => ({
    judul: h.textContent, sub: h.tagName === "H2", el: h,
    lompat: () => h.scrollIntoView({ block: "start" }),
  }));

  // Tautan internal (daftar isi, catatan kaki) jangan diperlakukan sebagai rute.
  el.naskah.onclick = (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;
    e.preventDefault();
    const t = document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)));
    if (t) t.scrollIntoView({ block: /^H\d$/.test(t.tagName) ? "start" : "center", behavior: "smooth" });
  };
}

let pdfjs;
async function tampilkanPdf(d) {
  if (!pdfjs) {
    pdfjs = await import("./vendor/pdf.min.mjs");
    pdfjs.GlobalWorkerOptions.workerSrc = new URL("vendor/pdf.worker.min.mjs", location.href).href;
  }
  el.memuat.textContent = "Membuka PDF…";
  const pdf = await pdfjs.getDocument({ data: await ambilIsi(d, d.pdf, "biner") }).promise;
  const hal1 = (await pdf.getPage(1)).getViewport({ scale: 1 });

  el.naskah.hidden = true;
  el.pdf.hidden = false;
  el.pdf.innerHTML = `<p class="pdf-info">Dokumen ini hanya tersedia sebagai PDF. Cubit layar untuk memperbesar.</p>`;
  const kotak = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const div = document.createElement("div");
    div.className = "hal";
    div.dataset.n = i;
    div.style.aspectRatio = `${hal1.width} / ${hal1.height}`;
    el.pdf.append(div);
    kotak.push(div);
  }

  const tugas = new Map();
  const obs = new IntersectionObserver((entri) => {
    for (const en of entri) {
      const div = en.target;
      if (en.isIntersecting && !div.firstChild) gambarHalaman(div);
      else if (!en.isIntersecting && div.firstChild) {
        tugas.get(div)?.cancel();
        tugas.delete(div);
        div.replaceChildren();
      }
    }
  }, { rootMargin: "150% 0px" });
  kotak.forEach((k) => obs.observe(k));

  async function gambarHalaman(div) {
    const canvas = document.createElement("canvas");
    div.append(canvas);
    const page = await pdf.getPage(+div.dataset.n);
    const skala = (div.clientWidth * Math.min(devicePixelRatio || 1, 2.5)) / page.getViewport({ scale: 1 }).width;
    const vp = page.getViewport({ scale: skala });
    canvas.width = Math.floor(vp.width);
    canvas.height = Math.floor(vp.height);
    const t = page.render({ canvas, viewport: vp });
    tugas.set(div, t);
    try { await t.promise; } catch {} finally { tugas.delete(div); }
  }

  const lompatKe = async (dest) => {
    if (typeof dest === "string") dest = await pdf.getDestination(dest);
    if (!Array.isArray(dest)) return;
    const idx = typeof dest[0] === "number" ? dest[0] : await pdf.getPageIndex(dest[0]);
    const div = kotak[idx];
    if (!div) return;
    let y = div.getBoundingClientRect().top + scrollY - 60;
    if (dest[1]?.name === "XYZ" && typeof dest[3] === "number") y += (1 - dest[3] / hal1.height) * div.clientHeight;
    scrollTo(0, y);
  };
  const outline = (await pdf.getOutline()) || [];
  const ratakan = (items, sub) => items.flatMap((o) => [
    { judul: o.title, sub, lompat: () => lompatKe(o.dest) },
    ...(sub ? [] : ratakan(o.items || [], true)),
  ]);
  isiDokumen = ratakan(outline, false);

  tutupPembaca = () => { obs.disconnect(); pdf.destroy(); };
}

/* ---------- lembar bawah ---------- */
function bukaLembar(html) {
  el.lembarIsi.innerHTML = html;
  el.latar.hidden = false;
  el.lembar.hidden = false;
  el.lembar.scrollTop = 0;
}
function tutupLembar() {
  el.latar.hidden = true;
  el.lembar.hidden = true;
}
el.latar.addEventListener("click", tutupLembar);

function lembarDaftarIsi() {
  if (!isiDokumen.length) return toast("Dokumen ini tidak punya daftar isi.");
  // judul aktif = judul terakhir yang sudah terlewati
  let aktif = -1;
  isiDokumen.forEach((x, i) => { if (x.el && x.el.getBoundingClientRect().top < 90) aktif = i; });
  bukaLembar(`<h3>Daftar isi</h3><ul class="isi-daftar">${isiDokumen.map((x, i) =>
    `<li><a href="#" data-i="${i}" class="${x.sub ? "sub" : ""} ${i === aktif ? "aktif" : ""}">${esc(x.judul)}</a></li>`).join("")}</ul>`);
  el.lembarIsi.querySelector(".aktif")?.scrollIntoView({ block: "center" });
  el.lembarIsi.onclick = (e) => {
    const a = e.target.closest("a[data-i]");
    if (!a) return;
    e.preventDefault();
    tutupLembar();
    isiDokumen[+a.dataset.i].lompat();
  };
}

function lembarSetelan(diRak) {
  const seg = (nama, pilihan, nilai) => `<div class="segmen" data-seg="${nama}">${pilihan.map(([v, l]) =>
    `<button data-v="${v}" aria-pressed="${String(v) === String(nilai)}">${l}</button>`).join("")}</div>`;
  bukaLembar(`
    <h3>Tema</h3>${seg("tema", [["auto", "Otomatis"], ["light", "Terang"], ["sepia", "Sepia"], ["dark", "Gelap"]], setelan.tema)}
    <h3>Ukuran huruf</h3>${seg("huruf", [[16, "Kecil"], [18, "Sedang"], [20, "Besar"], [23, "Jumbo"]], setelan.huruf)}
    ${diRak ? `
      <h3>Offline</h3>
      <button class="tombol-lebar" id="simpan-semua">Simpan semua dokumen ke perangkat</button>
      <p class="catatan-kecil" id="info-ruang">Dokumen yang pernah dibuka otomatis tersimpan dan bisa dibaca tanpa internet.</p>
      ${!brankas ? `
        <h3>Brankas</h3>
        <p class="catatan-kecil">Brankas masih kosong. Dokumen yang dijadikan pribadi dari laptop akan muncul di sini
        setelah dibuka dengan sandi.</p>` : kunciBrankas ? `
        <h3>Brankas</h3>
        <p class="catatan-kecil">Terbuka · ${dokPribadi.length} dokumen pribadi tampil di rak.</p>
        <button class="tombol-lebar" id="kunci-brankas">Kunci brankas</button>` : `
        <h3>Brankas</h3>
        <form id="form-brankas" class="form-brankas">
          <input type="password" name="sandi" placeholder="Sandi brankas" autocomplete="current-password" required>
          <button type="submit">Buka</button>
        </form>
        <p class="catatan-kecil" id="info-brankas">Dokumen pribadi hanya muncul setelah brankas dibuka. Sandi diingat di perangkat ini sampai dikunci lagi.</p>`}`
    : dokAktif ? `${tombolPdf(dokAktif, "tombol-lebar")}
      ${dokAktif.url ? `<a class="tombol-lebar" href="${esc(dokAktif.url)}" target="_blank" rel="noopener">Buka video di YouTube</a>` : ""}` : ""}
  `);
  el.lembarIsi.onclick = (e) => {
    const b = e.target.closest(".segmen button");
    if (b) {
      const nama = b.parentElement.dataset.seg;
      setelan[nama] = nama === "huruf" ? +b.dataset.v : b.dataset.v;
      b.parentElement.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      // pertahankan posisi baca saat ukuran huruf berubah
      const p = dokAktif ? kemajuan[dokAktif.id]?.p : null;
      terapkanSetelan();
      if (p != null && nama === "huruf") scrollTo(0, p * (document.documentElement.scrollHeight - innerHeight));
    }
    if (e.target.closest("#simpan-semua")) { tutupLembar(); simpanSemua(); }
    if (e.target.closest("#kunci-brankas")) {
      kunciKembali();
      tutupLembar();
      renderRak();
      toast("Brankas dikunci.");
    }
  };
  const form = $("#form-brankas");
  if (form) form.onsubmit = async (e) => {
    e.preventDefault();
    const info = $("#info-brankas");
    const tombol = form.querySelector("button");
    tombol.disabled = true;
    info.textContent = "Membuka…";
    try {
      await bukaBrankas(form.sandi.value);
      tutupLembar();
      renderRak();
      toast(`Brankas terbuka: ${dokPribadi.length} dokumen pribadi.`);
    } catch {
      info.textContent = "Sandi salah.";
      form.sandi.select();
    } finally {
      tombol.disabled = false;
    }
  };
  if (diRak && navigator.storage?.estimate) {
    navigator.storage.estimate().then(({ usage }) => {
      const i = $("#info-ruang");
      if (i && usage) i.textContent += ` Terpakai sekitar ${(usage / 1048576).toFixed(1)} MB.`;
    });
  }
}

$("#tombol-setelan").addEventListener("click", () => lembarSetelan(true));
$("#tombol-aa").addEventListener("click", () => lembarSetelan(false));
$("#tombol-isi").addEventListener("click", lembarDaftarIsi);
$("#tombol-kembali").addEventListener("click", () => {
  if (dariRak) history.back(); else location.hash = "";
});

/* ---------- rute ---------- */
async function rute() {
  tutupLembar();
  tutupPembaca?.();
  tutupPembaca = null;
  const m = location.hash.match(/^#\/d\/(.+)$/);
  const d = m && dokumen.find((x) => x.id === decodeURIComponent(m[1]));
  if (d) return bukaDokumen(d);

  dokAktif = null;
  document.title = "Daging";
  el.pembaca.hidden = true;
  el.rak.hidden = false;
  await renderRak();
  scrollTo(0, gulirRak);
  dariRak = false;
}
addEventListener("hashchange", rute);

terapkanSetelan();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", terapkanSetelan);
await muatIndeks();
rute();

if ("serviceWorker" in navigator && location.protocol !== "file:") {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
