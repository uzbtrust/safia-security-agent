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
