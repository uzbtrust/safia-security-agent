# Handoff: LOCAL → CLOUD

Append-only; faqat LOCAL chat yozadi. Yangi yozuv pastga qo'shiladi.
Format: sana · yo'nalish · bajarildi · natija yo'llari · bug'lar (reproduce buyrug'i, kutilgan vs haqiqiy, log ≤ 30 qator) · keyingi / savol.

## 2026-10-01 — LOCAL → CLOUD
Bajarildi: T0.3 **qisman**. Jihoz aniqlandi, Ollama server sozlandi va ishga tushirildi. Model yuklash foydalanuvchi qarori bilan keyinga qoldirildi (disk). Smoke test va tok/s hali **o'lchanmagan**.
Natija yo'llari: `docs/HARDWARE.md`, `configs/local/models.yaml`, `configs/local/ollama.env`, `configs/local/serve-ollama.sh`.
Topilmalar (o'lchangan yoki manbasi ko'rsatilgan):
- Jihoz: MacBook Air M4, 16 GB, fansiz. Ollama GPU uchun 11.8 GiB ajratadi (server logi). Bo'sh disk bir necha GB ga tebranadi: 15.3 GB (02:40) → 23.7 GB (03:04), swap 3.3 GB → 0. Reja ≥ 5 GB zaxira bilan, har pull'dan oldin qayta o'lchanadi.
- **Model shortlist.** PLAN §6 dagi gpt-oss-20b (13.79 GB), Devstral (14.33 GB) va Qwen3-Coder-Next (51.74 GB) bu mashinaga sig'maydi (registry manifest hajmlari). Sig'adi: qwen2.5-coder:7b (4.68), qwen3:8b (5.23), gemma4:latest (6.58, hali baholanmagan). 14B'lar (≈ 9 GB) faqat ketma-ket. Taklif: baseline = qwen2.5-coder:7b; H5 uchun bitta oilada juftliklar: 7B va 14B (o'lcham), 7B Q4 va Q8 (kvant).
- **Server kontrakti.** `base_url=http://127.0.0.1:11434/v1`, server-wide ctx 8192 (Ollama'ning o'z default'i bu yerda 4096). Model yuklangach tekshiraman: ctx'dan uzun prompt jim kesiladimi va `/v1` orqali `num_ctx` ni so'rov bilan berib bo'ladimi. Hozircha bu faraz. Agar tasdiqlansa, `openai_compat` klienti `usage.prompt_tokens` ctx'ga yetsa xato ko'tarishi kerak.
- **Reja bo'yicha savol (T1.2 ga ta'sir qiladi).** PLAN §5.1: "temperature 0; yakuniy run 3 seed". Greedy (T=0) da seed ta'sir qilmaydi, 3 run bir xil chiqishi kutiladi (farq faqat suzuvchi nuqta/batch nodeterminizmidan bo'lishi mumkin). Variantlar: T>0 (masalan 0.2) va seed 1..3, yoki T=0 qoldirib barqarorlikni boshqacha o'lchash. Qaror cloud/foydalanuvchida; determinizmni smoke testda o'lchayman.
- Docker o'rnatilmagan (T3.2 gacha kerak emas). To'liq Docker Desktop bu disk uchun og'ir: T3.2 da engilroq runtime yoki tashqi disk haqida avval hajmni o'lchab qaror qilamiz.
Keyingi: foydalanuvchi modelni yuklashga ruxsat bergach (tavsiya: qwen2.5-coder:7b, 4.68 GB) smoke test: JSON-schema (`/v1` `response_format` va native `format`), tok/s (prefill va decode), ctx kesilishi, determinizm, `ollama ps`. T0.2 klienti tayyor bo'lgach smoke test'ni o'sha klient bilan qaytaraman.
Savol: repo public yoki private? (`local/dev` ni push qilishdan oldin kerak)

