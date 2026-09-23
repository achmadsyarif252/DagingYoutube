"""Ambil metadata + transkrip lengkap sebuah video YouTube.

Pemakaian:
    python scripts/ambil_video.py <url-youtube>

Hasil disimpan di kerja/<video_id>/:
    info.json       metadata video (judul, channel, durasi, chapter, dll.)
    transkrip.md    transkrip berstempel waktu, dikelompokkan per ~30 detik
"""

import json
import re
import sys
from pathlib import Path

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BAHASA_PRIORITAS = ["id", "en"]
DURASI_BLOK = 30  # detik per paragraf transkrip


def ambil_video_id(url: str) -> str:
    pola = r"(?:v=|youtu\.be/|shorts/|live/|embed/)([A-Za-z0-9_-]{11})"
    m = re.search(pola, url)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url
    sys.exit(f"Tidak bisa menemukan ID video dari: {url}")


def format_waktu(detik: float) -> str:
    detik = int(detik)
    j, sisa = divmod(detik, 3600)
    m, d = divmod(sisa, 60)
    return f"{j}:{m:02d}:{d:02d}" if j else f"{m}:{d:02d}"


def ambil_metadata(video_id: str) -> dict:
    opsi = {"skip_download": True, "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opsi) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    return {
        "id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "judul": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "channel_url": info.get("channel_url"),
        "tanggal_upload": info.get("upload_date"),
        "durasi_detik": info.get("duration"),
        "durasi": format_waktu(info.get("duration") or 0),
        "penonton": info.get("view_count"),
        "bahasa": info.get("language"),
        "tag": info.get("tags") or [],
        "kategori": info.get("categories") or [],
        "thumbnail": info.get("thumbnail"),
        "deskripsi": info.get("description") or "",
        "chapter": [
            {"mulai": format_waktu(c["start_time"]), "judul": c["title"]}
            for c in (info.get("chapters") or [])
        ],
    }


def ambil_transkrip(video_id: str):
    daftar = YouTubeTranscriptApi().list(video_id)
    semua = list(daftar)
    if not semua:
        return None, None
    # Utamakan subtitle manual, lalu otomatis, sesuai urutan bahasa prioritas
    transkrip = None
    for cari in (daftar.find_manually_created_transcript, daftar.find_generated_transcript):
        try:
            transkrip = cari(BAHASA_PRIORITAS)
            break
        except Exception:
            continue
    if transkrip is None:
        transkrip = semua[0]
    jenis = "otomatis" if transkrip.is_generated else "manual"
    return transkrip.fetch(), f"{transkrip.language} ({transkrip.language_code}, {jenis})"


def susun_transkrip(potongan) -> str:
    baris, blok, mulai_blok = [], [], None
    for p in potongan:
        teks = p.text.replace("\n", " ").strip()
        if not teks:
            continue
        if mulai_blok is None:
            mulai_blok = p.start
        blok.append(teks)
        if p.start - mulai_blok >= DURASI_BLOK:
            baris.append(f"[{format_waktu(mulai_blok)}] {' '.join(blok)}")
            blok, mulai_blok = [], None
    if blok:
        baris.append(f"[{format_waktu(mulai_blok)}] {' '.join(blok)}")
    return "\n\n".join(baris)


def main():
    if len(sys.argv) < 2:
        sys.exit("Pemakaian: python scripts/ambil_video.py <url-youtube>")
    video_id = ambil_video_id(sys.argv[1])
    folder = ROOT / "kerja" / video_id
    folder.mkdir(parents=True, exist_ok=True)

    print(f"Mengambil metadata {video_id} ...")
    info = ambil_metadata(video_id)

    print("Mengambil transkrip ...")
    try:
        potongan, sumber = ambil_transkrip(video_id)
    except Exception as e:
        potongan, sumber = None, None
        print(f"  Gagal mengambil transkrip: {type(e).__name__}: {e}")
    info["sumber_transkrip"] = sumber

    (folder / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    if potongan:
        isi = susun_transkrip(potongan)
        (folder / "transkrip.md").write_text(isi, encoding="utf-8")
        jumlah_kata = len(isi.split())
    else:
        jumlah_kata = 0

    print()
    print(f"Judul     : {info['judul']}")
    print(f"Channel   : {info['channel']}")
    print(f"Durasi    : {info['durasi']}")
    print(f"Chapter   : {len(info['chapter'])}")
    print(f"Transkrip : {sumber or 'TIDAK ADA'} — {jumlah_kata} kata")
    print(f"Folder    : {folder}")


if __name__ == "__main__":
    main()
