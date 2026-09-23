# Instruksi untuk agent (Antigravity, Gemini CLI, Codex, dll.)

Baca `CLAUDE.md` untuk gambaran folder ini. Seluruh instruksi berlaku untuk agent apa pun, bukan hanya Claude.

- URL YouTube → ikuti `.claude/skills/daging/SKILL.md`
- Topik riset → ikuti `.claude/skills/riset/SKILL.md`

Di file skill tersebut, `$ARGUMENTS` berarti input dari pengguna (URL atau topik beserta arahannya).
Perintah `/daging` dan `/riset` hanya ada di Claude Code. Agent lain cukup membaca file SKILL.md
dan mengikuti alurnya langsung, memakai alat pencarian/pembuka web milik agent itu sendiri.
Selalu jalankan skrip dari folder ini, misalnya `python scripts/buat_dokumen.py <kode>`.
