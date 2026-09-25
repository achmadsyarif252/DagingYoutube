"""Buat versi audio (dibacakan) dari dokumen, untuk didengarkan di app baca.

Pemakaian:
    python scripts/buat_audio.py                 semua dokumen publik yang belum/berubah audionya
    python scripts/buat_audio.py <cari>          satu dokumen (sebagian judul / nama file / kode)
    python scripts/buat_audio.py --contoh <cari> contoh 30 detik → kerja/contoh_audio.mp3
    python scripts/buat_audio.py <cari> --matikan    dokumen ini tanpa audio (audionya dihapus)
    python scripts/buat_audio.py <cari> --nyalakan   buat audio lagi untuk dokumen itu
    Dokumen dengan "tanpa_audio": true (di kerja/<kode>/info.json, terbawa ke baca/<nama>.json) dilewati.
    Tambah --pribadi untuk ikut membuat audio dokumen pribadi. PERHATIAN: teksnya dikirim ke layanan
    suara Microsoft (edge-tts), jadi ini keputusan sadar, bukan default.

Menulis  output/audio/<nama>.opus + .json   (publik)
         pribadi/audio/<nama>.opus + .json  (pribadi; terbit terenkripsi lewat brankas.py)

Teks diambil dari versi baca HTML (output/baca/<nama>.html) atau, bila tidak ada, dari PDF.
Dibersihkan untuk didengar: nomor catatan kaki, timestamp, daftar isi, dan catatan kaki dilewati;
tabel diganti keterangan singkat. Satu file per dokumen, dengan penanda waktu per bab di .json.
"""

import asyncio
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

import edge_tts

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SUARA = "id-ID-ArdiNeural"
VERSI_TEKS = "1"   # naikkan bila aturan pembersihan teks berubah, supaya audio dibuat ulang
TEMPAT = {"publik": ROOT / "output", "pribadi": ROOT / "pribadi"}


# ---------------------------------------------------------------- teks dari HTML

class PengurasHtml(HTMLParser):
    """Ubah potongan HTML versi baca menjadi [{judul, paragraf[]}] per bab (h1)."""

    LEWATI_KELAS = {"toc", "footnote", "label", "dibuat"}
    BLOK = {"p", "li", "h2", "h3", "h4", "blockquote", "td", "th", "dt", "dd"}

    def __init__(self):
        super().__init__()
        self.bab = [{"judul": "Pembuka", "paragraf": []}]
        self.tumpukan = []      # (tag, dilewati?, kelas)
        self.buf = []
        self.di_h1 = False
        self.h1_buf = []
        self.judul_kotak = False

    def _dilewati(self):
        return any(l for _, l, _ in self.tumpukan)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        kelas = set((a.get("class") or "").split())
        lewati = bool(kelas & self.LEWATI_KELAS) or tag in ("sup", "pre", "img", "script", "style") \
            or (tag == "a" and "ts" in kelas)
        if tag == "table":
            if not self._dilewati() and not any("cover" in k for _, _, k in self.tumpukan):
                self._simpan()
                self.bab[-1]["paragraf"].append("Di bagian ini ada tabel; lihat versi teks untuk rinciannya.")
            lewati = True
        if tag in ("br",):
            self.buf.append(" ")
            return
        if tag in ("img", "hr", "meta", "link", "input"):
            return
        self.tumpukan.append((tag, lewati, kelas))
        if "admonition-title" in kelas:
            self.judul_kotak = True
        if tag == "h1" and not self._dilewati():
            self._simpan()
            self.di_h1 = True
            self.h1_buf = []
        elif tag in self.BLOK and not self._dilewati():
            self._simpan()

    def handle_endtag(self, tag):
        sampul = self._di_sampul()
        while self.tumpukan:
            t, _, _ = self.tumpukan.pop()
            if t == tag:
                break
        if tag == "h1" and self.di_h1:
            judul = rapikan("".join(self.h1_buf))
            self.di_h1 = False
            if sampul:
                self.bab[-1]["paragraf"].append(judul + ".")
            else:
                self.bab.append({"judul": judul, "paragraf": [judul + "."]})
        elif tag in self.BLOK or tag in ("div", "section"):
            self._simpan(akhiran=True, titik_dua=self.judul_kotak)   # tiap blok diakhiri jeda kalimat
            self.judul_kotak = False

    def _di_sampul(self):
        return any("cover" in k for _, _, k in self.tumpukan)

    def handle_data(self, data):
        if self._dilewati():
            return
        (self.h1_buf if self.di_h1 else self.buf).append(data)

    def _simpan(self, akhiran=False, titik_dua=False):
        teks = rapikan("".join(self.buf))
        self.buf = []
        if not teks:
            return
        if titik_dua and teks[-1] not in ".!?:;":
            teks += ":"
        elif akhiran and teks[-1] not in ".!?:;":
            teks += "."
        self.bab[-1]["paragraf"].append(teks)

    def hasil(self):
        self._simpan()
        return [b for b in self.bab if b["paragraf"]]


