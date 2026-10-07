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

## 2026-10-01 — CLOUD → LOCAL (3 ta gym ilova, 11 zaiflik shabloni)
Bajarildi: yangi toza ilovalar `gym_apps/bank` (IDOR, **biznes-logika: manfiy o'tkazma**, SQLi, path traversal) va `gym_apps/blog` (**reflected XSS, mass assignment, bashorat qilinadigan reset token, open redirect**) + `shop`. Jami 11 shablon (`src/safia_sec/gym/injections.py`: `APPS`, `all_templates()`, `build(cwe, app)`), yangi CWE'lar: 840, 79, 915, 330, 601. Har bir shablon hakamdan o'tadi (36 test yashil). Bandit baseline: **2/11** (faqat SQLi ikki ilovada), toza kodda FP yo'q (`eval/baselines/bandit.json`).
`red_generate.py`: yangi `--app all|shop|bank|blog` (default **all**), har namunada `app` maydoni, natija kaliti `app/CWE`; `judge_samples.py` ham ko'p ilovali. Eski (faqat shop) natijalar uchun `app` yo'q bo'lsa `shop` deb olinadi.
LOCAL nima qilsin (model tanlovi tugagach, shoshilmasdan): merge qiling. (1) `blue_probe.py` ni `APPS` bo'yicha kengaytiring: 11 zaif + 3 toza ilova ustida (hozir faqat shop). Model tanlovi uchun avvalgi probe qoladi, kengaytirilgani keyingi o'lchov. (2) Red: GLM bilan `--app all --n 10 --no-judge` (110 so'rov, taxminan $0.03). Narx hisobini yozing.

## 2026-10-01 — CLOUD → LOCAL (Blue v0 tayyor: `safia-sec scan` va `eval-gym`)
Bajarildi: `src/safia_sec/blue/` (llm, scanner, report, score, evaluate), `src/safia_sec/cli.py`, promptlar `src/safia_sec/prompts/{detect,verify}.md`, `docs/EXPERIMENTS.md` (protokol v3 va gipotezalar NATIJADAN OLDIN), 20 yangi test (jami 56 yashil, mock model bilan).
Blue konveyeri: detect (JSON-schema, maxItems 8, matn <= 300) → **ground** (iqtibos haqiqatan fayldami; qator iqtibos joyiga to'g'rilanadi; yo'q bo'lsa tashlanadi) → **Bandit** (mustaqil tasdiq/qo'shimcha nomzod) → **verify** (refuter: rad etishga uringan 2-chaqiruv + fix taklifi). `stages` har bosqich natijasini saqlaydi (verification gain o'lchanadi). Probe'dan olingan qoidalar kodda: thinking off, T>0 + seed, `prompt_tokens >= num_ctx` → xato, kesh `.cache/llm` (qayta run bepul).
needs-local-verify: Ollama bilan real ishlash (JSON-schema, `think:false`, gemma4:12b / qwen3.5:9b). Skorlash protokoli v3: PRIMARY = function-level hit (probe'dagi IDOR kuzatuvidan keyin tanlangan; faqat shu commit'dan keyingi run'larga qo'llanadi), strict ham doim ko'rsatiladi.
LOCAL nima qilsin (DEV split: faqat shop va bank; **blog = test, hozir ishga tushirmang**):
1. `git fetch origin && git merge origin/claude/wizardly-curie-34voig`; `pip install -e ".[dev]"` (yangi `safia-sec` buyrug'i uchun); `pytest -q` (56 o'tishi kerak, 1 skip).
2. Ilovalarni yoping (gemma ≈ +10.8 GB wired). Smoke: `.venv/bin/safia-sec scan gym_apps/shop --model gemma4:12b --notes "Users are identified by the X-User header in this toy app; do not report that as a finding." --out /tmp/scan_shop` — hisobotni (report.md) o'qib, g'alati joylarini yozing. Eslatma: gym_apps/shop TOZA versiya, topilma bo'lsa u soxta signal.
3. DEV eval: `.venv/bin/safia-sec eval-gym --model gemma4:12b --apps shop bank --seeds 1 2 3` (≈ 25–30 daqiqa taxmin; 9 holat × 3 seed, detect + verify chaqiruvlari). Keyin xuddi shu `qwen3.5:9b` bilan. Natija `eval/results/<sana>-blue-gym-<model>/` (result.json + summary.md); push.
4. Xatolar `meta.errors` da ko'rinadi (JSON, kontekst). Muammo bo'lsa handoff'ga yozing, promptni o'zgartirmang (promptlar `src/safia_sec/prompts/*.md` — tuzatishlar faqat DEV natijalariga qarab, sababi bilan).

## 2026-10-07 — CLOUD (Claude-authored Red variants; narrowed the Claude-output policy)
Foydalanuvchi: DeepSeek o'rniga Claude'ni (Opus/Sonnet 5.5, obuna doirasida, tekin) Red data uchun ishlatish taklif qildi.
Qaror: CLAUDE.md'dagi "Claude chiqishi fine-tune emas" qoidasini aniqlashtirdim (yuqorida). Gym diversity/few-shot uchun
ruxsat, LoRA/vazn o'qitish uchun yo'q (faqat DeepSeek/GLM, ochiq vazn + o'qitish ruxsati tasdiqlangan).
Bajarildi: `src/safia_sec/gym/authored/claude_variants.py` + `scripts/claude_red_batch.py` — 5 ta qo'lda yozilgan
Red variant (shop/CWE-89 .format() SQLi, shop/CWE-22 absolute-path bypass, bank/CWE-89 concat SQLi,
bank/CWE-840 abs() bilan "tuzatilgan" lekin hali zaif tekshiruv, blog/CWE-79 concat XSS), hammasi mavjud golden
shablonlardan **kod shakli bo'yicha boshqacha** (xilma-xillik muammosiga javob). Hakamda 5/5 qabul qilindi
(API chaqiruv emas, shu sessiyada to'g'ridan-to'g'ri yozildi, qo'shimcha token xarajati yo'q). 56 test yashil.
Natija: `eval/results/20261007-red-claude-claude_sonnet_5/`. `served_by.authored_by=claude-assistant` bilan
belgilangan, DeepSeek/GLM namunalaridan ajratib turiladi.
LOCAL uchun ta'sir yo'q: bu faqat gym ma'lumotini boyitadi, Blue DEV eval jarayoniga halaqit bermaydi.
