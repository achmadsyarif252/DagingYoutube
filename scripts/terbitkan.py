"""Commit dan push semua perubahan ke GitHub, supaya dokumen baru muncul di app HP.

Pemakaian:
    python scripts/terbitkan.py ["pesan commit"] [--tanpa-audio]

Sebelum commit, audio dokumen yang belum/berubah dibuat dulu (scripts/buat_audio.py; beberapa menit per
dokumen). Dokumen pribadi ikut dibuatkan audio hanya bila file pribadi/.audio ada (teks dikirim ke edge-tts).

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
    if "--tanpa-audio" not in sys.argv:
        perintah = [sys.executable, str(ROOT / "scripts" / "buat_audio.py")]
        if (ROOT / "pribadi" / ".audio").exists():
            perintah.append("--pribadi")
        if subprocess.run(perintah, cwd=ROOT).returncode != 0:
            print("Peringatan: sebagian audio gagal dibuat; dokumen tetap diterbitkan.")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "buat_indeks.py")], cwd=ROOT, check=True)
    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        print("Tidak ada perubahan untuk diterbitkan.")
        return

    argumen = [a for a in sys.argv[1:] if not a.startswith("--")]
    pesan = argumen[0] if argumen else ""
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
