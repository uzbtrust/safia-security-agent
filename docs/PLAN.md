# Safia AI — ML Engineer case study: «Build a local AI security agent»

> Jonli reja hujjati — ichki ish hujjati, o'zbekcha. Topshiriladigan hujjatlar (README, DECISIONS, EXPERIMENTS va h.k.) inglizcha bo'ladi.

| | |
|---|---|
| Holat | Reja bosqichi — kod hali yozilmagan |
| Boshlandi | 2026-10-01 (Toshkent vaqti) |
| Muddat | xat sanasidan +2 hafta ≈ **2026-10-15**. Xat 1-oktabrda kelgan deb hisobladim — Gmail'da sanani tekshiring |
| Topshirish maqsadi | **2026-10-14** (1 kun zaxira; aniq soat aytilmagan) |
| Repo / branch | `uzbtrust/safia-security-agent` · `claude/wizardly-curie-34voig` |

---

## 1. Qisqacha

**Nima quramiz.** `safia-sec scan <repo>` — kod bazasini xavfsizlik nuqtai nazaridan tahlil qilib, zaifliklar va xavfli qarorlarni topadigan hamda ularni *dalil bilan* tushuntiradigan **lokal** AI agent.

**Asosiy g'oya (thesis).** Kichik lokal LLM zaiflikni *topuvchi* sifatida ishonchsiz — ko'p soxta signal (FP) beradi. Lekin u *tergovchi* sifatida foydali bo'la oladi:

1. Deterministik vositalar (Semgrep, Bandit, sir-qidiruv) **nomzod** topadi; LLM esa SAST ko'rmaydigan mantiqiy zaifliklarni (authz, biznes-logika) taklif qiladi.
2. Agent kodni tool'lar bilan o'qib **dalil** yig'adi (fayl:qator, iqtibos, source→sink yo'li) va o'z xulosasini **rad etishga** urinadi.
3. Dalil LLM'dan *mustaqil* tekshiriladi: iqtibos haqiqatan fayldami; imkon bo'lsa — lokal sandbox'da zararsiz PoC + canary.
4. Natija: SARIF/Markdown hisobot; har bir finding'da "nega ishonish mumkin va nima uni rad etadi".

Bu gipotezani **o'lchaymiz** va qayerda ishlamasligini ham yozamiz.

**Ustuvorlik:** (1) baholash intizomi → (2) dalil bilan tasdiqlash → (3) halol tajribalar, muvaffaqiyatsizlari ham → (4) toza muhandislik. UI va polish — eng oxirida, minimal.

**Nima qilmaymiz:** begona tizimlarni skan/hujum; mahsulot ichida cloud LLM; "0-day topdik" kabi da'volar; hamma tillarni qo'llash; chiroyli UI.

---

## 2. Ular nimani baholaydi (xatdan o'qilgan)

- Ochiq qoldirilgan savollar — *bizning qarorlarimiz*: agent nima, qanday o'rganadi, nimaga ruxsat etiladi, topilmani qanday tasdiqlaydi, natijani qanday tushuntiradi. Shu qarorlar — case study'ning o'zi.
- So'zma-so'z aytilgan: *qiziqarli g'oya, kuchli texnik qaror, muvaffaqiyatsiz tajribadan olingan saboq, o'ylangan trade-off* — "keraksiz polish"dan afzal. "Yashirin checklist yo'q", "so'ralmagan ko'nikmalaringizni ham ko'rsating".
- Chegaralar: faqat o'zimizniki yoki ruxsat berilgan tizimlar; ataylab zaif lokal lablar mumkin; begona tizimni skan/hujum — **mumkin emas**.
- Topshirish: repo + qarorlar haqida qisqa tushuntirish; demo, baholash, tajriba eslatmalari — qadrlanadi.
- Xat `bcc` bilan kelgan → ehtimol ko'p nomzodga ketgan. Ko'pchilik "RAG + LLM fayl o'qiydi" demo topshiradi. Ajralib turish yo'li: **baholash intizomi, dalil bilan tasdiqlash, halollik**.
- Vakansiya ML Engineer (lokal LLM, GPU server, Docker, Linux, Git), shuning uchun **ML-injenerlik** jihatlari — baholash, serving/kvantlash, reproducibility — ko'rinib turishi kerak.

---

## 3. Halol baho — xavflar va tuzoqlar

