"""Brankas: dokumen pribadi yang hanya bisa dibuka dengan sandi di app baca.

Dokumen pribadi disimpan polos di pribadi/ (tidak di-commit). Yang terbit ke repo publik hanya:
    output/rahasia/brankas.json   daftar dokumen pribadi, terenkripsi (judul pun tidak terbaca)
    output/rahasia/<acak>-p.bin   PDF terenkripsi
    output/rahasia/<acak>-b.bin   versi baca HTML (gzip) terenkripsi

Kripto: PBKDF2-SHA256 (600.000 iterasi) -> kunci AES-256-GCM. Format .bin = iv(12 byte) + ciphertext.
Harus cocok dengan app/app.js (fungsi brankas).

Sandi dibaca dari env DAGING_SANDI atau file pribadi/.sandi (set lewat: python scripts/privasi.py sandi).
"""

import base64
import gzip
import hashlib
import json
import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent.parent
PRIBADI = ROOT / "pribadi"
RAHASIA = ROOT / "output" / "rahasia"
BERKAS_SANDI = PRIBADI / ".sandi"
ITERASI = 600_000
CEK = b"daging-brankas-v1"


def baca_sandi():
    s = os.environ.get("DAGING_SANDI") or (BERKAS_SANDI.read_text(encoding="utf-8").strip() if BERKAS_SANDI.exists() else "")
    return s or None


def turunkan_kunci(sandi: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", sandi.encode("utf-8"), salt, ITERASI, 32)


def enkripsi(kunci: bytes, data: bytes) -> bytes:
    iv = secrets.token_bytes(12)
    return iv + AESGCM(kunci).encrypt(iv, data, None)


def dekripsi(kunci: bytes, data: bytes) -> bytes:
    return AESGCM(kunci).decrypt(data[:12], data[12:], None)


b64 = lambda b: base64.b64encode(b).decode()
unb64 = base64.b64decode


def susun(meta_dari_nama):
    """Enkripsi ulang isi pribadi/ ke output/rahasia/. Hanya menulis file yang benar-benar berubah."""
    pdfs = sorted(PRIBADI.glob("*.pdf")) if PRIBADI.exists() else []
    berkas_brankas = RAHASIA / "brankas.json"
    if not pdfs:
        if RAHASIA.exists():
            for f in RAHASIA.iterdir():
                f.unlink()
            RAHASIA.rmdir()
            print("Brankas kosong: output/rahasia/ dihapus.")
        return
    sandi = baca_sandi()
    if not sandi:
        print("Brankas DILEWATI: sandi belum diset (python scripts/privasi.py sandi).")
        return

    lama = json.loads(berkas_brankas.read_text(encoding="utf-8")) if berkas_brankas.exists() else None
    kunci, ganti = None, True
    if lama:
        k = turunkan_kunci(sandi, unb64(lama["salt"]))
        try:
            if dekripsi(k, unb64(lama["cek"])) == CEK:
                kunci, salt, ganti = k, unb64(lama["salt"]), False
        except Exception:
            pass
        if ganti:
            print("Sandi berbeda dari brankas lama: semua dokumen pribadi dienkripsi ulang.")
    if ganti:
        salt = secrets.token_bytes(16)
        kunci = turunkan_kunci(sandi, salt)

    RAHASIA.mkdir(parents=True, exist_ok=True)
    (PRIBADI / "baca").mkdir(parents=True, exist_ok=True)
    entri, dipakai = [], {"brankas.json"}
    for pdf in pdfs:
        berkas_meta = PRIBADI / "baca" / f"{pdf.stem}.json"
        meta = json.loads(berkas_meta.read_text(encoding="utf-8")) if berkas_meta.exists() else meta_dari_nama(pdf)
        meta.setdefault("acak", secrets.token_hex(8))
        html = PRIBADI / "baca" / f"{pdf.stem}.html"
        isi_pdf = pdf.read_bytes()
        isi_html = html.read_bytes() if html.exists() else None
        sidik = hashlib.sha256(isi_pdf + (isi_html or b"")).hexdigest()[:12]

        a = meta["acak"]
        bin_pdf, bin_html = RAHASIA / f"{a}-p.bin", RAHASIA / f"{a}-b.bin"
        if ganti or meta.get("sidik") != sidik or not bin_pdf.exists() or (isi_html and not bin_html.exists()):
            bin_pdf.write_bytes(enkripsi(kunci, isi_pdf))
            if isi_html:
                bin_html.write_bytes(enkripsi(kunci, gzip.compress(isi_html, mtime=0)))
            meta["sidik"] = sidik
            print(f"Dienkripsi: {pdf.stem}")
        berkas_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        dipakai.add(bin_pdf.name)
        if isi_html:
            dipakai.add(bin_html.name)
        publik = {k: v for k, v in meta.items() if k not in ("acak", "sidik")}
        entri.append({
            "id": f"p-{a}", **publik,
            "pdf": f"output/rahasia/{bin_pdf.name}",
            "baca": f"output/rahasia/{bin_html.name}" if isi_html else None,
            # v ikut berubah saat sandi diganti, supaya HP tidak memakai salinan lama dari cache
            "ukuran": len(isi_pdf), "v": sidik + salt.hex()[:6], "pribadi": True,
        })

    for f in RAHASIA.iterdir():
        if f.name not in dipakai:
            f.unlink()

    entri.sort(key=lambda d: (d.get("tanggal") or "", d["id"]), reverse=True)
    data_entri = json.dumps(entri, ensure_ascii=False, sort_keys=True).encode("utf-8")
    if lama and not ganti:
        try:
            if dekripsi(kunci, unb64(lama["entri"])) == data_entri:
                print(f"Brankas: {len(entri)} dokumen pribadi (tidak berubah).")
                return
        except Exception:
            pass
    brankas = {
        "v": 1, "kdf": "PBKDF2-SHA256", "iterasi": ITERASI, "salt": b64(salt),
        "cek": lama["cek"] if (lama and not ganti) else b64(enkripsi(kunci, CEK)),
        "entri": b64(enkripsi(kunci, data_entri)),
    }
    berkas_brankas.write_text(json.dumps(brankas, indent=1), encoding="utf-8")
    print(f"Brankas: {len(entri)} dokumen pribadi.")
