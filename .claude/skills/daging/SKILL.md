---
name: daging
description: Buat dokumen PDF pembahasan lengkap ("daging") dari sebuah URL video YouTube. Pakai setiap kali pengguna menempelkan link YouTube atau meminta analisis/pembahasan video.
argument-hint: <url-youtube> [arahan tambahan]
---

# /daging — Pembahasan lengkap video YouTube → PDF

Input: $ARGUMENTS (URL YouTube, boleh diikuti arahan tambahan seperti "fokus ke sisi teknis").

## Alur kerja

1. **Ambil bahan**
   `python scripts/ambil_video.py <url>`
   Hasilnya ada di `kerja/<video_id>/`: `info.json` dan `transkrip.md`.
   - Kalau transkrip TIDAK ADA: beri tahu pengguna dan berhenti. Jangan mengarang isi video dari judul/deskripsi saja.

2. **Baca seluruh bahan**: `info.json` (termasuk deskripsi & chapter) dan `transkrip.md` **sampai habis**.
   Transkrip panjang dibaca bertahap dengan offset/limit. Jangan menulis sebelum semua bagian terbaca.

3. **Petakan segmen**: gunakan chapter dari video kalau ada; kalau tidak ada, tentukan sendiri
   pergantian topik berdasarkan transkrip (catat timestamp mulai tiap segmen).

4. **Riset tambahan** (WebSearch/WebFetch) untuk: istilah & konsep kunci, tokoh/data/studi yang disebut,
   verifikasi klaim penting, konteks terbaru, dan pandangan yang berbeda. Catat sumbernya.

5. **Tulis** `kerja/<video_id>/dokumen.md` mengikuti struktur dan standar di bawah.

6. **Render PDF**: `python scripts/buat_dokumen.py <video_id>` → `output/<tanggal>_<judul>.pdf`.
   Lalu **terbitkan** ke app baca di HP: `python scripts/terbitkan.py` (commit + push ke GitHub).
   Kalau push gagal, laporkan pesan errornya; PDF lokal tetap sudah jadi.
   **Pribadi**: kalau pengguna meminta dokumen ini pribadi/rahasia, tambahkan `"pribadi": true` ke
   `info.json` *sebelum* render (PDF lalu ada di `pribadi/`, terbit hanya terenkripsi). Pastikan sandi
   brankas sudah diset (`pribadi/.sandi` ada); kalau belum, minta pengguna menjalankan
   `python scripts/privasi.py sandi` di terminal biasa sebelum menerbitkan.

7. **Laporkan** ke pengguna: path PDF, jumlah bagian, dan 3–5 hal paling menarik dari video (singkat).

## Standar isi

- **Bahasa Indonesia** yang jelas dan enak dibaca, apa pun bahasa videonya. Istilah teknis boleh tetap
  dalam bahasa aslinya, dengan penjelasan saat pertama kali muncul.
- **Komprehensif, bukan ringkasan.** Setiap poin, argumen, contoh, angka, cerita, dan langkah yang ada
  di video harus tercakup. Setelah membaca dokumen ini, pembaca tidak perlu menonton videonya lagi.
- **Ditulis ulang dengan kata-kata sendiri.** Jangan menyalin transkrip. Kutipan langsung maksimal
  satu kalimat pendek, dan hanya bila kalimatnya memang khas atau penting.
- **Nilai tambah di luar video**: jelaskan konsep di balik pernyataan, beri konteks, dan beri contoh
  tambahan bila membantu. Selalu bedakan dengan jelas mana isi video dan mana tambahan (pakai callout).
- **Kritis dan jujur**: tandai klaim yang lemah, keliru, usang, atau hanya opini. Jangan melebih-lebihkan.
- Cantumkan timestamp `[[mm:ss]]` di setiap segmen dan pada poin-poin penting.
- Panjang mengikuti isi. Sebagai patokan: video 20 menit ≈ 10–20 halaman.

## Struktur dokumen.md

Setiap `#` (H1) dimulai di halaman baru dan masuk daftar isi. `##` juga masuk daftar isi.

```markdown
[TOC]

# Gambaran Umum
Siapa pembicara/channelnya (beserta kredibilitasnya), apa tujuan video, untuk siapa, dan
tesis/gagasan utamanya. Tuliskan dalam 2–4 paragraf. Ini pengantar, bukan ringkasan isi.

# Peta Isi
Tabel: | Waktu | Bagian | Inti pembahasan |  (waktu pakai [[mm:ss]])

# Pembahasan Lengkap
## 1. <Judul segmen> [[mm:ss]]
Penjabaran detail dan berurutan: apa yang dikatakan, alasannya, contoh/data/cerita yang dipakai.
Gunakan ### untuk sub-poin bila segmennya padat.

!!! konteks "Konteks tambahan"
    Penjelasan konsep di baliknya, latar belakang, data dari luar video.

!!! kritis "Catatan kritis"
    Klaim yang perlu dicek, bias, penyederhanaan berlebihan, atau hal yang terlewat.

## 2. ...

# Konsep & Istilah Kunci
### <Istilah>
Penjelasan mendalam (bukan definisi satu baris), dan bagaimana istilah itu dipakai di video.

# Pendalaman Topik Terkait
Topik yang hanya disinggung sekilas atau relevan tapi tidak dibahas di video.

# Perspektif Lain
Pandangan yang berbeda atau berlawanan, dengan argumennya. Lewati bila memang tidak relevan.

# Cara Menerapkan
Langkah konkret, checklist, atau latihan (pakai `!!! praktik`). Lewati untuk video yang tidak praktis.

# Kesimpulan
Penilaian keseluruhan: gagasan terkuat, kelemahan, dan untuk siapa video ini paling berguna.

# Referensi & Bacaan Lanjutan
- Sumber yang disebut di video
- Sumber riset tambahan (dengan link)
```

Jenis callout yang tersedia: `konteks` (biru), `kritis` (oranye), `praktik` (hijau), `catatan` (abu-abu).
Isi callout harus diindentasi 4 spasi.