1. **Qiyin joy model emas, precision.** Fine-tune qilingan 7B model BigVul'da F1 ≈ 68%, realistik PrimeVul'da esa ≈ 3% olgan ([PrimeVul](https://arxiv.org/pdf/2403.18624)). Demak "zaiflik datasetida fine-tune qilamiz" — eng xavfli yo'l. Uni faqat *triage* uchun, vaqt chegarasi bilan, oxirida sinaymiz.
2. **Agent — sehr emas.** "[Sifting the Noise](https://arxiv.org/abs/2601.22952)" (2026): agent'lar SAST shovqinini keskin kamaytiradi, lekin foyda *kuchli* modellarga (Claude Sonnet 4, GPT-5 darajasi) bog'liq; kuchsizlarida cheklangan va beqaror; agressiv filtr haqiqiy zaifliklarni ham o'chirib yuboradi. Bizning lokal modellarimiz kuchsiz tomonda. Shuning uchun model-mustaqil tekshiruvlarga (iqtibos tekshiruvi, PoC) tayanamiz va LLM-verifikatsiya foydasini *o'lchaymiz*, taxmin qilmaymiz.
3. **Kontaminatsiya.** Juice Shop, DVWA kabi mashhur zaif ilovalar LLM'lar o'qigan ma'lumotda bor — natija yuqori chiqadi. Choralar: yangi o'z ilovamiz (CakeShop), yopiq test to'plami, izoh/ismlarni tozalash, memorization probe (E5).
4. **O'zimiz yozgan ilovani o'zimiz baholasak — noxolis.** Sintetik zaifliklar haqiqiyidan "toza" va oson. Shuning uchun dev/test ajratamiz, tashqi benchmark (RealVuln) qo'shamiz va bu cheklovni README'da yozamiz.
5. **Ground truth to'liq emas.** Ochiq ilovalarda ro'yxatga kirmagan haqiqiy zaifliklar ham bor — "FP"larning bir qismi aslida TP. ~30 ta FP'ni qo'lda ko'rib chiqamiz (adjudikatsiya).
6. **Vaqt.** 2 hafta — MVP + baholash + 1–2 tajriba uchun yetadi, "mahsulot" uchun emas. Eng katta xavf — scope creep (framework almashtirish, UI, ko'p til). Kesish chizig'i 7-bo'limda.
7. **Muhit.** Bu cloud sessiyada HuggingFace/Ollama/arXiv bloklangan, GPU yo'q, Docker daemon ishlamaydi. Modelli run'lar va Docker lablari — sizning kompyuteringizda. Kod, testlar (mock LLM), hujjatlar — bu yerda.
8. **AI yordami.** Men kod yozishda yordam beraman, lekin siz har bir qarorni tushunib, o'z so'zingiz bilan himoya qila olishingiz kerak (ehtimol suhbatda so'rashadi). README'da AI yordamini ochiq yozamiz. Hujjatdagi **har bir raqam haqiqiy run'dan** olinadi — hech qachon to'qilmaydi.

---

## 4. Dizayn

### 4.1 "Agent" nima?

Agent = LLM + tool'lar + maqsad + to'xtash sharti + ruxsat siyosati. Framework ishlatmaymiz — kichik, o'zimiz yozgan sikl: model har qadamda JSON-schema bilan **cheklangan** action qaytaradi (`read_file`, `grep`, `find_refs`, …, `final`). Sabab: kichik modellarda native function-calling ishonchsiz; o'z sikl log, replay, byudjet va tushuntirish uchun qulay. (Shu yondashuvga yaqin misol: [Vulnhuntr](https://www.darkreading.com/application-security/open-source-llm-tool-finds-python-zero-days) — LLM zanjir bo'ylab qo'shimcha kontekst so'raydi.)

### 4.2 Pipeline

```
 repo ─► [1 Index] ─► [2 Nomzodlar] ─► [3 Analyst] ─► [4 Verifier] ─► [5 Report]
         tree-sitter    Semgrep/Bandit    gipoteza       tool'lar + refuter   JSON → SARIF
         symbols,       sir-qidiruv       (CWE, source   iqtibos tekshiruvi   Markdown/HTML
         route'lar      + LLM "scout"     →sink da'vosi) (+ sandbox PoC)
                                               ▲                 │
                                 [Bilim: playbook + CWE/OWASP]   └─► [Xotira: TP/FP feedback]
```

1. **Index** — tree-sitter (Python, JS/TS): funksiyalar, chaqiruvlar (taxminiy call graph), route'lar (Flask/FastAPI/Express), konfiguratsiya fayllari (Dockerfile, CI, .env).
2. **Nomzodlar** — Semgrep/Bandit, sir-qidiruv; LLM-Scout: har bir entry point uchun "nima noto'g'ri ketishi mumkin?" (authz, biznes-logika — SAST ko'rmaydigan joylar).
3. **Analyst** — nomzod + kod konteksti + playbook/RAG → tuzilgan gipoteza (`cwe`, `claim`, `source`, `sink`, iqtibos).
4. **Verifier** — tool'lar bilan dalil yig'adi; **refuter** "nega bu zaif emas" (guard, sanitizer, auth) deb bahslashadi; yakuniy qaror. Byudjet: ≤ 8 qadam/finding.
5. **Reporter** — JSON → SARIF 2.1.0 + Markdown (+ bitta fayl HTML, escape qilingan).

### 4.3 Tasdiqlash narvoni (agent topilmani qanday tekshiradi)

| Daraja | Nimani tekshiradi | Kim tekshiradi | Narx |
|---|---|---|---|
| **L0** | Iqtibos/fayl/qator haqiqatan mavjudmi (gallyutsinatsiyaga qarshi) | kod (LLM emas) | ~0 |
| **L1** | Mustaqil vosita (Semgrep/Bandit) ham shu joyni belgilaganmi | vosita | past |
| **L2** | source→sink yo'li har bir hop uchun fayl:qator bilan; himoya (sanitizer/auth) yo'qligi; refuter bahsi | LLM + tool'lar | o'rta |
| **L3** | Lokal sandbox'da deklarativ probe + canary oracle | kod (LLM emas) | yuqori; faqat web lablarda |

Yakuniy yorliq: `confirmed-dynamic` > `confirmed-static` > `likely` > `needs-review` > `rejected`.

Muhim: L0 va L3 **model-mustaqil** — kichik model o'z xatosini "tasdiqlab yuborishi" (self-verification bias) xavfidan himoya qiladi. Shu g'oya katta tizimlarda ham bor: DARPA AIxCC finalistlari har bir topilmani PoV (proof of vulnerability) bilan isbotlaydi ([Buttercup](https://trailofbits.com/buttercup/)). Self-consistency (k=3) faqat chegaraviy holatlarda.

### 4.4 Ruxsatlar — agent nima qila oladi

- **Default — faqat o'qish.** Target read-only; `read_file` path-jail (`realpath`; tashqariga chiqaruvchi symlink rad etiladi). Umumiy **shell tool yo'q** (ataylab: kamroq qobiliyat, ko'proq xavfsizlik).
- **Byudjet:** qadam/finding, token va vaqt limiti; limitga yetsa — `needs-review`.
- **Dinamik tekshiruv** faqat `--allow-dynamic` bilan va faqat allowlist host'ga (127.0.0.1 / compose tarmog'i): DNS va redirect tekshiruvi, so'rovlar limiti, zararsiz payload (canary o'qish; hech narsani o'chirmaydi/buzmaydi). Probe — *deklarativ* (HTTP so'rov + oracle), LLM yozgan ixtiyoriy kod emas.
- **Audit:** har bir tool chaqiruvi `audit.jsonl` ga.
- **Repo matni — ma'lumot, ko'rsatma emas.** Koddagi "ignore previous instructions…" kabi izohlar agentni boshqara olmasligi kerak (E6 testi).
- **Patch** taklif qilsa — faqat `out/` ga diff yozadi; targetga tegmaydi.
- Hisobotda kod iqtiboslari **escape** qilinadi (xavfsizlik agentining hisobotida XSS bo'lmasligi kerak).

### 4.5 Bilim va "o'rganish"

1. **Playbook'lar** — qo'lda yozilgan, framework'ga xos checklist (Flask/FastAPI/Express: source, sink, sanitizer, tipik xatolar). Kichik modellarga eng ko'p foyda kutiladi (H4).
2. **RAG** — CWE, OWASP Cheat Sheets/ASVS/WSTG, CAPEC; lokal embedding. `make kb` yuklab oladi (repo'ga ko'chirmaymiz).
3. **Xotira** — foydalanuvchi "bu FP" desa saqlanadi; keyingi skanlarda o'xshash holatlar few-shot sifatida qo'shiladi (yaqin g'oya: [Memoir](https://arxiv.org/pdf/2608.09181) — o'qimadim).
4. **Fine-tune (Tier 3)** — detection emas, **triage** (SAST alert: TP/FP). Juftlik ma'lumot: zaif versiya = TP, to'g'rilangan versiya = "qattiq negativ" (PrimeVul saboqi). Split: loyiha va vaqt bo'yicha. Kutilma: kichik foyda yoki foyda yo'q — baribir yoziladi.

### 4.6 Tushuntirish — finding shakli

```json
{
  "id": "F-007", "title": "IDOR: istalgan user istalgan buyurtmani o'qiy oladi",
  "cwe": "CWE-639", "severity": "high", "verification": "confirmed-dynamic",
  "location": {"file": "app/orders.py", "lines": [41, 48]},
  "trace": [
    {"role": "source", "at": "app/orders.py:41", "quote": "order_id = request.args['id']"},
    {"role": "sink",   "at": "app/orders.py:44", "quote": "Order.query.get(order_id)"}
  ],
  "missing_guard": "egalik tekshiruvi yo'q (order.user_id == current_user.id)",
  "evidence": ["grep: get_order() ichida user_id tekshiruvi yo'q", "probe: userB token → 200 + canary"],
  "refutation_attempt": "@login_required va egalik tekshiruvi qidirildi; faqat autentifikatsiya bor, avtorizatsiya yo'q",
  "fix": "diff ...", "refs": ["CWE-639", "OWASP A01"]
}
```

---

## 5. Baholash (asosiy differensiator)

### 5.1 Protokol (ML intizomi)

- **Eval-driven:** avval baseline'lar va harness, keyin agent. Har bir yangi komponent dev'da metrikani siljitishi kerak — aks holda olib tashlaymiz.
- **Gipotezalar oldindan yoziladi** (H1…H7, pastda) va natijadan *oldin* commit qilinadi — git tarixi tartibni isbotlaydi.
- **Dev / test:** dev'da prompt va kod sozlanadi; test — 11-oktabrda muzlatgandan keyin, **bir marta**. Test natijasiga qarab sozlamaymiz; yomon bo'lsa — yomon deb yozamiz.
- **Determinizm:** temperature 0; yakuniy run 3 seed. Model digest, git SHA, config → `eval/results/<run>.json`.
- **LLM cache** (model + prompt + params → javob): qayta run arzon; **record/replay** — reviewer GPU'siz `make replay` bilan yozib olingan run'ni ko'ra oladi.
- **Statistika:** sonlarni (TP/FP/FN) va ishonch oralig'ini (Wilson/bootstrap) ko'rsatamiz; n kichik bo'lsa — "yo'nalish, isbot emas".
- **Harness'ning o'zini unit-test qilamiz** (matcher, metrika): xato baholash — baholamaslikdan yomon.

### 5.2 Targetlar

| Nom | Til | Nega kerak | Ground truth | Split |
|---|---|---|---|---|
| **CakeShop v1** (o'zimiz yozamiz) | Python/Flask | yangi (kontaminatsiyasiz); klassik + **biznes-logika** zaifliklari; har biriga "fixed twin" (FP o'lchash) | `ground_truth.yaml` | dev |
| **[RealVuln](https://github.com/kolega-ai/Real-Vuln-Benchmark)** (tashqi; Python, v3'da +TS/JS) | Py/TS | qo'lda belgilangan ground truth + FP-trap'lar; boshqa skanerlar bilan taqqoslash. **Avval tekshiramiz:** litsenziya, format, skorlash | benchmark bilan | repo'lar dev/test'ga bo'linadi |
| **CakeShop v2** (muzlatgandan keyin) | Python | yopiq test: yangi zaifliklar, agent prompt'lari ko'rilmagan holda yoziladi (ideal: do'st yozsa) | YAML | test |
| Juice Shop `routes/` | TS | kodda [`vuln-code-snippet` belgilari](https://help.owasp-juice.shop/appendix/code-snippets.html) = tayyor ground truth. Skandan oldin belgilarni **o'chiramiz** — aks holda javob oshkor | kod ichida | ixtiyoriy |
| DVWA | PHP | low/medium/high/**impossible** darajalar = tayyor zaif/to'g'rilangan juftliklar (FP testi) | struktura | ixtiyoriy |
| OWASP Benchmark (~100–200 namuna) | Java | klassik TPR/FPR, boshqa SAST'lar bilan taqqoslash | CSV | ixtiyoriy |

> RealVuln va Juice Shop haqidagi ma'lumot qidiruvdan olindi (to'liq o'qimadim); DVWA va OWASP Benchmark — xotiradan. 1–2-kuni mavjudligi, litsenziyasi va tuzilmasini tekshiramiz. Repo'larni `pin`lab (commit SHA) ishlatamiz.

**CakeShop** (Safia tortlar sotadi — xatdagi gapga ishora): ~20 zaiflik, ~10 sinf. Klassik: SQLi, XSS, path traversal, SSRF, deserialization, hardcoded secret, zaif hash, buzilgan authz/IDOR, mass assignment. **Biznes-logika:** narx/miqdor manipulyatsiyasi, promo-kod stacking, loyalty-ball race. Ataylab zaif: README'da katta ogohlantirish, deploy qilinmaydi.

### 5.3 Metrikalar

- **Finding-level P / R / F1.** strict = fayl + qator (±5) + CWE oilasi; lenient = fayl + qator. RealVuln bilan taqqoslash uchun F3 ham; lekin P va R **alohida** ko'rsatiladi (bizning g'oya — precision).
- **FP:** "fixed twin" / FP-trap'lardagi noto'g'ri signallar; KLOC'ga to'g'ri kelgan shovqin.
- **Verification gain:** precision L2 dan oldin/keyin; L0 rad etgan gallyutsinatsiyalar soni.
- **Kalibratsiya:** yorliq (`confirmed`/`likely`/…) bo'yicha haqiqiy precision.
- **Xarajat:** token, sekund/skan, tok/s, xotira. **Barqarorlik:** 3 run orasida Jaccard. **Structured-output:** valid JSON %.

### 5.4 Ablation matritsasi

| Kod | Tarkib |
|---|---|
| C0 | Semgrep + Bandit (faqat) |
| C1 | LLM-only: fayl/funksiya bo'yicha oddiy prompt |
| C2 | C0 nomzodlari + LLM triage |
| C3 | C2 + playbook / RAG |
| C4 | C3 + agentik verifier (tool'lar) + refuter + L0 |
| C5 | C4 + dinamik PoC (faqat CakeShop) |
| C6 | C4 + xotira |
| C7 | C4 + LoRA-triage (Tier 3) |

Modellar: kichik (7–9B) va o'rta (~14–32B, sig'sa); bitta modelda Q4 vs Q8.

### 5.5 Gipotezalar (oldindan)

- **H1** C2 precision'i C0'dan yuqori, recall'ni > 5 p.p. yo'qotmasdan.
- **H2** LLM-only (C1) Semgrep topa olmaydigan biznes-logika zaifliklarining bir qismini topadi (C0 shu sinfda ≈ 0).
- **H3** Verifier (C4) FP'ni ≥ 30% kamaytiradi, recall yo'qotishi ≤ 10 p.p. *(ishonchim past — 3-band; shuning uchun o'lchaymiz)*
- **H4** Qo'lda yozilgan playbook generik RAG'dan ko'proq yordam beradi (kichik modellarda).
- **H5** Model o'lchami kvantlash darajasidan muhimroq.
- **H6** Mashhur ilovalarda izoh/ismlar tozalansa, recall sezilarli tushadi (memorization).
- **H7** (Tier 3) triage-LoRA held-out loyihalarda FP-filtr aniqligini oshiradi.

### 5.6 Tajribalar (→ `docs/EXPERIMENTS.md`)

| # | Tajriba | Javob beradi |
|---|---|---|
| E1 | Model/kvant bake-off: valid-JSON %, tool-qadam aniqligi, triage aniqligi, tok/s, xotira | H5 |
| E2 | Baseline'lar C0 / C1: "LLM-only qancha FP beradi?" | H1, H2 |
| E3 | Ablation C2 → C4: verification gain | H1, H3 |
| E4 | Playbook vs RAG vs hech narsa | H4 |
| E5 | Memorization probe: izoh/hint/ism tozalash → tushish | H6 |
| E6 | Prompt-injection va path-jail testlari (agentni *o'zini* red-team qilish) | — |
| E7 | (Tier 3) LoRA-triage | H7 |
| E8 | (Tier 3) uz/ru tushuntirish sifati — siz qo'lda baholaysiz | — |

---

## 6. Texnik qarorlar (DECISIONS.md'ning boshlang'ich varianti)

| Mavzu | Tanlov | Nega | Rad etilgan |
|---|---|---|---|
| Til | Python 3.11+ (`uv`) | rol talabi (Python/PyTorch); ekotizim | — |
| LLM runtime | Ollama + OpenAI-mos API | hamma yerda ishlaydi, reviewer takrorlay oladi; GPU serverda vLLM/llama.cpp — faqat `base_url` | LM Studio/MLX-only (kamroq ko'chma) |
| Agent sikli | o'zimiz yozgan JSON-action sikl + pydantic | kichik modellarda native tool-calling ishonchsiz; log/replay/byudjet oson | LangGraph/CrewAI/AutoGen (nazorat kam, dependency ko'p) |
| Statik vositalar | Semgrep + Bandit + sir-qidiruv | ochiq, offline ishlaydi (`--metrics off`, qoidalar lokal) | CodeQL (litsenziya cheklovi — tekshiring), Joern (og'ir) |
| Parser | tree-sitter | ko'p til, tez | faqat regex |
| Retrieval | SQLite + numpy + lokal embedding | minimal dependency; minglab chunk uchun yetadi | Chroma/Weaviate (ortiqcha) |
| Chiqish | JSON → SARIF 2.1.0 + Markdown (+ HTML) | SARIF — sanoat standarti | maxsus web-UI |
| Tasdiqlash | L0–L3 narvon; dinamik probe deklarativ | LLM'ga ixtiyoriy kod ishlatishga ruxsat bermaymiz | agentga shell berish |
| Fine-tune | faqat triage (Tier 3), go/no-go 8-oktabr | PrimeVul saboqi | detection fine-tune |
| Cloud LLM | mahsulotda yo'q. Ixtiyoriy: baholashda "yuqori chegara" sifatida, ochiq belgilanadi | topshiriq: "lokal, imkon qadar" | — |
| Til qamrovi | Python (chuqur), JS/TS (asosiy); qolganlari LLM-only | vaqt | hamma tillar |

**Model nomzodlari** (blog sharhlaridan, *tekshirilmagan* — 1-kuni Ollama kutubxonasida hozirgi holatini ko'ring; tanlov jihozga sig'ishiga qarab): Qwen2.5-Coder 7B/14B (baseline), gpt-oss-20b, Devstral 24B, Gemma 4, Qwen3-Coder-Next. Strukturali chiqish: Ollama `format` = JSON schema; ishlamasa — GBNF/outlines.

---

## 7. Reja

Kalendar: 1-okt payshanba … 14-okt chorshanba. Dam olish kunlari (3–4 va 10–11-okt) uzun bloklar — og'ir run'lar uchun.

**Hajm** (taxminiy): kuniga ~2 soat → faqat Tier 1; ~3–4 soat → Tier 1 + Tier 2 ning yarmi; 6+ soat → Tier 2 to'liq + Tier 3 dan bittasi.

- **Tier 1 (majburiy):** pipeline (index → nomzod → analyst → verifier → report), L0 + refuter, guardrails + audit, eval harness + baseline'lar + ablation C0–C4, CakeShop, hujjatlar.
- **Tier 2 (tavsiya):** playbook/RAG (C3), bake-off (E1), prompt-injection testi + THREAT_MODEL (E6), record/replay, RealVuln adapteri, dinamik PoC (C5), xotira (C6).
- **Tier 3 (ixtiyoriy, birinchi kesiladi):** LoRA-triage (E7), patch taklifi + tekshiruvi, uz/ru tushuntirish (E8), og'ir memorization probe.

### Bosqich 0 — Asos (1–2-okt)
- [ ] Jihoz aniqlash; `ollama` o'rnatish; 1 ta kichik model bilan sinash (tok/s, JSON-schema rejimi)
- [ ] Model shortlist (2–3 ta, xotiraga sig'adigan)
- [ ] RealVuln'ni tekshirish: litsenziya, format, skorlash → ishlatamizmi?
- [ ] Protokol + gipotezalar yozish (`EXPERIMENTS.md`)
- [ ] O'qish (2–3 soat, faqat abstract + xulosa): PrimeVul, IRIS, "Sifting the Noise", RealVuln
- [ ] Repo skeleti: pyproject, Makefile, CI, mock LLM

**DoD:** `make test` yashil (mock LLM bilan); modelga so'rov sizning mashinangizda ishlaydi; gipotezalar commit qilingan.

### Bosqich 1 — Skelet + baseline (3–5-okt)
- [ ] CakeShop v1 + fixed twin + `ground_truth.yaml`
- [ ] Eval harness (matcher, metrika, cache) + unit testlar
- [ ] C0 va C1 baseline natijalari
- [ ] Yupqa kesim: index → nomzod → LLM triage → report (JSON + MD)

**DoD:** birinchi natija jadvali (xunuk bo'lsa ham) repo'da; `make eval-dev` ishlaydi.

### Bosqich 2 — Agent (6–8-okt)
- [ ] Tool'lar: `read_file` (jail), `grep`, `find_def/refs`, `list_routes`
- [ ] Verifier sikli (JSON action, byudjet) + L0 iqtibos tekshiruvi + refuter
- [ ] Playbook'lar + RAG (`make kb`)
- [ ] Ablation C2 → C4 dev'da; failure analysis #1 (kamida 10 ta xato qo'lda ko'rib chiqiladi)
- [ ] **8-okt go/no-go:** LoRA-triage — faqat jadval orqada bo'lmasa va GPU (Colab/lokal) bo'lsa

**DoD:** ablation jadvali + "nima kutilmagan bo'ldi" yozuvi.

### Bosqich 3 — Chuqurlik (9–11-okt)
Har biri time-box 0.5–1 kun:
- [ ] Policy + audit + prompt-injection va path-jail testlari + `THREAT_MODEL.md` **(majburiy)**
- [ ] Model/kvant bake-off (E1)
- [ ] Dinamik PoC: CakeShop, docker compose, canary *(Docker ishlasa)*
- [ ] Xotira (FP feedback)
- [ ] 11-okt kechqurun: **muzlatish** — kod/prompt/playbook, git tag `freeze-1`

**DoD:** kamida 2 ta qo'shimcha tajriba natijasi; kod muzlatilgan.

### Bosqich 4 — Yakuniy baholash (12-okt)
- [ ] CakeShop v2 (yangi zaifliklar; agent prompt'larini ko'rmasdan)
- [ ] Test split'da **bir marta** run (3 seed); transcript'lar yoziladi (kechasi ishga tushirib qo'yish mumkin)
- [ ] ~30 ta FP'ni qo'lda adjudikatsiya qilish

**DoD:** yakuniy natijalar JSON + jadval.

### Bosqich 5 — Yozish + topshirish (13–14-okt)
- [ ] README (1 sahifa), DECISIONS, EXPERIMENTS (muvaffaqiyatsizliklar bilan), LIMITATIONS, THREAT_MODEL, ARCHITECTURE
- [ ] Demo: 3–5 daqiqalik ekran yozuvi + `make replay`
- [ ] "Yangi odam" testi: toza muhitda README bo'yicha ishga tushirish
- [ ] Repo ruxsatlari (private bo'lsa Fahriddin'ga access yoki public)
- [ ] Email (8-bo'lim shabloni) — **14-okt**'da yuborish

### Kesish chizig'i
Orqada qolsak, shu tartibda voz kechamiz: LoRA → uz/ru → patch taklifi → xotira → dinamik PoC → RAG (playbook qoladi).
**Hech qachon kesilmaydi:** baseline'lar + eval harness + L0/L2 verifikatsiya + halol README/EXPERIMENTS.
**Fallback** (10-okt'da juda orqada bo'lsak): Bosqich 1–2 natijalari + halol tahlil — baribir kuchli topshiriq.

---

## 8. Ish taqsimoti, repo va topshirish

### Kim nima qiladi

| Men (Claude) | Siz |
|---|---|
| Repo skeleti, kod, unit testlar (mock LLM), CakeShop, eval harness, hujjat skeletlari, CI | Jihoz/Ollama, real run'lar (modelli), Docker lablari, natijalarni ko'rish va adjudikatsiya, demo yozuvi |
| Natijalarni tahlil qilish, xatolarni tasniflash, kodni tuzatish | Har bir qarorni tushunish; yakuniy matnlarni o'z so'zingizda tahrirlash; email |

**Tavsiya:** 0-bosqichdan keyin repo'ni o'z kompyuteringizga clone qilib, Claude Code'ni o'sha yerda ishga tushiring — shunda men Ollama/Docker'ni bevosita ishlataman va iteratsiya ancha tezlashadi. Cloud sessiya — skelet, kod, test, hujjat uchun yaxshi; ML iteratsiyasi uchun yomon (model yuklab bo'lmaydi). Bu yerda PyPI ochiq, demak Semgrep/Bandit, tree-sitter va CakeShop testlari (Flask test client) ishlaydi.

Aylanma: branch → pull → run → natijalarni commit → push → men tahlil qilaman.

### Repo tuzilmasi

```
safia-security-agent/
├── README.md                 # 1 sahifa: nima, natija, 2 daqiqada sinash, cheklovlar
├── docs/
│   ├── PLAN.md               # shu hujjat (ichki)
│   ├── DECISIONS.md          # ADR uslubi: tanlov, alternativa, nega
│   ├── EXPERIMENTS.md        # gipoteza → sozlama → natija → saboq (muvaffaqiyatsizlar ham)
│   ├── ARCHITECTURE.md
│   ├── THREAT_MODEL.md       # agentning o'zi uchun tahdidlar
│   └── LIMITATIONS.md
├── src/safia_sec/
│   ├── cli.py
│   ├── llm/                  # OpenAI-mos klient, JSON-schema, cache, record/replay, mock
│   ├── index/                # tree-sitter, symbols, routes, refs
│   ├── tools/                # read_file(jail), grep, find_def/refs, semgrep/bandit, http_probe
│   ├── agent/                # scout, analyst, verifier, refuter, policy, memory
│   ├── knowledge/            # playbooks/ (qo'lda), KB build + retriever
│   ├── report/               # json, sarif, markdown, html
│   └── eval/                 # ground-truth schema, matcher, metrics, runner, configs
├── targets/cakeshop/         # v1 + fixed twin + ground_truth.yaml (+ docker-compose)
├── eval/                     # configs/, results/ (commit), replays/
├── tests/                    # unit + mock-LLM integratsiya + security testlari
├── docker/                   # sandbox image
├── .github/workflows/ci.yml  # ruff + pytest (GPU kerak emas)
├── Makefile                  # setup | test | scan | eval-dev | eval-test | replay | demo
└── pyproject.toml
```

Git tarixi ham baholanishi mumkin: kichik, ma'noli commit'lar; muvaffaqiyatsiz tajribalar ham tarixda qoladi.

### README (reviewer yo'li, 15 daqiqa)
1. 3 jumla: nima va nega (thesis).
2. Natija jadvali (3–4 qator) va bitta halol xulosa.
3. "2 daqiqada sinang": `make replay` (GPU'siz) va `make demo` (Ollama bilan).
4. Qanday ishlaydi (diagramma) → ARCHITECTURE.
5. Nima ishlamadi va nimani o'rgandik → EXPERIMENTS.
6. Cheklovlar, xavfsizlik doirasi, AI yordami.

### Email shabloni (topshirish; inglizcha)

```
Subject: Re: <original subject>

Hello Fahriddin,

Here is my case study submission: <repo link>

Short version
- Idea: a small local LLM is a weak detector but a useful investigator. Static tools propose
  candidates; the agent gathers evidence with read-only tools and tries to refute its own claim;
  every finding carries machine-checkable evidence (optionally a sandboxed PoC on a local lab).
- Models: <names>, run locally via Ollama.
- Results (frozen test split, n=<...>): <1-2 numbers from EXPERIMENTS.md>.
  What did not work: <one line>.
- Start here: README -> docs/DECISIONS.md -> docs/EXPERIMENTS.md.
  `make replay` shows a recorded run without a GPU.
- Scope/safety: only own and local lab targets; enforced in code (docs/THREAT_MODEL.md).
- AI assistance: I used Claude Code as a pair-programmer; experiments, numbers and
  decisions are mine and documented.

Year of study: <...>  (if not already mentioned)

Best regards,
<Name>
```

---

## 9. Ochiq savollar (sizdan)

1. **Jihoz:** OS / CPU / RAM / GPU (masalan "MacBook M2 16 GB" yoki "RTX 3060 12 GB")? → model sinfi, LoRA mumkinligi, eval hajmi.
2. **Vaqt:** kuniga necha soat? Yaqin 2 haftada imtihon/ish bormi? → Tier hajmi.
3. **Ish muhiti:** Claude Code'ni o'z kompyuteringizda ishga tushira olasizmi (8-bo'limdagi tavsiya)?
4. **Repo:** public yoki private? (private bo'lsa — Fahriddin'ga access beramiz.)
5. **Yo'nalish:** Python-first, CakeShop + RealVuln, LoRA — ixtiyoriy/oxirida. Rozimisiz?

---

## 10. Manbalar

- PrimeVul: [Vulnerability Detection with Code Language Models: How Far Are We?](https://arxiv.org/pdf/2403.18624)
- [Sifting the Noise: LLM Agents in Vulnerability False Positive Filtering](https://arxiv.org/abs/2601.22952)
- [RealVuln](https://arxiv.org/abs/2604.13764) · [repo](https://github.com/kolega-ai/Real-Vuln-Benchmark)
- [IRIS: LLM-Assisted Static Analysis](https://proceedings.iclr.cc/paper_files/paper/2025/file/582d4e27fa24168f3af1f4582655034b-Paper-Conference.pdf) — LLM taint spetsifikatsiyasini chiqaradi va alert'larni filtrlaydi
- Yaqin ishlar (o'qilmagan): [SastBench](https://arxiv.org/pdf/2601.02941), [Memoir](https://arxiv.org/pdf/2608.09181), [OpenAnt](https://arxiv.org/pdf/2606.19149)
- [Vulnhuntr (Dark Reading)](https://www.darkreading.com/application-security/open-source-llm-tool-finds-python-zero-days)
- [DARPA AIxCC](https://www.darpa.mil/news/2024/ai-cyber-challenge-cybersecurity) · [Buttercup](https://trailofbits.com/buttercup/)
- [Juice Shop coding challenges](https://help.owasp-juice.shop/appendix/code-snippets.html)
- Model sharhlari (blog, tekshirilmagan): [Tembo](https://www.tembo.io/blog/best-local-llm-for-coding), [howaiworks](https://howaiworks.ai/blog/best-open-weight-llm-agentic-coding)

---

## 11. Jurnal (nima o'zgardi va nega)

- **2026-10-01** — Reja v1. Muhit tekshirildi: 4 CPU / 16 GB / GPU yo'q / Docker daemon yo'q; PyPI ochiq; HuggingFace, Ollama registry va arXiv bloklangan. Shu sababli modelli run'lar va Docker lablari foydalanuvchi mashinasida rejalashtirildi.
