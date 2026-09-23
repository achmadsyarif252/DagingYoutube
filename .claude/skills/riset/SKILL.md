---
name: riset
description: Buat dokumen PDF riset mendalam dan komprehensif tentang suatu topik (sejarah, ekonomi, sains, tokoh, konsep, dll.) berdasarkan riset web. Pakai ketika pengguna memberi topik, bukan URL YouTube.
argument-hint: <topik> [arahan tambahan]
---

# /riset — Dokumen riset mendalam tentang suatu topik → PDF

Input: $ARGUMENTS (topik, boleh diikuti arahan seperti "fokus periode 1945–1998" atau "untuk pemula").

## Alur kerja

1. **Siapkan folder**
   `python scripts/siapkan_topik.py "<topik>"` → mencetak `Kode` dan folder `kerja/topik-<slug>/`.
   Setelah ruang lingkup jelas, perbarui `judul` (nama rapi) dan `subjudul` (ruang lingkup
   satu kalimat) di `info.json`.

2. **Tentukan ruang lingkup dan kerangka**: jenis topiknya apa (lihat "Kerangka per jenis topik"),
   batas waktu/wilayah, dan pertanyaan-pertanyaan yang harus dijawab dokumen.
   Kalau topiknya terlalu luas untuk satu dokumen (misal "sejarah dunia"), pilih cakupan yang masuk akal,
   jelaskan pilihan itu di Pendahuluan, dan sebutkan saat melapor.

3. **Riset** dengan WebSearch/WebFetch, dan catat setiap sumber (judul, penerbit, tahun, URL) di
   `kerja/<kode>/sumber.md` selama bekerja.
   - Lakukan banyak pencarian dari berbagai sudut, dengan kueri bahasa Indonesia **dan** Inggris.
   - Utamakan sumber kredibel: jurnal/akademik, lembaga resmi (BPS, Bank Indonesia, World Bank, IMF,
     PBB, kementerian), ensiklopedia bereputasi, media arus utama, dan buku.
   - Angka penting dicek silang ke minimal 2 sumber. Selalu catat tahun datanya.
   - Target: minimal ~15 sumber berbeda untuk topik besar.

4. **Tulis** `kerja/<kode>/dokumen.md` sesuai standar dan struktur di bawah.

5. **Render PDF**: `python scripts/buat_dokumen.py <kode>` → `output/<tanggal>_<judul>.pdf`.
   Lalu **terbitkan** ke app baca di HP: `python scripts/terbitkan.py` (commit + push ke GitHub).
   Kalau push gagal, laporkan pesan errornya; PDF lokal tetap sudah jadi.
   **Pribadi**: kalau pengguna meminta dokumen ini pribadi/rahasia, tambahkan `"pribadi": true` ke
   `info.json` *sebelum* render (PDF lalu ada di `pribadi/`, terbit hanya terenkripsi). Pastikan sandi
   brankas sudah diset (`pribadi/.sandi` ada); kalau belum, minta pengguna menjalankan
   `python scripts/privasi.py sandi` di terminal biasa sebelum menerbitkan.

6. **Laporkan**: path PDF, ruang lingkup yang dipilih, jumlah sumber, dan 3–5 temuan paling menarik.

## Standar isi

- **Bahasa Indonesia**, jelas dan mengalir seperti buku populer yang serius, bukan daftar poin.
- **Komprehensif dan mendalam**: jelaskan *mengapa* dan *bagaimana*, bukan hanya *apa*.
  Hubungkan sebab-akibat antarbagian. Pembaca awam harus bisa mengikuti, dan pembaca yang sudah paham
  tetap mendapat hal baru.
- **Setiap klaim faktual penting diberi rujukan** dengan catatan kaki Markdown: `...tumbuh 5,0%[^3].`
  lalu definisikan `[^3]: Penulis/Lembaga, *Judul*, Tahun. <https://url-lengkap>` di akhir file
  (URL dalam kurung sudut `< >` supaya bisa diklik di PDF).
- **Tulis dengan kata-kata sendiri.** Kutipan langsung dibuat singkat (maksimal 1–2 kalimat) dan diberi rujukan.
- **Jujur soal ketidakpastian**: bedakan fakta, interpretasi, dan perdebatan. Tandai data yang lama atau
  diperdebatkan. Jangan pernah mengarang angka, tanggal, kutipan, atau sumber.
- Pakai tabel untuk data dan perbandingan, serta callout untuk sorotan:
  `!!! konteks`, `!!! kritis`, `!!! catatan`, `!!! praktik` (isi diindentasi 4 spasi).
- Panjang mengikuti kedalaman topik. Patokan untuk topik besar: 20–40 halaman.

## Struktur dokumen.md

Setiap `#` (H1) dimulai di halaman baru dan masuk daftar isi bersama `##`.

```markdown
[TOC]

# Pendahuluan
Apa topiknya, mengapa penting, ruang lingkup dan batasannya, serta cara membaca dokumen ini.

# Gambaran Besar
Peta konsep, yaitu pemahaman utuh dalam 1–2 halaman sebelum masuk ke detail.
Boleh ditambah tabel "Fakta Kunci".

# <Bagian inti 1..n>   ← sesuai kerangka per jenis topik, beberapa H1 dengan ## dan ###

# Data & Angka Kunci
Tabel-tabel utama beserta tahun dan sumbernya.

# Perdebatan & Perspektif
Isu yang diperdebatkan, aliran pemikiran berbeda, dan argumen tiap pihak.

# Kondisi Terkini & Prospek
Keadaan saat ini (sebutkan per tanggal berapa), tren, dan skenario ke depan.

# Kronologi            ← untuk topik sejarah/perkembangan: tabel | Tahun | Peristiwa |
# Glosarium            ← istilah penting dengan penjelasan yang cukup
# Kesimpulan           ← sintesis dan pelajaran utama, bukan pengulangan
# Bacaan Lanjutan      ← buku/sumber terbaik untuk mendalami, dengan alasan singkat

[^1]: ... (definisi catatan kaki, dikumpulkan di akhir; otomatis jadi halaman "Catatan Kaki")
```

## Kerangka per jenis topik (untuk bagian inti)

- **Sejarah (negara/peristiwa/institusi)**: latar sebelum peristiwa, lalu per periode/era secara kronologis
  (aktor, kebijakan, peristiwa, sebab-akibat), titik balik, dampak jangka panjang, dan warisan hari ini.
- **Ekonomi (negara/sektor)**: struktur ekonomi dan sektor utama, sejarah perkembangan dan krisis,
  indikator makro (PDB, inflasi, utang, perdagangan, ketenagakerjaan), kebijakan fiskal dan moneter,
  kekuatan dan kelemahan struktural, perbandingan dengan negara sejenis, serta tantangan dan peluang.
- **Tokoh**: latar dan pembentukan, perjalanan hidup per fase, gagasan dan karya, pengaruh, kontroversi, warisan.
- **Konsep/ilmu/teknologi**: definisi dan intuisi, sejarah penemuan, cara kerja/mekanisme, contoh dan
  penerapan, batasan dan miskonsepsi, serta perkembangan terbaru.
- **Isu/kebijakan**: akar masalah, para pihak dan kepentingannya, data, opsi kebijakan beserta
  bukti efektivitasnya, dan pengalaman negara lain.
- Topik gabungan (misal "sejarah ekonomi Jepang"): gabungkan kerangka yang relevan.
