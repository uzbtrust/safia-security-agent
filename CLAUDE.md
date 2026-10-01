# Safia security agent — Claude Code yo'riqnomasi

Repo: Safia (AI Team) ML Engineer case study — **lokal AI security agent**. Reja: `docs/PLAN.md`. Vazifalar taxtasi: `docs/TASKS.md`. Muddat ~2026-10-15, topshirish maqsadi 2026-10-14.

## Ikki chat, bitta repo
- **CLOUD** chat (Claude Code on the web; foydalanuvchining credit'i ketadi): kod, testlar (mock LLM), hujjat, review, natijalar tahlili. GPU, Docker daemon, HuggingFace/Ollama/arXiv **yo'q**; PyPI va public GitHub'ni read-only clone bor.
- **LOCAL** chat (foydalanuvchi kompyuteri): real LLM (Ollama), GPU, Docker, uzoq run'lar, prompt sozlash, demo.
- Qaysi chat ekaningni foydalanuvchi birinchi xabarda aytadi. Ishni boshlashdan oldin `docs/TASKS.md` va `docs/handoff/*.md` ni o'qi; faqat o'z chating vazifalarini ol.
- Haqiqat manbai: model haqidagi har qanday da'vo **local run**dan keladi. Cloud'da yozilgan va real modelda sinalmagan kod `needs-local-verify` deb belgilanadi.

## Fayl egaligi (konfliktsiz ishlash uchun)
- CLOUD: `src/**` (prompts/ dan tashqari), `gym_apps/**`, `targets/**`, `tests/**`, `scripts/**`, `docs/**` (`handoff/local.md` va `HARDWARE.md` dan tashqari), `.github/**`, `Makefile`, `pyproject.toml`, `.gitignore`.
- LOCAL: `src/safia_sec/prompts/**`, `configs/local/**`, `eval/results/**`, `eval/replays/**`, `docs/handoff/local.md`, `docs/HARDWARE.md`.
- Boshqaning fayliga kichik tuzatish (≤ 20 qator) kerak bo'lsa — mumkin: commit xabarida `[cross]` yoz va handoff'ga qayd qil. Kattasini handoff'da so'ra.
- Branch'lar: CLOUD → `claude/wizardly-curie-34voig`; LOCAL → `local/dev`. Bir-biridan `git fetch` + `git merge` qiladi; `main`ga yakuniy merge'ni foydalanuvchi qiladi.

## Qoidalar
- **Raqamlarni hech qachon to'qima.** Hujjatdagi har bir metrika `eval/results/*/result.json` dagi haqiqiy run'dan. Halol baho ber: muammo va xavfni yashirma, natijani chiroyli ko'rsatma.
- **Xavfsizlik doirasi:** faqat o'zimizniki va lokal lablar. Begona tizimga so'rov yo'q. Agentning o'ziga umumiy shell tool berilmaydi. Dinamik tekshiruv faqat allowlist'dagi host'ga (127.0.0.1).
- Agent mahsulot yo'lida to'liq lokal: cloud LLM yo'q. Cloud modelni faqat ochiq belgilangan "reference" sifatida baholashda ishlatish mumkin; uning chiqishlari fine-tune ma'lumoti bo'lmaydi.
- Til: foydalanuvchi bilan o'zbekcha (lotin). Kod, izohlar, commit xabarlari, README/DECISIONS/EXPERIMENTS/ARCHITECTURE/LIMITATIONS/THREAT_MODEL — inglizcha. `PLAN.md` va `TASKS.md` — o'zbekcha.
- Katta fayllar (model, cache, dataset) commit qilinmaydi. Natija — kichik JSON + `summary.md` (≤ 60 qator).
- Commit'lar kichik va ma'noli. Sessiya tugashidan oldin commit + push (cloud konteyner vaqtinchalik).
