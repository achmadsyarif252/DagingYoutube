"""Ubah dokumen Markdown hasil analisis menjadi PDF yang rapi.

Pemakaian:
    python scripts/buat_dokumen.py <video_id>

Membaca  kerja/<video_id>/info.json dan kerja/<video_id>/dokumen.md
Menulis  output/<tanggal>_<judul>.pdf
         output/baca/<tanggal>_<judul>.html dan .json (versi baca untuk app di HP)
Kalau info.json berisi "pribadi": true, semuanya ditulis ke pribadi/ (tidak di-commit) dan hanya
terbit ke app dalam bentuk terenkripsi (lihat scripts/brankas.py).

Sintaks tambahan di dokumen.md:
    [[12:34]] atau [[1:02:03]]   -> link timestamp yang membuka video di detik itu
    [TOC]                        -> daftar isi otomatis
    !!! konteks "Judul"          -> kotak callout (jenis: konteks, kritis, praktik, catatan)
        isi callout (indentasi 4 spasi)
"""

import datetime
import html
import json
import re
import sys
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent

CSS = """
@page { size: A4; margin: 22mm 20mm 20mm 20mm; }
:root {
  --ink: #1d2230; --muted: #5d6475; --accent: #b3261e; --line: #e2e4ea;
  --soft: #f6f7f9;
}
* { box-sizing: border-box; }
body {
  font-family: "Georgia", "Cambria", serif; font-size: 10.8pt; line-height: 1.62;
  color: var(--ink); margin: 0;
}
h1, h2, h3, h4, .cover, .toc, table, .admonition-title, figcaption {
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
a { color: var(--accent); text-decoration: none; }

/* Sampul */
.cover { page-break-after: always; padding-top: 12mm; }
.cover .label { font-size: 9pt; letter-spacing: .18em; text-transform: uppercase; color: var(--accent); font-weight: 700; }
.cover h1 { font-size: 26pt; line-height: 1.2; margin: 6mm 0 8mm; border: none; page-break-before: avoid; }
.cover img { width: 100%; height: 95mm; object-fit: cover; border-radius: 6px; margin-bottom: 8mm; }
.cover table { width: 100%; border-collapse: collapse; font-size: 10pt; }
.cover td { padding: 2.2mm 0; border: none; border-bottom: 1px solid var(--line); vertical-align: top; }
.cover td:first-child { color: var(--muted); width: 34mm; }
.cover .dibuat { margin-top: 10mm; font-size: 8.5pt; color: var(--muted); }
.cover.topik { padding-top: 70mm; }
.cover.topik h1 { font-size: 32pt; }
.cover .subjudul { font-size: 13pt; color: var(--muted); text-align: left; }

/* Catatan kaki (rujukan) */
sup a.footnote-ref { font-family: "Segoe UI", Arial, sans-serif; font-size: 7.5pt; }
.footnote { margin-top: 10mm; font-size: 8.8pt; color: var(--muted); page-break-before: always; }
.footnote::before { content: "Catatan Kaki"; display: block; font-family: "Segoe UI", Arial, sans-serif; font-size: 18pt; font-weight: 700; color: var(--ink); margin-bottom: 5mm; }
.footnote hr { display: none; }
.footnote p { text-align: left; margin-bottom: 1mm; }
.footnote-backref { display: none; }

/* Daftar isi */
.toc { page-break-after: always; }
.toc::before { content: "Daftar Isi"; display: block; font-size: 18pt; font-weight: 700; margin-bottom: 6mm; }
.toc ul { list-style: none; padding-left: 0; margin: 0; }
.toc ul ul { padding-left: 6mm; }
.toc li { margin: 1.4mm 0; font-size: 10pt; }
.toc > ul > li > a { font-weight: 600; }
.toc ul ul a { color: var(--ink); }

/* Isi */
h1 { font-size: 20pt; margin: 0 0 5mm; padding-bottom: 2mm; border-bottom: 2px solid var(--accent); page-break-before: always; }
h2 { font-size: 15pt; margin: 9mm 0 3mm; color: var(--ink); page-break-after: avoid; }
h2::before { content: ""; display: inline-block; width: 4px; height: .9em; background: var(--accent); margin-right: 3mm; vertical-align: -1px; }
h3 { font-size: 12pt; margin: 6mm 0 2mm; page-break-after: avoid; }
h4 { font-size: 10.8pt; margin: 4mm 0 1.5mm; color: var(--muted); page-break-after: avoid; }
p { margin: 0 0 3mm; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 3mm; padding-left: 6mm; }
li { margin: .8mm 0; }
blockquote { margin: 4mm 0; padding: 2mm 5mm; border-left: 3px solid var(--line); color: var(--muted); font-style: italic; }
code { font-family: Consolas, monospace; font-size: 9.5pt; background: var(--soft); padding: .3mm 1.2mm; border-radius: 3px; }
pre { background: var(--soft); padding: 3mm 4mm; border-radius: 4px; overflow: hidden; white-space: pre-wrap; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 3mm 0 5mm; font-size: 9.3pt; page-break-inside: avoid; }
th { background: var(--soft); text-align: left; font-weight: 600; }
th, td { border: 1px solid var(--line); padding: 1.8mm 2.5mm; vertical-align: top; }
hr { border: none; border-top: 1px solid var(--line); margin: 6mm 0; }
a.ts { font-family: "Segoe UI", Arial, sans-serif; font-size: 8.5pt; font-weight: 600; background: #fdecea; color: var(--accent); padding: .2mm 1.6mm; border-radius: 3px; white-space: nowrap; }

/* Callout */
.admonition { margin: 4mm 0; padding: 3mm 4.5mm; border-radius: 5px; border-left: 4px solid; page-break-inside: avoid; }
.admonition p:last-child { margin-bottom: 0; }
.admonition-title { font-weight: 700; font-size: 9.5pt; margin-bottom: 1.5mm !important; text-transform: uppercase; letter-spacing: .05em; }
.admonition.konteks { background: #eef4fb; border-color: #2f6fb3; }
.admonition.konteks .admonition-title { color: #2f6fb3; }
.admonition.kritis  { background: #fdf3e7; border-color: #c76b00; }
.admonition.kritis  .admonition-title { color: #c76b00; }
.admonition.praktik { background: #edf7ef; border-color: #2e8540; }
.admonition.praktik .admonition-title { color: #2e8540; }
.admonition.catatan { background: var(--soft); border-color: #8a8f9c; }
.admonition.catatan .admonition-title { color: #5d6475; }
"""


