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

## 2026-10-07 — CLOUD (DEV eval tahlili; qadam 3 yopildi, qadam 4 boshlandi)
Bajarildi: `origin/local/dev` merge qilindi (`ad79f87`). DEV gym natijalari (`eval/results/20261007-blue-gym-{gemma4_12b,qwen3.5_9b}/`)
o'qildi va `docs/EXPERIMENTS.md`ga qo'shildi: dev gym son + H1-H4 har biri haqiqiy natija bilan tekshirildi (hech biri
to'qilmadi, har bir raqam `result.json`/`summary.md`dan). `docs/TASKS.md` 3-qadam [x], 4-qadam [~] ga o'tkazildi.
Asosiy topilma: gemma4:12b function recall 18/21, qwen3.5:9b 1/21 — farq sabab **verifier**: Qwen o'zini-o'ziga
zarar qilib 9/10 haqiqiy topilmani noto'g'ri sabab bilan rad etdi (H3dagi "self-verification bias" xavfi Qwen'da
real ro'y berdi, Gemma'da yo'q). H2 ham modelga bog'liq chiqdi: Gemma'da grounding soxta signalni kamaytirdi,
recall'ga tegmadi (H2 tasdiqlandi); Qwen'da grounding 2 ta haqiqiy topilmani yo'qotdi (H2 rad etildi). Yagona
umumiy bo'shliq: **bank/CWE-840** (manfiy o'tkazma summasi) — ikkala modelda 0/3, garchi prompt buni nomlasa ham.
LOCAL uchun ta'sir yo'q (faqat tahlil, promptlarga tegilmadi). Qadam 4 (few-shot xotira) endi shu bo'shliqni
nishonga oladi: bank/CWE-840 va shunga o'xshash "removed/weakened business-logic check" holatlari uchun misol.
Ochiq savol (LOCAL uchun, shart emas): `qwen3.5:9b` endi diskdan o'chirilsin (model tanlovi yakunlandi, `ollama rm`).

## 2026-10-07 — CLOUD → LOCAL (4-qadam: few-shot misollar qo'shildi, oldin/keyin run kerak)
Bajarildi: `src/safia_sec/blue/fewshot.py` — detect prompt'ga 3 ta qo'lda yozilgan, **gym ilovalaridan nusxa
olinmagan** (original) zaiflik-pattern misoli qo'shildi: (1) bank/CWE-840 bo'shlig'iga mo'ljallangan "abs() bilan
tuzatilgan lekin hali zaif" misoli, (2) removed ownership check (IDOR), (3) boshqa shakldagi SQLi (bir CWE'ga
emas, patternga o'rgatish uchun). `[cross]` `src/safia_sec/prompts/detect.md`ga bitta `{examples}` joy
belgisi qo'shdim (1 qator, `{notes}Reply` → `{notes}{examples}Reply`); boshqa matn tegilmagan.
Yoqish/o'chirish: CLI'da `--no-examples` (yangi flag, `scan` va `eval-gym`da ham bor). **Muhim:** `--no-examples`
bergan holat eski (2026-10-07'dan oldingi) prompt matnini aynan takrorlaydi, shuning uchun u `.cache/llm`dagi
eski yozuvlardan **bepul** o'qiydi — faqat misollar YOQILGAN tomoni yangi model chaqiruvi talab qiladi.
59 test yashil (3 yangi: misollar prompt'da bor/yo'q, CLI flag). Promptning o'zi (`detect.md` matni) o'zgartirilmadi,
faqat bo'sh joy belgisi qo'shildi — `{examples}` bo'sh bo'lsa chiqish aynan avvalgidek.
LOCAL nima qilsin (gemma4:12b bilan, xuddi 2026-10-07 dev gym kabi sozlamalar, shop+bank, seed 1 2 3):
1. `git fetch origin && git merge origin/claude/wizardly-curie-34voig`; `pip install -e ".[dev]"`; `pytest -q`
   (59 o'tishi kerak, Mac'da netns yo'qligi sababli balki 58 + 1 skip).
2. Baseline (deyarli bepul, keshdan): `safia-sec eval-gym --model gemma4:12b --apps shop bank --seeds 1 2 3 --no-examples --out eval/results/20261007-blue-gym-gemma4_12b-noex`
3. Misollar bilan (yangi chaqiruvlar kerak): `safia-sec eval-gym --model gemma4:12b --apps shop bank --seeds 1 2 3 --out eval/results/20261007-blue-gym-gemma4_12b-fewshot`
4. Ikkalasini solishtiring: ayniqsa bank/CWE-840 qatori (18/21 → nechaga o'zgardi) va toza ilovadagi soxta signal
   (misol bir CWE'ni haddan tashqari ko'p chaqirtirib yubormasligini tekshiring). Push qiling, handoff'ga 3-5 qator
   raqam bilan yozing (to'qimasdan, result.json'dan).
Ochiq savol yo'q; promptga tegmadim, faqat bo'sh joy qo'shdim — agar `detect.md` matnini keyin siz o'zgartirsangiz,
`{examples}` qatorini saqlang (aks holda misollar jim tushib qoladi, xato chiqmaydi).

## 2026-10-07 — CLOUD → LOCAL (4-qadam 1-raund + RealVuln; YUQORIDAGI yozuv o'rniga shu bajariladi)
Foydalanuvchi bilan kelishuv: few-shot ko'pi bilan 2 raund, faqat dev dalili bilan; keyin muzlatish; yakuniy test bir marta;
LoRA qarori eng oxirida. Protokol run'dan OLDIN `docs/EXPERIMENTS.md` ("Step 4 protocol", "RealVuln") ga yozildi.
Bajarildi (`[cross]`, foydalanuvchi so'rovi bilan): `prompts/detect.md` qayta yozildi (CWE ro'yxati — gemma bank/CWE-840 ni
to'g'ri funksiyada topgan, lekin CWE-606/603 deb belgilagan edi; "himoyalangan kod topilma emas" qoidasi; qaysi qatorni
ko'rsatish), `verify.md`ga `{examples}`. `blue/fewshot.py` — 4 ta "zaif / himoyalangan" juftlik (gym yoki benchmark kodi emas).
Test fayllari va migrations sukut bo'yicha o'tkaziladi (`--include-tests`). Topilma limiti 12, javob limiti 2048 token.
RealVuln: `targets/realvuln/split.json` (sha256 juft/toq → dev/test, keyin LOC byudjeti; dev = 6 repo, 91 zaiflik + 16 tuzoq),
`scripts/realvuln_fetch.py`, `safia-sec eval-realvuln`. Skorlash RealVuln matcher qoidalari bilan (fayl + CWE + qator ±10,
mos kelmagan topilma = FP), asosiy metrika F3. Adapter tekshiruvi: dev ground truth'ni topilma sifatida bersak TP 91/91, FP 0.
74 test yashil. Promptlar o'zgargani uchun eski kesh ishlamaydi (kutilgan).
LOCAL nima qilsin (gemma4:12b; ilovalarni yoping; uzun run'lar uchun `caffeinate -i` Mac uxlab qolmasligi uchun):
1. `git fetch origin && git merge origin/claude/wizardly-curie-34voig`; `pip install -e ".[dev]"`; `pytest -q` (74 o'tishi kerak;
   macOS'da netns yo'qligi sababli 1 ta skip bo'lishi mumkin).
2. `python scripts/realvuln_fetch.py --split dev` (≈10 s, ≈14 MB; faqat o'qish, kod ishga tushirilmaydi).
3. Gym dev: `caffeinate -i safia-sec eval-gym --model gemma4:12b --apps shop bank --seeds 1 2 3` (taxmin 35–45 daq, o'lchanmagan).
4. RealVuln dev: `caffeinate -i safia-sec eval-realvuln --model gemma4:12b --split dev` (taxmin 1–2 soat, o'lchanmagan: 37 chunk,
   har biriga 1 detect + bir nechta verify chaqiruvi).
5. Vaqt bo'lsa (tavsiya, majburiy emas): xuddi shu 4-buyruq `--no-examples` bilan (few-shot gym tashqarisida yordam beradimi?).
   Gym `--no-examples` ixtiyoriy.
6. Natijalarni push qiling; handoff'ga har run uchun 3–5 qator (raqamlar faqat result.json/summary.md dan, to'qimasdan):
   gym (function recall, located, clean false signal), RealVuln (TP/FP/FN, precision, recall, F3, stratum bo'yicha, xatolar soni).
TAQIQ: `blog` (gym test) va RealVuln `--split test` ishga tushirilmaydi — ular muzlatishdan keyin bir marta.

## 2026-10-08 — CLOUD → LOCAL (4-qadam 2-raund; muzlatish va yakuniy test tartibi)
Merge: `local/dev` (06103d0). 1-raund tahlili va 2-raund `docs/EXPERIMENTS.md`da (run'dan OLDIN yozildi).
Asosiy topilma: RealVuln dev'dagi 51 FN'dan 32 tasida model 10 qator ichida BOSHQA zaiflikni aytgan — har handler'dan
bitta (odatda injection) aytib, yonidagi "yo'q narsa"larni (rate limit, cookie flaglari, xato tafsilotlari) o'tkazgan.
2-raund (`e0c88de`, bitta commit, `[cross]`): har funksiyadagi HAR BIR zaiflik; har handler nimasi yo'qligini tekshirish;
"yo'q nazorat" def/route qatoriga; CWE aniqlashtirishlar; 5-few-shot misol (bitta handler, 3 topilma). Skaner tuzatishlari:
dedupe ikki xil secret'ni birlashtirib yuborardi, Django `tests.py` skan qilinardi, JSON'dan keyingi matn xato berardi,
topilma limiti 12 to'lgan edi (endi 16, javob 2560 token). Gym eslatmasiga: "X-User o'qimaydigan route'lar ochiq".
77 test yashil. Promptlar o'zgargan, kesh ishlamaydi.

### A sessiya — 2-raundni dev'da o'lchash va muzlatish (taxmin 75–90 daq; 1-raund 73 daq edi)
1. `git fetch origin && git merge origin/claude/wizardly-curie-34voig`; `pip install -e ".[dev]"`; `pytest -q` (77; macOS'da 76 + 1 skip).
2. `caffeinate -i safia-sec eval-realvuln --model gemma4:12b --split dev --out eval/results/20261008-realvuln-dev-gemma4_12b-r2`
3. Qoida (mexanik, oldindan yozilgan). 1-raund final F3 = **0.459** (TP 40, FP 12, FN 51 dan hisoblangan).
   r2 final F3 (`result.json` dagi TP/FP/FN dan, 3 xona aniqlikda) **> 0.459** → 2-raund muzlaydi.
   **< 0.459** → `git revert --no-edit e0c88de` (1-raund qaytadi). **Aynan teng** → to'xtang, menga yozing (gym-dev bilan hal qilinadi).
4. `git tag step4-freeze && git push origin local/dev step4-freeze`. Handoff'ga: r2 TP/FP/FN, P, R, F3 (stratum bo'yicha),
   qaysi raund muzladi. Muzlatilgandan keyin `src/` va `prompts/` ga hech kim tegmaydi.

### B sessiya — yakuniy test, BIR MARTA (taxmin 2–2.5 soat; muzlatilgan commit'da)
5. `python scripts/realvuln_fetch.py --split test --final`
6. Gym test (blog), ikki qo'l: `caffeinate -i safia-sec eval-gym --model gemma4:12b --apps blog --seeds 1 2 3 --out eval/results/<sana>-final-gym-blog-gemma4_12b`
   va xuddi shu `--no-examples --out eval/results/<sana>-final-gym-blog-gemma4_12b-noex` (har biri ~17 daq).
7. RealVuln test, ikki qo'l: `caffeinate -i safia-sec eval-realvuln --model gemma4:12b --split test --final --out eval/results/<sana>-final-realvuln-test-gemma4_12b`
   va xuddi shu `--no-examples --out ...-noex` (har biri taxmin 50–65 daq).
8. Hech narsani qayta ishga tushirmang va hech narsani sozlamang (natija yomon bo'lsa ham — bu halol natija). Push + handoff.
Keyin men README / LIMITATIONS / EXPERIMENTS yakuniy matnini faqat shu fayllardagi raqamlar bilan yozaman.

## 2026-10-08 — CLOUD → LOCAL (A+B BITTA SESSIYADA, Vast.ai GPU'da; yuqoridagi A/B o'rniga SHU bajariladi)
Sabab: Mac boshqa ish uchun band. Protokol o'zgarishi run'dan OLDIN `EXPERIMENTS.md` ("Hardware change") ga yozildi:
r1 ham GPU'da qayta ishlatiladi, qoida r1 va r2 ni BIR mashinada solishtiradi (`scripts/freeze_decide.py`).
Hamma ish bitta skriptda: `scripts/vast_final.sh` (o'rnatish → pytest → Ollama (har GPU'ga alohida server, faqat 127.0.0.1)
→ model digest tekshiruvi → A: r1 va r2 RealVuln dev, parallel → qoida → B: faqat g'olib daraxtda blog + RealVuln test,
misollar bilan GPU0'da, `--no-examples` GPU1'da → `vast_results.tgz`, oxirgi qator `ALL DONE`). 1 GPU bo'lsa ketma-ket ishlaydi.
Cloud'da sinalgan: sintaksis, ikki daraxt (r1 = e0c88de qaytarilgan: 4 misol, limit 12; r2: 5 misol, limit 16, har daraxt o'z
kodini yuklaydi), qoida Mac r1 natijasini 0.459 deb qayta hisoblaydi. GPU qismi (Ollama/CUDA) sinalmagan — needs-local-verify.
1. Merge: `git fetch origin && git merge origin/claude/wizardly-curie-34voig`; Mac'da `pytest -q` (78; 77 + 1 skip).
2. Vast (kalit `$VAST_TOKEN` muhitdan; hech qachon chop etmang): `vastai` CLI (yo'q bo'lsa `pip install vastai`), `vastai set api-key`.
   Taklif: **bitta mashinada 2× RTX 4090** (yoki 2× RTX 3090), on-demand (interruptible EMAS), reliability ≥ 0.98,
   disk ≥ 60 GB, internet ≥ 500 Mbps, CUDA ≥ 12.2, jami ≤ ~$1/soat, eng arzonidan. Topilmasa: bitta 24 GB karta
   (4090/3090/A5000) ≤ ~$0.5/soat. Image: CUDA 12 + Python ≥ 3.10 (masalan rasmiy `pytorch/pytorch` CUDA 12 runtime), SSH.
3. Kodni yuborish (token instance'ga YUBORILMAYDI): `.git` bilan, `.venv`, `.cache`, `__pycache__` siz:
   `rsync -az --exclude .venv --exclude .cache --exclude __pycache__ -e "ssh -p <PORT>" ./ root@<HOST>:/workspace/safia/`
4. Ishga tushirish: `ssh ... 'cd /workspace/safia && nohup bash scripts/vast_final.sh > vast_run.log 2>&1 &'`;
   har ~5 daqiqada `tail -5 vast_run.log`. Taxmin (o'lchanmagan): o'rnatish + model ~10 daq, A+B 2×GPU'da ~20–30 daq.
5. Xato bo'lsa: sababi infratuzilma bo'lsa tuzatib skriptni qayta ishga tushiring (kesh tufayli tugagan chaqiruvlar bepul va
   aynan bir xil takrorlanadi). `exit 3` (aynan teng) → B qilinmaydi, to'xtang. Hech qanday sozlama/promptni o'zgartirmang.
6. `ALL DONE` dan keyin: `scp` bilan `vast_results.tgz`, `vast_run.log`, `ollama_gpu*.log` ni oling; repo ichida
   `tar xzf vast_results.tgz`; `vast_run.log` ni `eval/results/<sana>-step4-freeze-gpu/` ga qo'ying.
7. **Instance'ni O'CHIRING** (`vastai destroy instance <ID>`, `vastai show instances` bo'sh ekanini tekshiring) — har qanday
   holatda, xato bo'lsa ham. Byudjet: hisobda $3.13 bor; **qat'iy chegara — jami sarf $3.15** (GPU + disk + trafik).
   Asosiy maqsad ishni oxirigacha yetkazish: shuning uchun ijaradan oldin narxni hisoblang (soatlik narx × ~1 soat
   ≤ ~$1.5 bo'lsin, zaxira qolsin), ishlayotganda har ~10 daqiqada balansni tekshiring (`vastai show user`).
   Sarf $3.15 ga yetsa — natijalar qanday bo'lsa ham to'xtating, borini oling va instance'ni o'chiring.
8. Muzlatish (Mac'da): `eval/results/<sana>-step4-freeze-gpu/decision.json` dagi `winner`: `r1` bo'lsa
   `git revert --no-edit e0c88de`; `r2` bo'lsa hech narsa. So'ng `git tag step4-freeze`, natijalarni commit qiling,
   `git push origin local/dev step4-freeze`.
9. Handoff: GPU nomi va soni, digest mos keldimi, vaqt va narx, r1/r2 GPU F3 (+ Mac r1 0.459 bilan farq), g'olib;
   B: blog (function recall, located, toza ilovada soxta signal) va RealVuln test (TP/FP/FN, P, R, F3, stratum bo'yicha)
   — ikki qo'l (misollar bilan / `--no-examples`); xatolar soni. Raqamlar faqat result.json/summary.md dan.
