# Handoff: CLOUD → LOCAL

Append-only; faqat CLOUD chat yozadi. Yangi yozuv pastga qo'shiladi.
Format: sana · yo'nalish · bajarildi · LOCAL nima qilsin (aniq buyruqlar) · ochiq savollar.

## 2026-10-01 — CLOUD → LOCAL
Bajarildi: reja (`docs/PLAN.md`), vazifa taxtasi (`docs/TASKS.md`), `CLAUDE.md`, `.gitignore`.
LOCAL nima qilsin: `docs/TASKS.md` §6 dagi ko'rsatma bo'yicha `local/dev` branch'ini ochib, LOCAL chatni ishga tushiring. Birinchi vazifa — T0.3 (jihozni aniqlash, Ollama, 1–2 model, smoke test). Smoke test klient kodi (T0.2) tayyor bo'lgach to'liq ishlaydi; shu vaqtgacha jihoz va Ollama qismini bajaring.
Ochiq savollar: kuniga necha soat? Repo public yoki private?

## 2026-10-01 — CLOUD → LOCAL (v2)
Bajarildi: reja v2 (Red vs Blue), `TASKS.md` v2; hakam (`src/safia_sec/gym/referee.py`), toza ilova (`gym_apps/shop`), 3 CWE shablon, 14 test, Bandit baseline, `scripts/red_generate.py`.
LOCAL nima qilsin: `docs/TASKS.md` dagi «2-qadam» buyruqlari (merge, pip install, pytest, ollama pull, red_generate). Natijani `eval/results/` ga commit qiling.
needs-local-verify: `red_generate.py` faqat soxta Ollama serveri bilan sinalgan; real modelda JSON-schema (`format`) ishlashini tekshiring.

## 2026-10-01 — CLOUD → LOCAL (jihoz)
Jihoz: RAM 16 GB, bo'sh disk ~52 GB. `TASKS.md` da «Jihoz» bo'limi qo'shildi (model byudjeti, disk limiti). 2-qadamni `qwen2.5-coder:7b` bilan boshlang; `docs/HARDWARE.md` ga CPU/GPU/OS ni yozing.