def rapikan(t: str) -> str:
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"\[\d+(?:[,–-]\d+)*\]", "", t)          # rujukan [3]
    t = t.replace("▶", "").replace("→", " ke ").replace("≈", " kira-kira ")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def bab_dari_html(path: Path):
    p = PengurasHtml()
    p.feed(path.read_text(encoding="utf-8"))
    return p.hasil()


# ---------------------------------------------------------------- teks dari PDF

def bab_dari_pdf(path: Path, judul_dok: str):
    """Ambil teks PDF; judul dikenali dari ukuran huruf (lebih besar dari teks isi)."""
    import pymupdf
    from collections import Counter
    doc = pymupdf.open(path)

    baris = []   # (teks, ukuran, halaman)
    for i, page in enumerate(doc):
        tinggi = page.rect.height
        for blok in page.get_text("dict")["blocks"]:
            for ln in blok.get("lines", []):
                teks = "".join(sp["text"] for sp in ln["spans"]).strip()
                if not teks:
                    continue
                y = ln["bbox"][1]
                if y < tinggi * 0.06 or y > tinggi * 0.94:      # kepala & kaki halaman
                    continue
                ukuran = max(sp["size"] for sp in ln["spans"])
                baris.append((teks, round(ukuran, 1), i))
    if not baris:
        return []

    isi = Counter(u for t, u, _ in baris for _ in range(len(t))).most_common(1)[0][0]
    judul_ukuran = sorted({u for _, u, _ in baris if u >= isi * 1.08}, reverse=True)
    # ukuran terbesar biasanya judul dokumen (sekali); tingkat bab = ukuran judul yang muncul >= 2 kali
    tingkat_bab = next((u for u in judul_ukuran if sum(1 for _, x, _ in baris if x == u) >= 2), None)

    bab, cur, par = [{"judul": "Pembuka", "paragraf": []}], [], []
    judul_buf, judul_uk = [], None

    def tutup_par():
        if par:
            bab[-1]["paragraf"].append(rapikan(" ".join(par)))
            par.clear()

    def tutup_judul():
        nonlocal judul_uk
        if not judul_buf:
            return
        j = rapikan(" ".join(judul_buf))
        if judul_uk == tingkat_bab and not j.lower().startswith(judul_dok.lower()[:25]):
            bab.append({"judul": j, "paragraf": [j + "."]})
        else:
            bab[-1]["paragraf"].append(j if j[-1] in ".!?:" else j + ".")
        judul_buf.clear()
        judul_uk = None

    for teks, uk, _ in baris:
        if uk >= isi * 1.08:
            tutup_par()
            if judul_uk is not None and uk != judul_uk:
                tutup_judul()
            judul_buf.append(teks)
            judul_uk = uk
            continue
        tutup_judul()
        par.append(teks)
        if re.search(r"[.!?:]$", teks) and len(teks) < 90:
            tutup_par()
    tutup_par()
    tutup_judul()
    return [b for b in bab if b["paragraf"]]


# ---------------------------------------------------------------- sintesis

async def sintesis(teks: str, keluar: Path):
    await edge_tts.Communicate(teks, SUARA).save(str(keluar))


def durasi(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


async def buat(bab, keluar: Path):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        batas = asyncio.Semaphore(8)

        # Bab panjang dipecah jadi potongan ±2.500 huruf yang disintesis paralel (satu permintaan
        # edge-tts berjalan berurutan dan lambat untuk teks puluhan ribu huruf).
        potongan = []   # (indeks bab, teks)
        for i, b in enumerate(bab):
            cur = []
            for par in b["paragraf"]:
                if cur and sum(len(x) for x in cur) + len(par) > 2500:
                    potongan.append((i, "\n".join(cur)))
                    cur = []
                cur.append(par)
            if cur:
                potongan.append((i, "\n".join(cur)))

        async def satu(k, teks):
            async with batas:
                f = tmp / f"{k:04d}.mp3"
                for coba in range(4):
                    try:
                        await sintesis(teks, f)
                        return f
                    except Exception as e:
                        if coba == 3:
                            raise
                        print(f"  ulang potongan {k + 1}: {e}")
                        await asyncio.sleep(3 * (coba + 1))

        berkas = await asyncio.gather(*(satu(k, teks) for k, (_, teks) in enumerate(potongan)))
        jeda = tmp / "jeda.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "1.2",
                        "-b:a", "48k", str(jeda)], check=True)
        daftar, bab_meta, t, bab_lalu = [], [], 0.0, None
        for (i, _), f in zip(potongan, berkas):
            if i != bab_lalu:
                if bab_lalu is not None:
                    daftar.append(jeda)
                    t += durasi(jeda)
                bab_meta.append({"judul": bab[i]["judul"], "t": round(t, 1)})
                bab_lalu = i
            daftar.append(f)
            t += durasi(f)
        (tmp / "daftar.txt").write_text("".join(f"file '{f.as_posix()}'\n" for f in daftar), encoding="utf-8")
        keluar.parent.mkdir(parents=True, exist_ok=True)
        sementara = keluar.with_name(keluar.name + ".part")   # .part di-.gitignore: tak ter-commit setengah jadi
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "daftar.txt"),
                        "-c:a", "libopus", "-b:a", "24k", "-ac", "1", "-application", "voip", "-f", "ogg",
                        str(sementara)], check=True)
        sementara.replace(keluar)
        return bab_meta, round(durasi(keluar))


