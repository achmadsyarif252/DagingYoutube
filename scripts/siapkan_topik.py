"""Siapkan folder kerja untuk riset sebuah topik.

Pemakaian:
    python scripts/siapkan_topik.py "<topik>"

Membuat kerja/topik-<slug>/info.json dan mencetak path foldernya.
"""

import datetime
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent


def slug(teks: str) -> str:
    teks = re.sub(r"[^\w\s-]", "", teks, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s_-]+", "-", teks)[:60] or "topik"


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        sys.exit('Pemakaian: python scripts/siapkan_topik.py "<topik>"')
    topik = sys.argv[1].strip()
    kode = f"topik-{slug(topik)}"
    folder = ROOT / "kerja" / kode
    folder.mkdir(parents=True, exist_ok=True)

    info_path = folder / "info.json"
    if info_path.exists():
        info = json.loads(info_path.read_text(encoding="utf-8"))
    else:
        info = {"jenis": "topik", "id": kode, "judul": topik, "subjudul": "",
                "dibuat": datetime.date.today().isoformat()}
        info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Kode   : {kode}")
    print(f"Folder : {folder}")


if __name__ == "__main__":
    main()
