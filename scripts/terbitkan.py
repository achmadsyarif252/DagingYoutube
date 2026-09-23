"""Commit dan push semua perubahan ke GitHub, supaya dokumen baru muncul di app HP.

Pemakaian:
    python scripts/terbitkan.py ["pesan commit"]

GitHub Actions (.github/workflows/pages.yml) lalu membangun ulang situs app dalam 1-2 menit.
"""

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent


def git(*args, cek=True):
    return subprocess.run(["git", *args], cwd=ROOT, check=cek, text=True, encoding="utf-8",
                          capture_output=True)


def main():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "buat_indeks.py")], cwd=ROOT, check=True)
    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        print("Tidak ada perubahan untuk diterbitkan.")
        return

    pesan = sys.argv[1] if len(sys.argv) > 1 else ""
    if not pesan:
        # hanya PDF baru; nama PDF yang dihapus (mis. baru dijadikan pribadi) jangan masuk pesan commit
        baru = [baris[3:] for baris in git("status", "--porcelain").stdout.splitlines()
                if baris.startswith("A ") and baris.rstrip('"').endswith(".pdf")]
        pesan = "Dokumen: " + ", ".join(Path(b.strip('"')).stem for b in baru) if baru else "Perbarui dokumen"
    git("commit", "-m", pesan[:200])
    hasil = git("push", cek=False)
    if hasil.returncode != 0:
        sys.exit(f"Commit berhasil, tapi push gagal:\n{hasil.stderr}")
    print(f"Terbit: {pesan[:200]}")


if __name__ == "__main__":
    main()