# ---------------------------------------------------------------- dokumen

def semua_dokumen(dengan_pribadi: bool):
    for status, dasar in TEMPAT.items():
        if status == "pribadi" and not dengan_pribadi:
            continue
        for pdf in sorted(dasar.glob("*.pdf")) if dasar.exists() else []:
            meta_path = dasar / "baca" / f"{pdf.stem}.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
            yield {"status": status, "dasar": dasar, "pdf": pdf, "judul": meta.get("judul") or pdf.stem,
                   "kode": meta.get("kode"), "html": dasar / "baca" / f"{pdf.stem}.html",
                   "meta_path": meta_path, "tanpa_audio": bool(meta.get("tanpa_audio"))}


def ambil_bab(d):
    return bab_dari_html(d["html"]) if d["html"].exists() else bab_dari_pdf(d["pdf"], d["judul"])


def hapus_audio(d):
    ada = False
    for ext in (".opus", ".json"):
        f = d["dasar"] / "audio" / f"{d['pdf'].stem}{ext}"
        if f.exists():
            f.unlink()
            ada = True
    return ada


def atur_tanpa_audio(d, tanpa: bool):
    """Tandai dokumen tanpa audio (atau sebaliknya) di metadata baca dan di kerja/<kode>/info.json."""
    paths = [d["meta_path"]]
    if d["kode"]:
        paths.append(ROOT / "kerja" / d["kode"] / "info.json")
    for path in paths:
        if not path.exists():
            continue
        m = json.loads(path.read_text(encoding="utf-8"))
        if tanpa:
            m["tanpa_audio"] = True
        else:
            m.pop("tanpa_audio", None)
        path.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    label = d["judul"] if d["status"] == "publik" else "(dokumen pribadi)"
    if tanpa:
        print(f"{label}: tanpa audio" + (" (audio lama dihapus)." if hapus_audio(d) else "."))
    else:
        print(f"{label}: audio dinyalakan lagi.")


def proses(d):
    if d["tanpa_audio"]:
        if hapus_audio(d):
            print(f"Audio dihapus (tanpa_audio): {d['judul'] if d['status'] == 'publik' else '(dokumen pribadi)'}")
        return False
    bab = ambil_bab(d)
    teks_semua = "\n".join(p for b in bab for p in b["paragraf"])
    sidik = hashlib.sha256(f"{SUARA}|{VERSI_TEKS}|{teks_semua}".encode()).hexdigest()[:12]
    keluar = d["dasar"] / "audio" / f"{d['pdf'].stem}.opus"
    meta_path = keluar.with_suffix(".json")
    if keluar.exists() and meta_path.exists() and json.loads(meta_path.read_text(encoding="utf-8")).get("sidik") == sidik:
        return False
    label = d["judul"] if d["status"] == "publik" else "(dokumen pribadi)"
    print(f"Audio: {label} — {len(bab)} bab, {len(teks_semua):,} huruf…")
    bab_meta, detik = asyncio.run(buat(bab, keluar))
    meta_path.write_text(json.dumps({"sidik": sidik, "suara": SUARA, "durasi": detik, "bab": bab_meta},
                                    ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  selesai: {detik // 60} menit, {keluar.stat().st_size / 1048576:.1f} MB")
    return True


def contoh(d):
    bab = ambil_bab(d)
    teks, n = [], 0
    for b in bab:
        for p in b["paragraf"]:
            teks.append(p)
            n += len(p)
            if n > 450:
                break
        if n > 450:
            break
    keluar = ROOT / "kerja" / "contoh_audio.mp3"
    asyncio.run(sintesis("\n".join(teks), keluar))
    print(f"Contoh: {keluar} ({durasi(keluar):.0f} detik)\n---\n" + "\n".join(teks))


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    dengan_pribadi = "--pribadi" in sys.argv
    dok = list(semua_dokumen(dengan_pribadi or "--contoh" in sys.argv))
    if a:
        q = a[0].lower()
        dok = [d for d in dok if q in d["judul"].lower() or q in d["pdf"].stem.lower() or q == (d["kode"] or "").lower()]
        if not dok:
            sys.exit(f"Tidak ada dokumen yang cocok dengan '{a[0]}'.")
    if "--contoh" in sys.argv:
        return contoh(dok[0])
    if "--matikan" in sys.argv or "--nyalakan" in sys.argv:
        if not a or len(dok) != 1:
            sys.exit("Sebutkan tepat satu dokumen:" + "".join(f"\n  {d['judul']}" for d in dok))
        atur_tanpa_audio(dok[0], "--matikan" in sys.argv)
        if "--nyalakan" in sys.argv:
            dok[0]["tanpa_audio"] = False
            proses(dok[0])
        return
    dibuat = sum(proses(d) for d in dok)
    print(f"Audio dibuat/diperbarui: {dibuat} dari {len(dok)} dokumen.")


if __name__ == "__main__":
    main()