def ke_detik(ts: str) -> int:
    total = 0
    for bagian in ts.split(":"):
        total = total * 60 + int(bagian)
    return total


def slug(teks: str) -> str:
    teks = re.sub(r"[^\w\s-]", "", teks, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s_-]+", "-", teks)[:70] or "video"


def format_tanggal(yyyymmdd):
    if not yyyymmdd:
        return "-"
    bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
             "Agustus", "September", "Oktober", "November", "Desember"]
    d = datetime.datetime.strptime(yyyymmdd, "%Y%m%d")
    return f"{d.day} {bulan[d.month - 1]} {d.year}"


def buat_sampul_topik(info: dict) -> str:
    e = html.escape
    hari_ini = format_tanggal(datetime.date.today().strftime("%Y%m%d"))
    subjudul = f'<p class="subjudul">{e(info["subjudul"])}</p>' if info.get("subjudul") else ""
    return f"""
<section class="cover topik">
  <div class="label">Daging · Riset Mendalam</div>
  <h1>{e(info.get("judul") or "")}</h1>
  {subjudul}
  <div class="dibuat">Dokumen dibuat {hari_ini}. Disusun dari riset berbagai sumber; rujukan tiap klaim
  tercantum sebagai catatan kaki di akhir dokumen. Data dan angka berlaku per tanggal sumbernya.</div>
</section>"""


