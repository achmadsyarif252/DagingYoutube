"""Susun daftar dokumen untuk app baca di HP.

Pemakaian:
    python scripts/buat_indeks.py

Membaca  output/*.pdf dan output/baca/<nama>.json
Menulis  output/index.json

PDF lama yang belum punya output/baca/<nama>.json dibuatkan metadata sekali saja
(judul dari nama file, tanggal dari awalan nama file atau waktu file diubah).
File .json itu ikut di-commit, jadi judul/tanggal bisa dirapikan manual kalau perlu.

Kalau folder pribadi/ ada (hanya di komputer lokal), brankas terenkripsi ikut disusun (lihat brankas.py).
"""

import datetime
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
BACA = OUTPUT / "baca"


def meta_dari_nama(pdf: Path) -> dict:
    nama = pdf.stem
    m = re.match(r"(\d{4}-\d{2}-\d{2})_(.+)", nama)
    if m:
        tanggal, judul = m.group(1), m.group(2).replace("-", " ").strip().capitalize()
    else:
        tanggal = datetime.date.fromtimestamp(pdf.stat().st_mtime).isoformat()
        judul = nama
    return {"judul": judul, "tanggal": tanggal}


def info_audio(dasar: Path, src: str):
    """Metadata audio (dari scripts/buat_audio.py) untuk app, atau None bila belum ada."""
    meta, opus = dasar.with_suffix(".json"), dasar.with_suffix(".opus")
    if not (meta.exists() and opus.exists()):
        return None
    m = json.loads(meta.read_text(encoding="utf-8"))
    return {"src": src, "durasi": m["durasi"], "bab": m["bab"], "v": m["sidik"], "ukuran": opus.stat().st_size}


def main():
    BACA.mkdir(parents=True, exist_ok=True)
    daftar = []
    for pdf in OUTPUT.glob("*.pdf"):
        berkas_meta = BACA / f"{pdf.stem}.json"
        if not berkas_meta.exists():
            berkas_meta.write_text(json.dumps(meta_dari_nama(pdf), ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Metadata baru: {berkas_meta.name}")
        meta = json.loads(berkas_meta.read_text(encoding="utf-8"))
        baca = BACA / f"{pdf.stem}.html"
        daftar.append({
            "id": pdf.stem,
            **meta,
            "pdf": f"output/{pdf.name}",
            "baca": f"output/baca/{baca.name}" if baca.exists() else None,
            "ukuran": pdf.stat().st_size,
            "audio": info_audio(OUTPUT / "audio" / pdf.stem, f"output/audio/{pdf.stem}.opus"),
        })

    daftar.sort(key=lambda d: (d.get("tanggal") or "", d["id"]), reverse=True)
    (OUTPUT / "index.json").write_text(json.dumps(daftar, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Indeks: {len(daftar)} dokumen → output/index.json")

    if (ROOT / "pribadi").exists():
        import brankas
        brankas.susun(meta_dari_nama)


if __name__ == "__main__":
    main()
