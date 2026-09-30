# Vazifalar taxtasi (v2) — Red vs Blue

> CLOUD tahrirlaydi, LOCAL o'qiydi va o'z xabarlarini `docs/handoff/local.md` ga yozadi.
> Holat: `[ ]` ochiq · `[~]` jarayonda · `[x]` tayyor. Yangilandi: 2026-10-01. Eski (v1) taxta git tarixida.

## G'oya (3 jumla)
Ikki lokal agent o'z kodimiz ustida bir-biriga qarshi o'ynaydi. **Red** toza ilovaga kichik zaiflik kiritadi va exploit-test yozadi; **hakam** (LLM emas, kod) zaiflikni faqat exploit haqiqatan ishlasa qabul qiladi; **Blue** (bizning security agent) o'zgargan ilovadan zaiflikni topadi. Blue topa olmagan holatlardan o'rganadi va natijada begona benchmark'da yaxshilanadimi, tekshiramiz.

## Oddiy ro'yxat (6 qadam)

| # | Qadam | Kim | Holat |
|---|---|---|---|
| 1 | Toza ilova + hakam + 3 CWE shablon (SQLi, IDOR, path traversal) + testlar + Bandit baseline | CLOUD | [x] |
| 2 | **Go/no-go:** lokal model Red bo'la oladimi? (`scripts/red_generate.py`) — yaroqlilik % | LOCAL | [ ] ← **hozir shu** |
| 3 | Blue v0: nomzod (Bandit) → LLM → dalil; hakam bergan ground truth bilan skorlash | CLOUD kod, LOCAL run | [ ] |
| 4 | O'rganish: Blue xato qilgan namunalar → few-shot xotira; oldin/keyin jadval (LoRA — ixtiyoriy) | CLOUD kod, LOCAL run | [ ] |
| 5 | Transfer: begona benchmark'da (RealVuln/Juice Shop qismi) oldin/keyin | LOCAL (+ CLOUD adapter) | [ ] |
| 6 | README, EXPERIMENTS (muvaffaqiyatsizlar bilan), demo, email | SIZ + CLOUD | [ ] |

**Kesish chizig'i:** LoRA → 5-qadamda ko'p model → ilova soni. Hech qachon kesilmaydi: 1–3-qadamlar va halol jadval.
**Go/no-go qoidasi (3-okt):** 3 CWE dan kamida 2 tasida ≥ 10 ta *har xil* qabul qilingan zaiflik chiqmasa, Red'ni shablon + LLM variatsiyasi bilan almashtiramiz (LLM faqat shablon ichini o'zgartiradi).

## Budjet
Cho'ntakdan maksimal ~$20 (faqat ixtiyoriy GPU ijarasi, LoRA uchun). Cloud credit alohida; Ollama va ochiq modellar bepul.

## 2-qadam: LOCAL uchun aniq ko'rsatma
```bash
git fetch origin && git merge origin/claude/wizardly-curie-34voig
python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
pytest -q                      # 14 ta test o'tishi kerak (hakam ishlayapti)
python scripts/bandit_baseline.py   # baseline: Bandit 3 dan 1 tasini topadi
ollama pull <model>            # jihozga mos 1-2 ta model
python scripts/red_generate.py --model <model> --n 10
```
Natija `eval/results/<sana>-red-<model>/` ga yoziladi (`result.json` + `summary.md`). Uni commit + push qiling va handoff'ga 3–5 qator yozing: nechta qabul qilindi, eng ko'p rad sababi, sizga nima g'alati tuyuldi.

## Hamkorlik (qisqa; to'liq: `CLAUDE.md`)
- CLOUD → `claude/wizardly-curie-34voig`, LOCAL → `local/dev`; bir-biridan `git fetch` + `git merge`.
- CLOUD: kod, test, hujjat. LOCAL: `prompts/`, `eval/results/`, `handoff/local.md`, `HARDWARE.md`.
- Hakam model yozgan kodni **ishga tushiradi**: faqat `src/safia_sec/gym/referee.py` orqali (alohida process, tarmoqsiz namespace, limitlar). Boshqa yo'l bilan ishga tushirmang. Haqiqiy izolyatsiya uchun keyinroq Docker.
- Raqamlarni to'qima: har bir metrika `result.json` dagi haqiqiy run'dan.

## Bug reports
_(hozircha yo'q)_
