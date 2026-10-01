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

## 2026-10-01 — CLOUD → LOCAL (blocker hal qilindi, Red oqimi)
Bajarildi: `local/dev` merge qilindi. Hakam tuzatildi: (1) izolyatsiya bo'lmasa model kodini **rad etadi** (`no_isolation`, fail-closed; `trusted=True` faqat o'zimiz yozgan kod uchun, testlarda); (2) `RLIMIT_AS` faqat Linux'da; (3) AST: `urllib.request/urlopen`, `os.open`, `pathlib`, `write_text/write_bytes`, `from x import <taqiqlangan>` bloklandi. 24 test (yangi: AST bo'shliqlari, no_isolation). Tanlangan A variant: generatsiya LOCAL, hakam CLOUD (`scripts/judge_samples.py`). Red prompti: valid exploit namunasi, fixture taqiqi, indentation talabi; `--no-judge` endi `old` ni ham saqlaydi.
LOCAL nima qilsin: (1) merge qiling; (2) `red_generate.py --model qwen2.5-coder:7b --n 10 --no-judge` (≈7 daq) → push; (3) foydalanuvchi API muhitini qo'ygach: DeepSeek va GLM bilan har CWE uchun `--n 10 --no-judge` (har biri alohida run), push. Men Linux'da `judge_samples.py` bilan baholayman.
Qayd: ctx kesilishi va T=0 determinizm haqidagi topilmalar T0.2 klientiga/T1.2 ga kiritiladi (`prompt_tokens >= num_ctx` → xato; barqarorlik uchun T>0).

## 2026-10-01 — CLOUD → LOCAL (OpenRouter + JEV)
Bajarildi: `red_generate.py` ga `--provider openrouter` (kalit: `OPENROUTER_API_KEY`, base `https://openrouter.ai/api/v1`) qo'shildi `[cross yo'nalishida: cloud local'ning o'zgartirishini kengaytirdi]`; har namunaga `served_by` (OpenRouter qaysi upstream/modelga yo'naltirgani) yoziladi. Fake server bilan sinaldi; real OpenRouter `needs-local-verify`.
LOCAL nima qilsin:
1. Model ID'larni oling (kalit kerak emas): `curl -s https://openrouter.ai/api/v1/models | python3 -c "import sys,json;[print(m['id'],m.get('pricing',{}).get('prompt'),m.get('pricing',{}).get('completion')) for m in json.load(sys.stdin)['data'] if any(k in m['id'].lower() for k in ('deepseek','glm'))]"` — DeepSeek V4.1 Flash va GLM 5.3 Flash ID'larini va narxini toping (bo'lmasa, yaqin variantni so'rang, taxmin qilmang).
2. Har model uchun avval `--cwe CWE-89 --n 3 --no-judge` (smoke), keyin to'liq `--n 10 --no-judge`: `python scripts/red_generate.py --provider openrouter --model <id> --n 10 --no-judge`. Push.
3. JEV: provayder noma'lum. `JEV_TOKEN` bilan ishlash uchun foydalanuvchidan **base URL** va **model ID** so'rang (OpenAI-mos bo'lsa): `RED_API_BASE=<url> RED_API_KEY="$JEV_TOKEN" python scripts/red_generate.py --provider openai --model <id> ...`. OpenAI-mos bo'lmasa, to'xtang va yozing.
Qoida: kalitlar chatga/logga/repo'ga tushmasin; `env` yoki `echo $KEY` chiqarmang. Faqat `gym_apps/shop` kodi yuboriladi.

## 2026-10-01 — CLOUD → LOCAL (Red namunalari hakamda baholandi)
Merge: `local/dev` (aeab4dc). Linux hakamda (netns faol) `judge_samples.py` bilan ikkala to'liq run baholandi → `eval/judged/<run>/`.
| Model | CWE-89 | CWE-639 | CWE-22 | Jami qabul | Har xil (whitespace-normallashgan matn) |
|---|---|---|---|---|---|
| GLM 5.3 Flash | 4/10 | 7/10 | 2/10 | 13/30 | 3 + 5 + 2 = 10 |
| DeepSeek V4.1 Flash | 1/10 | 10/10 | 0/10 | 11/30 | 1 + 2 + 0 = 3 |
Asosiy rad sabablari: GLM — `static_check_exploit` (6; sintaksis xato / taqiqlangan import), `exploit_fails_on_patched` (5), `static_check_patch` (3). DeepSeek — `exploit_fails_on_patched` (15: zaiflik haqiqatda ishlamaydi yoki exploit noto'g'ri).
Xulosa (n=10/CWE, yo'nalish, isbot emas): (1) API Red ishlaydi, qabul ~35–45%; (2) go/no-go chegarasi (CWE boshiga ≥10 har xil) n=10 bilan matematik jihatdan erishib bo'lmaydi, katta n kerak; (3) **diversity cheklovi:** bitta kichik ilovada har CWE uchun zaiflik joyi bitta, "har xil" matnlar ko'pincha bir xil xatoning variantlari (CWE-639: 10/10 qabul, lekin 2 xil). Haqiqiy xilma-xillik uchun ko'proq gym ilovalari/endpoint'lar kerak (cloud vazifasi).
Keyingi (LOCAL): hozircha shart emas, lokal model tanlovi (Blue probe) davom etsin. Keyin kerak bo'lsa GLM bilan `--n 40 --no-judge` (≈ $0.03). Narx hisobi sizdan, baholash mendan.
