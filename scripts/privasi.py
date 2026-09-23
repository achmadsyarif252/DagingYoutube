"""Atur dokumen pribadi (brankas) untuk app baca.

Pemakaian:
    python scripts/privasi.py sandi                     set/ganti sandi brankas (disimpan di pribadi/.sandi)
    python scripts/privasi.py daftar                    tampilkan dokumen publik dan pribadi
    python scripts/privasi.py <cari> pribadi            jadikan dokumen pribadi (terenkripsi)
    python scripts/privasi.py <cari> publik             jadikan dokumen publik lagi

<cari> = sebagian judul, nama file, atau kode kerja (mis. V_Aq1Wu1yj8). Setelah itu jalankan
python scripts/terbitkan.py supaya perubahan sampai ke app.
"""

import getpass
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
TEMPAT = {"publik": ROOT / "output", "pribadi": ROOT / "pribadi"}


def semua_dokumen():
    hasil = []
    for status, dasar in TEMPAT.items():
        for pdf in sorted(dasar.glob("*.pdf")) if dasar.exists() else []:
            meta_path = dasar / "baca" / f"{pdf.stem}.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
            hasil.append({"status": status, "pdf": pdf, "judul": meta.get("judul") or pdf.stem, "kode": meta.get("kode")})
    return hasil


def atur_sandi():
    if not sys.stdin.isatty():
        sys.exit("Perintah ini perlu terminal interaktif. Jalankan di jendela PowerShell/CMD biasa,\n"
                 "atau tulis sandinya sendiri ke file pribadi/.sandi (satu baris).")
    s1 = getpass.getpass("Sandi brankas baru: ")
    s2 = getpass.getpass("Ulangi sandi      : ")
    if s1 != s2:
        sys.exit("Sandi tidak sama.")
    if len(s1) < 16:
        print("Peringatan: sandi pendek mudah ditebak. Disarankan 4+ kata acak, mis. kopi-jendela-harimau-senja.")
    TEMPAT["pribadi"].mkdir(exist_ok=True)
    (TEMPAT["pribadi"] / ".sandi").write_text(s1, encoding="utf-8")
    print("Sandi disimpan di pribadi/.sandi. Jika brankas sudah ada, semua dokumen pribadi akan dienkripsi ulang.")
    indeks()


def indeks():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "buat_indeks.py")], cwd=ROOT, check=True)


def pernah_dicommit(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    r = subprocess.run(["git", "log", "--all", "--format=%h", "--", rel], cwd=ROOT, capture_output=True, text=True)
    return bool(r.stdout.strip())


def pindah(cari: str, tujuan: str):
    q = cari.lower()
    cocok = [d for d in semua_dokumen()
             if q in d["judul"].lower() or q in d["pdf"].stem.lower() or q == (d["kode"] or "").lower()]
    if not cocok:
        sys.exit(f"Tidak ada dokumen yang cocok dengan '{cari}'.")
    if len(cocok) > 1:
        sys.exit("Lebih dari satu dokumen cocok, perjelas:\n" + "\n".join(f"  [{d['status']}] {d['judul']}" for d in cocok))
    d = cocok[0]
    if d["status"] == tujuan:
        sys.exit(f"'{d['judul']}' sudah {tujuan}.")
    if tujuan == "pribadi":
        sys.path.insert(0, str(ROOT / "scripts"))
        import brankas
        if not brankas.baca_sandi():
            sys.exit("Sandi brankas belum diset. Jalankan dulu: python scripts/privasi.py sandi")

    asal, ke = TEMPAT[d["status"]], TEMPAT[tujuan]
    (ke / "baca").mkdir(parents=True, exist_ok=True)
    nama = d["pdf"].stem
    tercommit = tujuan == "pribadi" and pernah_dicommit(d["pdf"])

    d["pdf"].replace(ke / d["pdf"].name)
    for ext in (".html", ".json"):
        f = asal / "baca" / f"{nama}{ext}"
        if f.exists():
            f.replace(ke / "baca" / f.name)
    meta_path = ke / "baca" / f"{nama}.json"
    if tujuan == "publik" and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for k in ("acak", "sidik"):
            meta.pop(k, None)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # supaya render ulang dari kerja/ tetap ke tempat yang benar
    if d["kode"]:
        info_path = ROOT / "kerja" / d["kode"] / "info.json"
        if info_path.exists():
            info = json.loads(info_path.read_text(encoding="utf-8"))
            if tujuan == "pribadi":
                info["pribadi"] = True
            else:
                info.pop("pribadi", None)
            info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"'{d['judul']}' sekarang {tujuan}.")
    indeks()
    print("Lanjutkan dengan: python scripts/terbitkan.py")
    if tercommit:
        print("\nPERHATIAN: dokumen ini pernah di-commit terbuka. Setelah terbit, file lamanya masih ada di\n"
              "riwayat git publik. Untuk menghapusnya dari riwayat perlu menulis ulang riwayat + force push.")


def daftar():
    for d in semua_dokumen():
        print(f"  [{d['status']:7}] {d['judul']}")


def main():
    a = sys.argv[1:]
    if a == ["sandi"]:
        atur_sandi()
    elif a == ["daftar"]:
        daftar()
    elif len(a) == 2 and a[1] in TEMPAT:
        pindah(a[0], a[1])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
