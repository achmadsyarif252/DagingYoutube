# DagingYoutube

Folder ini menghasilkan dokumen PDF berbahasa Indonesia yang **komprehensif dan mendalam** ("daging"-nya),
bukan ringkasan. Ada dua jalur:

| Input | Skill | Launcher |
|---|---|---|
| URL video YouTube | `/daging` (`.claude/skills/daging/SKILL.md`) | `DagingYoutube.bat` |
| Topik bebas (sejarah, ekonomi, tokoh, konsep, ...) | `/riset` (`.claude/skills/riset/SKILL.md`) | `DagingTopik.bat` |

- Kalau pengguna menempelkan URL YouTube atau menyebut topik tanpa mengetik perintah, tetap jalankan skill yang sesuai.
- `scripts/ambil_video.py <url>`: metadata dan transkrip → `kerja/<video_id>/`
- `scripts/siapkan_topik.py "<topik>"`: folder riset → `kerja/topik-<slug>/`
- `scripts/buat_dokumen.py <kode>`: `kerja/<kode>/dokumen.md` + `info.json` → `output/*.pdf`
  (dirender dengan Microsoft Edge lewat Playwright; mendukung `[TOC]`, callout `!!!`, catatan kaki `[^n]`,
  dan `[[mm:ss]]` untuk video)
- `buat_dokumen.py` juga menulis versi baca untuk HP: `output/baca/<nama>.html` + `.json`.
- `scripts/terbitkan.py`: susun indeks (`scripts/buat_indeks.py`), lalu commit + push ke GitHub.
  GitHub Actions (`.github/workflows/pages.yml`) menerbitkan app baca PWA (`app/`) beserta `output/`
  ke GitHub Pages. Kalau mengubah file di `app/`, naikkan `VERSI` di `app/sw.js`.
- **Dokumen pribadi (brankas)**: repo dan app publik, tapi dokumen bertanda `"pribadi": true` di
  `kerja/<kode>/info.json` dirender ke `pribadi/` (tidak di-commit) dan terbit hanya dalam bentuk
  terenkripsi di `output/aset/` (judul ikut terenkripsi; dibuka dengan sandi di app).
  Di app, brankas sengaja tersembunyi: hanya dibuka dengan tekan lama tombol Setelan (⚙). Jangan
  menambah tombol/menu/teks yang menunjukkan ada brankas atau dokumen pribadi.
  `scripts/privasi.py sandi | daftar | <cari> pribadi | <cari> publik`. Jangan pernah menulis judul
  atau topik dokumen pribadi ke pesan commit, nama file publik, atau tempat lain yang ikut di-push.
- **Audio (dibacakan)**: `scripts/buat_audio.py [<cari>]` membuat `output/audio/<nama>.opus` + `.json` (bab dan
  waktunya) dengan suara `id-ID-ArdiNeural` lewat edge-tts, lalu ffmpeg (Opus 24 kbps, ±10 MB/jam).
  `terbitkan.py` menjalankannya otomatis (lewati dengan `--tanpa-audio`). Per dokumen: instruksi "no audio"
  → `"tanpa_audio": true` di `info.json`; untuk dokumen yang sudah ada: `buat_audio.py <cari> --matikan`
  (audio dihapus) / `--nyalakan`. Dokumen pribadi hanya dibuatkan
  audio bila `pribadi/.audio` ada, karena teksnya dikirim ke layanan Microsoft.
- Dependensi: `python -m pip install yt-dlp youtube-transcript-api markdown playwright cryptography edge-tts pymupdf`,
  plus `ffmpeg` di PATH.
- Revisi dilakukan dengan mengedit `dokumen.md`, lalu render ulang.
