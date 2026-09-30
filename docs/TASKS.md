# Vazifalar taxtasi — CLOUD ↔ LOCAL

> Bu taxtani **CLOUD** chat tahrirlaydi. LOCAL chat faqat o'qiydi va o'z xabarlarini `docs/handoff/local.md` ga qo'shadi.
> Holat: `[ ]` ochiq · `[~]` jarayonda · `[x]` tayyor. Oxirgi yangilanish: 2026-10-01 (taxta yaratildi).

---

## 1. Bo'lish qoidasi

**Cloud yozadi va tahlil qiladi; local ishga tushiradi va isbotlaydi.** Model haqidagi har qanday da'vo faqat local run'dan keladi. Cloud'da yozilgan, real modelda sinalmagan kod `needs-local-verify` deb belgilanadi.

Yangi vazifani shu 5 savol bilan tasniflang:

| # | Savol | "Ha" bo'lsa |
|---|---|---|
| 1 | Real LLM (Ollama), GPU, Docker daemon yoki HuggingFace/Ollama/arXiv'dan yuklash kerakmi? | **LOCAL** |
| 2 | Natijasi mock LLM, unit test yoki localhost'dagi Flask bilan tekshiriladimi? | **CLOUD** |
| 3 | Soatlab davom etadimi, yoki "prompt o'zgartir → real javobni ko'r" kabi tez interaktiv sikl kerakmi? | **LOCAL** (cloud'da kutish credit yeydi) |
| 4 | Ko'p token sarflaydimi: katta kod, refaktor, review, log/natija tahlili? | **CLOUD** (credit shu uchun) — kirish ixcham bo'lsin |
| 5 | Sizning o'zingiz qilishingiz/tushunishingiz shartmi: o'qish, FP adjudikatsiya, demo, email, yakuniy matn? | **SIZ** |

Ikkalasi kerak bo'lsa — bo'ling: cloud kod + test yozadi, local real modelda tasdiqlaydi.

**Cloud'da nima ishlaydi (tekshirilgan, 2026-10-01):** Python 3.11, `uv`, PyPI (Bandit, Semgrep — lokal qoidalar bilan offline, tree-sitter, Flask, pytest), public GitHub repo'larni read-only clone (RealVuln va h.k.), localhost'da Flask server. **Ishlamaydi:** GPU, Docker daemon, HuggingFace, Ollama registry, arXiv.

---

## 2. Hamkorlik tartibi

- **Branch'lar:** CLOUD → `claude/wizardly-curie-34voig`; LOCAL → `local/dev` (cloud branch'dan ochiladi). Bir-biridan `git fetch` + `git merge` qiladi. `main`ga yakuniy merge — sizning ishingiz (topshirishdan oldin).
- **Fayl egaligi:** `CLAUDE.md` dagi ro'yxat. Fayllar kesishmasa, konflikt bo'lmaydi. Boshqaning fayliga ≤ 20 qator tuzatish mumkin: commit xabarida `[cross]` + handoff'ga qayd.
- **Prompt'lar kodda emas, fayllarda:** `src/safia_sec/prompts/*.md`. Cloud v0 yozadi, keyin LOCAL egasi. Kod va prompt alohida o'zgaradi.
- **Kontraktlar:** `schemas.py` va `LLMClient` protokolini faqat cloud o'zgartiradi va handoff'da e'lon qiladi.
- **Cloud → local:** kod, testlar, skriptlar, prompt v0. LOCAL: `git fetch origin && git merge origin/claude/wizardly-curie-34voig`.
- **Local → cloud:** `eval/results/**`, prompt'lar, `docs/handoff/local.md`, `docs/HARDWARE.md`. CLOUD: `git fetch origin local/dev && git merge origin/local/dev`.
- **Natija papkasi:** `eval/results/<YYYYMMDD>-<config>-<target>-<model>/` ichida `result.json` (mashina uchun) va `summary.md` (≤ 60 qator: config, model digest, git SHA, metrika jadvali, 5 ta xato namunasi + finding id). Cloud avval `summary.md` ni o'qiydi, kerak bo'lsagina `result.json` ni.
- **Sync ritmi:** har bosqich oxirida va har katta run'dan keyin (kuniga 1–2 marta). Siz xabarchisiz: cloud'ga "local'dan yangi natija bor, fetch qil", local'ga "cloud'da yangi kod bor, merge qil" deb yozasiz.
- **Handoff yozuvi** (append-only, pastga qo'shiladi):
  ```
  ## 2026-10-03 — LOCAL → CLOUD
  Bajarildi: T0.3, T1.6 (prompts v0.2)
  Natija: eval/results/20261003-c1-cakeshop-<model>/summary.md
  Bug: <qisqa sarlavha> · reproduce: `make ...` · kutilgan vs haqiqiy · log ≤ 30 qator
  Keyingi / savol: ...
  ```
- Cloud konteyner vaqtinchalik: sessiya tugashidan oldin commit + push.

**Halol eslatmalar**
1. Cloud'da yozilgan kod real modelda birinchi urinishda ishlamaydi. Har integratsiya nuqtasi (JSON-schema, tool sikli, kontekst uzunligi) uchun 2–3 aylanish kuting. Shuning uchun T0.2 → T0.3 birinchi: avval yupqa, ishlaydigan skelet.
2. Sync sizning vaqtingizni yeydi. Og'irlashsa, soddalashtiring: LOCAL'ni faqat "operator" qiling (run + push), tahlil va tuzatishni cloud'ga bering.

---

## 3. Credit (faqat cloud) — qanday sarflash

- Men qolgan balansni ko'ra olmayman. claude.ai'dagi usage/billing sahifasidan kuzating va credit **muddatini** tekshiring.
- **O'lchang:** T0.1–T0.2 va T1.1–T1.3 dan keyin sarfni ko'ring va qolganini shunga qarab rejalashtiring. Taxminiy qoida (o'lchab sozlang): ~50% qurish (0–3-bosqich), ~25% natijalar tahlili va tuzatish, ~25% zaxira (review, blind v2, yakuniy hujjatlar).
- **Yaxshi ketadi:** katta kod + test yozish, review, natijalar tahlili, blind test yozish.
- **Bekor ketadi:** uzoq run'larni kutish; katta log o'qish (LOCAL `summary.md` tayyorlasin); "salom/tuzatdim" kabi mayda almashinuv; bir vazifani ikki marta qilish; keraksiz subagent va parallel sessiyalar.
- **Parallel cloud sessiyalar:** faqat T0.2 tugagach va modullar kesishmasa (masalan T1.1 / T1.2 / T1.3); ko'pi bilan 2 ta. Bu vaqtni sotib oladi, credit'ni tejamaydi; birlashtirish esa sizning vaqtingizni yeydi.
- Har vazifa uchun DoD tayyor (quyida) — "yaxshi spetsifikatsiya → bir yurishda" ishlang.

---

## 4. Vazifalar

### Bosqich 0 — Asos (1–2-okt)

| ID | Vazifa | Chat | Bog'liq | Tayyor (DoD) |
|---|---|---|---|---|
| [ ] T0.1 | Repo skeleti: `pyproject.toml` (uv), `Makefile`, ruff + pytest, `.github/workflows/ci.yml`, `src/safia_sec/` paketi | CLOUD | — | `make test` yashil, CI ishlaydi |
| [ ] T0.2 | Kontraktlar: `schemas.py` (Finding, Candidate, Hypothesis, Evidence, GroundTruthEntry, RunResult), `LLMClient` protokoli, `llm/mock.py` (skriptlangan javoblar), `llm/openai_compat.py` (Ollama/vLLM, JSON-schema rejimi), `llm/cache.py` (cache + record/replay) | CLOUD | T0.1 | testlar yashil; `needs-local-verify`: Ollama bilan JSON-schema |
| [ ] T0.3 | Jihozni aniqlash (OS/CPU/RAM/GPU), Ollama o'rnatish, 1–2 model pull, smoke test: `openai_compat` klienti bilan JSON-schema so'rov + tok/s o'lchash | LOCAL | T0.2 (klient qismi) | `docs/HARDWARE.md`, `configs/local/models.yaml`, handoff yozuvi |
| [ ] T0.4 | RealVuln'ni clone qilib tekshirish (litsenziya, format, skorlash, hajm); dev/test split va adapter qarori | CLOUD | — | `docs/notes/realvuln.md` |
| [ ] T0.5 | O'qish: PrimeVul, IRIS, Sifting the Noise, RealVuln (abstract + xulosa) | SIZ | — | har biri uchun 2–3 qator o'z xulosangiz |
| [ ] T0.6 | `docs/EXPERIMENTS.md` skeleti: H1–H7 (pre-registration) — natijadan *oldin* commit | CLOUD | — | commit qilingan |

### Bosqich 1 — Skelet + baseline (3–5-okt)

| ID | Vazifa | Chat | Bog'liq | Tayyor (DoD) |
|---|---|---|---|---|
| [ ] T1.1 | CakeShop v1 (Flask, ~20 zaiflik: klassik + biznes-logika) + fixed twin + `ground_truth.yaml` + Flask test-client testlar | CLOUD | T0.1 | testlar yashil; README'da "ataylab zaif" ogohlantirish |
| [ ] T1.2 | Eval harness: matcher, metrikalar, runner, cache, natija jadvali + unit testlar; **C0** (Bandit + Semgrep; qoidalar `.cache/` da, repo'ga ko'chirilmaydi) CakeShop'da — LLM kerak emas | CLOUD | T0.2, T1.1 | C0 natija papkasi (cloud'da haqiqiy run) |
| [ ] T1.3 | Index + tool'lar: tree-sitter, `read_file` (jail), `grep`, `find_def/refs`, `list_routes` | CLOUD | T0.2 | testlar yashil |
| [ ] T1.4 | Yupqa kesim: index → nomzod → LLM triage → report (JSON/MD/SARIF), CLI `safia-sec scan`, prompt v0 | CLOUD | T1.2, T1.3 | mock bilan E2E test yashil; `needs-local-verify` |
| [ ] T1.5 | Real modelda **C1** (LLM-only) va **C2** (triage) run'lari, CakeShop | LOCAL | T0.3, T1.4 | natija papkasi + `summary.md` |
| [ ] T1.6 | Prompt v0 → real modelda 5–10 namunada sozlash; kuzatuvlar | LOCAL | T1.4 | prompt'lar commit + handoff |

### Bosqich 2 — Agent (6–8-okt)

| ID | Vazifa | Chat | Bog'liq | Tayyor (DoD) |
|---|---|---|---|---|
| [ ] T2.1 | Agent: analyst, verifier (JSON-action sikl, byudjet), refuter, L0 iqtibos validatori; skriptlangan mock testlar (to'g'ri yo'l, gallyutsinatsiya, tuzoq) | CLOUD | T1.3, T1.4 | testlar yashil; `needs-local-verify` |
| [ ] T2.2 | Policy + audit + `THREAT_MODEL.md`; security testlari: path-jail, symlink, prompt-injection kanaryasi, HTML escape | CLOUD | T2.1 | testlar yashil |
| [ ] T2.3 | Playbook'lar (Flask/FastAPI/Express) + KB build skriptlari (CWE/OWASP) | CLOUD | — | skript + kichik fixture testlar |
| [ ] T2.4 | KB build'ni ishga tushirish (yuklab olish + Ollama embedding); playbook vs RAG ablation (E4) | LOCAL | T2.3 | natija papkasi |
| [ ] T2.5 | Ablation C2→C4 dev'da real modelda (E3); ≥ 10 xato namunasini yig'ish | LOCAL | T2.1 | natija papkasi |
| [ ] T2.6 | Natijalar tahlili: xato taksonomiyasi, prompt/kod tuzatish takliflari | CLOUD | T2.5 | `docs/notes/failure-analysis-1.md` |
| [ ] T2.7 | **8-okt go/no-go:** LoRA-triage (Tier 3) — faqat jadval orqada bo'lmasa va GPU (lokal/Colab) bo'lsa | SIZ | T2.5 | qaror `PLAN.md` jurnalida |

### Bosqich 3 — Chuqurlik (9–11-okt)

| ID | Vazifa | Chat | Bog'liq | Tayyor (DoD) |
|---|---|---|---|---|
| [ ] T3.1 | Dinamik probe: `http_probe` (allowlist, DNS/redirect tekshiruvi, so'rov limiti), deklarativ probe schema, canary oracle, CakeShop'ni 127.0.0.1'da ishga tushiruvchi harness; testlar (mock LLM probe rejasi). **Docker shart emas** | CLOUD | T2.1 | testlar yashil |
| [ ] T3.2 | Docker: sandbox image + compose; dinamik tekshiruvni Docker ichida sinash (tarmoqsiz, non-root, read-only) | LOCAL | T3.1 | handoff + `docker/` tuzatishlari |
| [ ] T3.3 | Bake-off (E1): `scripts/bakeoff.py` cloud'da, run'lar local'da | CLOUD → LOCAL | T0.3 | natija papkasi |
| [ ] T3.4 | Xotira (FP feedback) + CLI `feedback` *(Tier 2)* | CLOUD | T2.1 | testlar yashil |
| [ ] T3.5 | record/replay + `make replay`; yozib olish local'da | CLOUD + LOCAL | T2.1 | `make replay` GPU'siz ishlaydi |
| [ ] T3.6 | Review: `/code-review`, `/security-review`, `/simplify` — butun kod bazasida | CLOUD | T3.1 | topilmalar tuzatilgan |
| [ ] T3.7 | **Muzlatish:** local/dev merge → `freeze-1` tag | CLOUD (siz tasdiqlaysiz) | hammasi | 11-okt kechqurun |

### Bosqich 4 — Yakuniy baholash (12-okt)

| ID | Vazifa | Chat | Bog'liq | Tayyor (DoD) |
|---|---|---|---|---|
| [ ] T4.1 | CakeShop v2 (blind): *yangi* cloud sessiyada, agent prompt/playbook va ground truth'ni ko'rmagan holda yoziladi (ideal: do'st yozsa) | CLOUD (yangi sessiya) | T3.7 | `targets/cakeshop_v2/` + GT alohida |
| [ ] T4.2 | Test split'da yakuniy run (3 seed) + transcript | LOCAL | T3.7, T4.1 | natija papkalari |
| [ ] T4.3 | ~30 FP'ni qo'lda adjudikatsiya | SIZ | T4.2 | `adjudication.csv` |
| [ ] T4.4 | Natijalarni jadvalga aylantirish, `EXPERIMENTS.md` yakuniy | CLOUD | T4.2, T4.3 | hujjat |
| [ ] T4.5 | *(ixtiyoriy)* Claude (cloud) "reference": test split kodini o'qib, agent formatida finding beradi → harness baholaydi. Natijada "reference, agentning bir qismi emas" deb belgilanadi. **Fine-tune ma'lumoti sifatida ishlatilmaydi** | CLOUD (yangi sessiya) | T4.2 | jadvalda bitta qator |

### Bosqich 5 — Yozish + topshirish (13–14-okt)

| ID | Vazifa | Chat | Bog'liq | Tayyor (DoD) |
|---|---|---|---|---|
| [ ] T5.1 | README, ARCHITECTURE, DECISIONS, LIMITATIONS yakuniy (inglizcha) | CLOUD | T4.4 | |
| [ ] T5.2 | O'z so'zingizda tahrirlash; demo yozuvi (3–5 daq); "yangi odam" testi | SIZ + LOCAL | T5.1 | |
| [ ] T5.3 | Email + repo ruxsatlari + yuborish | SIZ | T5.2 | 14-okt |

### Tier 3 (8-okt go/no-go'dan keyin)

| ID | Vazifa | Chat | Bog'liq | Tayyor (DoD) |
|---|---|---|---|---|
| [ ] T9.1 | LoRA-triage: data-prep skripti (juftlik; split loyiha/vaqt bo'yicha) + training skripti (jihozga qarab Unsloth/MLX/PEFT) | CLOUD | T2.7 | skript + kichik fixture testlar |
| [ ] T9.2 | Datasetni yuklab olish, training (lokal GPU yoki Colab), baseline bilan solishtirish (E7) | LOCAL / SIZ | T9.1 | natija papkasi |
| [ ] T9.3 | Patch taklifi + tekshiruvi | CLOUD → LOCAL | T2.1 | |
| [ ] T9.4 | uz/ru tushuntirish: kod cloud'da, sifatni siz baholaysiz (E8) | CLOUD + SIZ | T2.1 | |

---

## 5. Bug reports

LOCAL bug'larni `docs/handoff/local.md` ga yozadi; CLOUD ularni shu yerga ko'chirib, tuzatgach yopadi.

_(hozircha yo'q)_

---

## 6. Chat boshlash

### LOCAL chatni ishga tushirish

```bash
git clone https://github.com/uzbtrust/safia-security-agent
cd safia-security-agent
git checkout -b local/dev      # default branch = cloud branch; local/dev undan ochiladi
claude                         # Claude Code'ni shu papkada ishga tushiring
```

Birinchi xabar:

```
Sen LOCAL chatsan: bu kompyuterda real LLM (Ollama), GPU va Docker bor.
Repo: Safia ML Engineer case study (lokal AI security agent).
1. CLAUDE.md, docs/PLAN.md, docs/TASKS.md va docs/handoff/cloud.md ni o'qi.
2. local/dev branch'da ishla. Faqat [LOCAL] vazifalarni ol; hozir T0.3
   (jihozni aniqlash, Ollama, 1-2 model, smoke test).
3. Natijani eval/results/<sana>-<config>-<target>-<model>/ ga (result.json +
   summary.md, <= 60 qator) yoz. Katta fayllarni commit qilma.
4. Tugatgach docs/handoff/local.md ga yozuv qo'sh, commit va
   `git push -u origin local/dev`. Muammo bo'lsa handoff'da bug formatida yoz.
5. Raqamlarni to'qima, halol baho ber.
```

### Yangi CLOUD sessiya (masalan T4.1 yoki parallel ish uchun)

```
Sen CLOUD chatsan: GPU/Docker/HuggingFace/Ollama yo'q; PyPI va public GitHub
read-only bor. CLAUDE.md, docs/PLAN.md, docs/TASKS.md va docs/handoff/local.md
ni o'qi. Avval `git fetch origin local/dev` qilib local'dan kelgan natijalarni
ko'r. Faqat [CLOUD] vazifalarni ol. Mock LLM bilan testla; real model kerak
joyni `needs-local-verify` deb belgila. Sessiya oxirida commit + push va
docs/handoff/cloud.md ga yozuv qo'sh.
```

*(T4.1 "blind" sessiyasi uchun alohida, qisqartirilgan prompt yoziladi: u agent prompt'larini va ground truth'ni ko'rmasligi kerak.)*
