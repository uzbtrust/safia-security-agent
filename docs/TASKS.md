# Vazifalar taxtasi (v2) — Red vs Blue

> CLOUD tahrirlaydi, LOCAL o'qiydi va o'z xabarlarini `docs/handoff/local.md` ga yozadi.
> Holat: `[ ]` ochiq · `[~]` jarayonda · `[x]` tayyor. Yangilandi: 2026-10-01. Eski (v1) taxta git tarixida.

## Mahsulot nima (xatdagi vazifa)
**Mahsulot — Blue:** `safia-sec scan <har qanday papka>` — lokal AI security agent. U kod bazasini ko'rib zaifliklar va xavfli qarorlarni topadi, dalil (fayl:qator) va tushuntirish beradi, tuzatish taklif qiladi. **Gym (Red + hakam) — Blue'ni o'qitish va baholash mexanizmi:** Red toza ilovaga zaiflik kiritadi va exploit yozadi; hakam (LLM emas, kod) zaiflikni faqat exploit haqiqatan ishlasa qabul qiladi; Blue shularni topishga o'rganadi. Asosiy savol: o'z-o'zi bilan o'rganish begona benchmark'da yordam beradimi?
**To'siq qoida:** README'ning birinchi jumlasi agent haqida bo'ladi, gym haqida emas. Blue yupqa qolib ketmasin.

## Qadamlar

| # | Qadam | Kim | Muddat | Holat |
|---|---|---|---|---|
| 1 | Toza ilova + hakam + 3 CWE shablon + testlar + Bandit baseline | CLOUD | tayyor | [x] |
| 2 | **Go/no-go:** lokal model Red bo'la oladimi? (`scripts/red_generate.py`) | LOCAL | 1–3-okt | [ ] ← **hozir shu** |
| 3 | **Blue v0 (mahsulot):** `scan` CLI + hisobot (qarang: «Blue tayyor sharti») | CLOUD kod, LOCAL run | 3–5-okt | [ ] |
| 4 | O'rganish: Blue xatolari → few-shot xotira; oldin/keyin jadval (LoRA ixtiyoriy; 8-okt qaror) | CLOUD kod, LOCAL run | 6–8-okt | [ ] |
| 5 | Transfer: begona lokal zaif ilova/benchmark'da (RealVuln yoki Juice Shop qismi) oldin/keyin; kodni muzlatish 11-okt kechqurun | LOCAL (+ CLOUD adapter) | 9–11-okt | [ ] |
| 6 | Yakuniy baholash: muzlatilgan kod, test to'plamida **bir marta** | LOCAL | 12-okt | [ ] |
| 7 | README (agent birinchi), EXPERIMENTS (muvaffaqiyatsizlar bilan), demo, email | SIZ + CLOUD | 13–14-okt | [ ] |

Muddat 15-okt, topshirish maqsadi 14-okt.

### Blue tayyor sharti (3-qadam, majburiy)
1. `safia-sec scan <papka>` istalgan Python papkada ishlaydi (o'zimiz yaratmagan kodda ham).
2. Har bir topilma: fayl:qator, zaiflik turi (CWE), **dalil** (kod iqtibosi, hakam/fayl bilan tekshiriladi), tushuntirish, tuzatish taklifi. Dalilsiz topilma hisobotga chiqmaydi.
3. Klassik zaifliklarga qo'shimcha «xavfli qarorlar» ham ko'rinadi (hardcoded secret, zaif hash, debug yoqilgan va h.k.).
4. Hisobot JSON + Markdown (SARIF — vaqt qolsa).
5. Ruxsat: faqat o'qiydi; faylga yozmaydi, tarmoqqa chiqmaydi, shell yo'q.
6. Skorlash: hakam bergan ground truth bilan (precision/recall) va Bandit baseline bilan taqqoslash.

**Kesish chizig'i:** LoRA → Red'ning o'rganishi (Blue'ga qarshi) → ko'p model → ilovalar soni. **Hech qachon kesilmaydi:** 1–3-qadamlar, transfer testi, halol jadval.
**Go/no-go qoidasi (3-okt):** 3 CWE dan kamida 2 tasida ≥ 10 ta *har xil* qabul qilingan zaiflik chiqmasa, Red'ni shablon + LLM variatsiyasi bilan almashtiramiz (LLM faqat shablon ichini o'zgartiradi).
**Tamoyillar:** (a) hakam faqat «zaiflik ishlaydi» ni isbotlaydi, realistiklikni emas — shuning uchun transfer testi; (b) «buzolmadi» ≠ «xavfsiz»: faqat qabul qilinganlar ishonchli musbat; (c) agentlar data orqali o'rganadi, bir-biriga gapirmaydi; (d) dev'da sozlaymiz, test'da bir marta o'lchaymiz.