## 2026-10-01 — LOCAL → CLOUD (2-qadam: BLOCKER, `red_generate` bajarilmadi)
Bajarildi: merge (toza), `uv venv` + `pip install -e ".[dev]"`, `pytest -q`, `scripts/bandit_baseline.py`, `ollama pull qwen2.5-coder:7b`.
Natija: Bandit baseline cloud bilan bir xil (CWE-89 topildi; CWE-639 va CWE-22 topilmadi; toza ilovada FP yo'q; `eval/baselines/bandit.json` o'zgarmadi). `pytest -q`: **7 passed, 7 failed** (cloud'da 14/14).
Bug: hakam macOS'da kod ishga tushira olmaydi · reproduce: `.venv/bin/python -m pytest -q --tb=line` · kutilgan: 14 passed · haqiqiy (0.06 s, subprocess hech qachon ishga tushmadi):
```
FAILED tests/test_referee.py::test_golden_template_is_accepted[CWE-22] / [CWE-639] / [CWE-89]
FAILED tests/test_referee.py::test_exploit_that_always_passes_is_rejected
FAILED tests/test_referee.py::test_exploit_that_fails_on_patched_is_rejected
FAILED tests/test_referee.py::test_patch_that_breaks_functional_tests_is_rejected
FAILED tests/test_referee.py::test_hanging_patch_times_out
subprocess.SubprocessError: Exception occurred in preexec_fn.   (subprocess.py:1994)
$ .venv/bin/python -c 'from safia_sec.gym.referee import _limits; _limits()'
  resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
ValueError: current limit exceeds maximum limit
```
- Sabab: `RLIMIT_AS` macOS'da o'rnatilmaydi (`RLIMIT_CPU` va `RLIMIT_FSIZE` ishlaydi). `preexec_fn` xatosi `judge()` dan chiqib ketadi.
- Xavfliroq: macOS'da `unshare` yo'q, shuning uchun `NETNS=False` va tarmoq izolyatsiyasi yo'q (`Verdict.isolated=False`). Hozir faqat shu RLIMIT_AS xatosi tasodifan "fail-closed" qilib turibdi (model kodi bajarilmaydi).
- AST filtri bo'shliqlari (faqat `check_source` bilan tekshirildi, kod bajarilmadi): `import urllib.request` + `urlopen(...)`, `Path('/abs').write_text(..)` va `os.open('/abs', ..)` filtrdan o'tadi. Faqat `socket` import'i ushlanadi. Tarmoq taqiqi bo'lmasa, test tarmoqqa chiqa oladi.
- Ogohlantirish: RLIMIT_AS'ni shunchaki `try/except` bilan o'tkazib "tuzatmang". Model yozgan kod tarmoq va xotira limitisiz bajarilib ketadi.
Tavsiya (qaror foydalanuvchi/cloud'da): A) generatsiya LOCAL'da, hakam CLOUD'da (Linux, `unshare -rn` ishlaydi): `red_generate.py --no-judge` samples'ni JSON'ga yozadi, cloud `judge` qiladi. B) macOS uchun `sandbox-exec` (tarmoq taqiqi, yozish faqat temp, `$HOME` o'qishini taqiqlash) va izolyatsiya yo'q bo'lsa `judge()` rad etadi. C) Docker (T3.2).
Qadam 5 (`red_generate.py --n 10`) shu sababli bajarilmadi: nechta qabul qilingani va rad sabablari bo'yicha ma'lumot yo'q.

## 2026-10-01 — LOCAL → CLOUD (T0.3 tugadi: real modelda smoke test)
Bajarildi: T0.3. `qwen2.5-coder:7b` yuklandi (Q4_K_M, 4.68 GB, digest `dae161e27b0e`); smoke test `configs/local/smoke_test.py`, sozlamalar `configs/local/`.
Natija: `eval/results/20261001-smoke-ollama-qwen2.5-coder_7b/summary.md`. Hammasi kichik tanlama (n=3 yoki bitta prompt): yo'nalish, isbot emas.
- Tezlik (AC quvvat, ctx 8192): decode 20.2 tok/s (median), prefill 168–199 tok/s, birinchi yuklash 23.5 s, xotirada 5.34 GB, hammasi GPU'da.
- `needs-local-verify` tasdiqlandi: Ollama native `format` ham, `/v1` `response_format` (json_schema) ham sxemaga amal qildi (3/3 va 3/3).
- ⚠ Kontekstdan uzun prompt **jim kesiladi**: mijozga xato yo'q, faqat server logida `WARN truncating input prompt limit=8192 prompt=10865 keep=4`. `/v1` `usage.prompt_tokens` aynan 8192 qaytadi, shu signal bilan aniqlash mumkin. Klient (`openai_compat`) `prompt_tokens >= num_ctx` bo'lsa xato ko'tarishi kerak (agent sikli uchun muhim; `red_generate` promptlari ~800 token, xavf yo'q).
- Determinizm: T=0 da seed 1–3 **bir xil** chiqdi (bitta prompt, 80 token), demak "T=0 + 3 seed" uchta bir xil run beradi. T=0.8 da seed'lar farq qiladi va bir xil seed takrorlanadi. Barqarorlikni o'lchash uchun T>0 kerak (qaror sizda).
- Red namunalari (faqat model chiqishi, kod BAJARILMADI; CWE-89, n=3): valid JSON va sxema 3/3, lekin `old` aniq topilgani 1/3. #0 snippet chekinishini (indentation) tashlab yuborgan, #1 snippet buzilgan va exploit'da sintaksis xatosi bor, #2 topilgan, lekin "zaiflik" qidiruvni buzadi (`LIKE '?'`). Uchala exploit ham gym ilovada yo'q pytest fixture oladi (`client`, `test_client`, `app`; conftest yo'q), promptdagi "faqat `create_app().test_client()`" qoidasiga qaramay. n=3 dan xulosa chiqarmayman: qabul foizi uchun to'liq run kerak.
Keyingi: blocker yechimini (A/B/C) kutaman. Ixtiyoriy (hech narsa bajarilmaydi): `red_generate` ni `--no-judge` bilan n=10 ishga tushirib namunalarni JSON'ga yozish (~7 daqiqa), keyin cloud Linux'da hakam bilan baholaydi.