def buat_sampul(info: dict) -> str:
    if info.get("jenis") == "topik":
        return buat_sampul_topik(info)
    e = html.escape
    baris = [
        ("Channel", f'<a href="{e(info.get("channel_url") or "")}">{e(info.get("channel") or "-")}</a>'),
        ("Tanggal upload", format_tanggal(info.get("tanggal_upload"))),
        ("Durasi", e(info.get("durasi") or "-")),
        ("Penonton", f'{info["penonton"]:,}'.replace(",", ".") if info.get("penonton") else "-"),
        ("Link video", f'<a href="{e(info["url"])}">{e(info["url"])}</a>'),
    ]
    tabel = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in baris)
    gambar = f'<img src="{e(info["thumbnail"])}">' if info.get("thumbnail") else ""
    hari_ini = format_tanggal(datetime.date.today().strftime("%Y%m%d"))
    return f"""
<section class="cover">
  <div class="label">Daging YouTube · Pembahasan Lengkap</div>
  <h1>{e(info.get("judul") or "")}</h1>
  {gambar}
  <table>{tabel}</table>
  <div class="dibuat">Dokumen dibuat {hari_ini}. Isi merupakan penjabaran dan analisis atas video,
  bukan transkrip kata per kata. Klik timestamp untuk membuka video di bagian tersebut.</div>
</section>"""


def tulis_versi_baca(info: dict, isi_html: str, dasar: Path, nama: str, tanggal: str):
    """Potongan HTML + metadata yang dibaca app di HP (lihat app/ dan scripts/buat_indeks.py)."""
    folder = dasar / "baca"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{nama}.html").write_text(isi_html, encoding="utf-8")
    kunci = ["jenis", "judul", "subjudul", "channel", "url", "thumbnail", "durasi"]
    meta = {k: info[k] for k in kunci if info.get(k)}
    lama = folder / f"{nama}.json"
    if lama.exists():   # pertahankan id acak brankas bila dokumen dirender ulang
        meta.update({k: v for k, v in json.loads(lama.read_text(encoding="utf-8")).items() if k in ("acak", "sidik")})
    meta.setdefault("jenis", "video")
    meta["kode"] = info["id"]
    meta["tanggal"] = tanggal
    (folder / f"{nama}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        sys.exit("Pemakaian: python scripts/buat_dokumen.py <video_id>")
    folder = ROOT / "kerja" / sys.argv[1]
    info = json.loads((folder / "info.json").read_text(encoding="utf-8"))
    teks = (folder / "dokumen.md").read_text(encoding="utf-8")

    def link_ts(m):
        ts = m.group(1)
        return f'<a class="ts" href="https://youtu.be/{info["id"]}?t={ke_detik(ts)}">▶ {ts}</a>'

    if info.get("jenis") != "topik":
        teks = re.sub(r"\[\[(\d{1,2}(?::\d{2}){1,2})\]\]", link_ts, teks)

    isi = markdown.markdown(
        teks,
        extensions=["extra", "toc", "sane_lists", "admonition"],
        extension_configs={"toc": {"toc_depth": "1-2", "title": ""}},
    )
    halaman = f"""<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<title>{html.escape(info.get("judul") or "")}</title><style>{CSS}</style></head>
<body>{buat_sampul(info)}{isi}</body></html>"""

    (folder / "dokumen.html").write_text(halaman, encoding="utf-8")

    tanggal = datetime.date.today().isoformat()
    dasar = ROOT / ("pribadi" if info.get("pribadi") else "output")
    keluaran = dasar / f"{tanggal}_{slug(info.get('judul') or info['id'])}.pdf"
    keluaran.parent.mkdir(exist_ok=True)
    tulis_versi_baca(info, buat_sampul(info) + isi, dasar, keluaran.stem, tanggal)

    kaki = (
        '<div style="width:100%;font-family:Segoe UI,Arial;font-size:7.5pt;color:#8a8f9c;'
        'padding:0 20mm;display:flex;justify-content:space-between;">'
        f'<span>{html.escape((info.get("judul") or "")[:90])}</span>'
        '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page()
        page.goto((folder / "dokumen.html").as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(keluaran),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            display_header_footer=True,
            header_template="<span></span>",
            footer_template=kaki,
            outline=True,
            tagged=True,
        )
        browser.close()

    print(f"PDF selesai: {keluaran}")


if __name__ == "__main__":
    main()