## Red manbalari va ish oqimi (2026-10-01 qarori)
- **Red = bir nechta model, hammasi bir xil promptda:** (1) lokal `qwen2.5-coder:7b` (go/no-go o'lchovi), (2) API: **DeepSeek V4.1 Flash** (ToS'da output'dan model o'qitish ruxsat etilgan, birlamchi manba o'qilgan), (3) API: **GLM 5.3 Flash** (coding bahosi yuqori, lekin o'qitish ruxsati noma'lum). Har bir namuna `result.json` da manba modeli bilan belgilanadi.
- **O'qitish ruxsati qoidasi:** GLM namunalari Blue'ni *o'qitish* uchun faqat Z.AI shartlari ruxsat bergani tasdiqlansa ishlatiladi; aks holda faqat baholash/taqqoslash uchun. DeepSeek namunalari ishlatiladi. README'da manba modellar ochiq yoziladi.
- **Tanlov mezoni — AA bahosi emas, hakam:** bir xil promptda qaysi model ko'proq *har xil qabul qilingan* zaiflik beradi. AA coding index DeepSeek uchun yo'q (null) — bu yomonlik belgisi emas.
- **Ish oqimi (macOS'da hakam ishlamaydi, u model kodini izolyatsiyasiz bajarmaydi):**
  1. LOCAL: `python scripts/red_generate.py --provider openai|ollama --model <m> --n 10 --no-judge` → `eval/results/<run>/result.json` (namunalar xom, bajarilmagan). Push.
  2. CLOUD (Linux, `unshare -rn`): `python scripts/judge_samples.py eval/results/<run>/` → `eval/judged/<run>/` (qabul soni, rad sabablari).
  3. Qaror cloud'da hakam natijasi bilan chiqadi.
- **OpenRouter (2026-10-01):** DeepSeek va GLM OpenRouter orqali (`--provider openrouter`, `OPENROUTER_API_KEY`); upstream provayder `served_by` da yoziladi. O'qitish ruxsati upstream shartlariga bog'liq (OpenRouter shartni o'zgartirmaydi). Uchinchi manba: **JEV** (`JEV_TOKEN`; base URL va model ID aniqlanishi kerak).
- **Kalit xavfsizligi:** `RED_API_BASE/KEY/MODEL` faqat muhit o'zgaruvchisida; kalit hech qachon repo'ga, logga yoki chatga tushmaydi. API'ga faqat `gym_apps/shop` kodi yuboriladi.

## Budjet
Cho'ntakdan maksimal ~$20 (faqat ixtiyoriy GPU ijarasi, LoRA uchun). Cloud credit alohida; Ollama va ochiq modellar bepul.

## Jihoz (foydalanuvchi mashinasi, 2026-10-01)
RAM 16 GB, disk 256 GB, bo'sh joy ~52 GB, GPU: noma'lum (LOCAL chat `docs/HARDWARE.md` ga aniq yozadi). Qarorlar:
- Asosiy model: **7–8B (Q4)**, ~5 GB. Birinchi: `qwen2.5-coder:7b`. 13B+ ishlatilmaydi (16 GB RAM'da sekin).
- Taqqoslash uchun 1–2 ta qo'shimcha model (har biri ≤ ~6 GB) va bitta kichik (1–3B) — E1 bake-off uchun. Jami modellar ≤ ~20 GB.
- Disk byudjeti: modellar ≤ 20 GB, Docker (Docker Desktop bo'lsa 10–20 GB — keyinroq, 3.2 qadamda), repo/venv < 1 GB. Bo'sh joy 15 GB dan tushsa, ishni to'xtatib xabar bering.
- Tashqi SSD shart emas. Ishlayotganda og'ir dasturlarni (brauzer) yoping.

## 2-qadam: LOCAL uchun aniq ko'rsatma
```bash
git fetch origin && git merge origin/claude/wizardly-curie-34voig
python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
pytest -q                      # 14 ta test o'tishi kerak (hakam ishlayapti)
python scripts/bandit_baseline.py   # baseline: Bandit 3 dan 1 tasini topadi
ollama pull qwen2.5-coder:7b   # birinchi model (~5 GB); nom topilmasa, `ollama search`/kutubxonadan o'xshash 7-8B coder model
python scripts/red_generate.py --model qwen2.5-coder:7b --n 10 --no-judge   # macOS: hakam yo'q, cloud baholaydi
```
Natija `eval/results/<sana>-red-<model>/` ga yoziladi (`result.json` + `summary.md`). Uni commit + push qiling va handoff'ga 3–5 qator yozing: nechta qabul qilindi, eng ko'p rad sababi, sizga nima g'alati tuyuldi.

## Hamkorlik (qisqa; to'liq: `CLAUDE.md`)
- CLOUD → `claude/wizardly-curie-34voig`, LOCAL → `local/dev`; bir-biridan `git fetch` + `git merge`.
- CLOUD: kod, test, hujjat. LOCAL: `prompts/`, `eval/results/`, `handoff/local.md`, `HARDWARE.md`.
- Hakam model yozgan kodni **ishga tushiradi**: faqat `src/safia_sec/gym/referee.py` orqali (alohida process, tarmoqsiz namespace, limitlar). Boshqa yo'l bilan ishga tushirmang. Haqiqiy izolyatsiya uchun keyinroq Docker.
- Raqamlarni to'qima: har bir metrika `result.json` dagi haqiqiy run'dan.

## Bug reports
_(hozircha yo'q)_
