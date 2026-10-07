# Blue gym evaluation: gemma4:12b

9 cases (2 clean, 7 injected), seeds [1, 2, 3], verify on, bandit on. n is small: a direction, not proof.

| stage | strict recall | function recall | CWE-only | clean runs with a false signal | findings per clean run | extras per injected run |
|---|---|---|---|---|---|---|
| raw | 12/21 (0.37-0.76) | 18/21 (0.65-0.95) | 18/21 (0.65-0.95) | 3/6 | 0.83 | 0.62 |
| grounded | 16/21 (0.55-0.89) | 18/21 (0.65-0.95) | 18/21 (0.65-0.95) | 2/6 | 0.67 | 0.57 |
| verified | 16/21 (0.55-0.89) | 18/21 (0.65-0.95) | 18/21 (0.65-0.95) | 2/6 | 0.33 | 0.43 |
| final | 16/21 (0.55-0.89) | 18/21 (0.65-0.95) | 18/21 (0.65-0.95) | 2/6 | 0.33 | 0.43 |

Final stage per case (strict / function, of seeds):

| case | strict | function |
|---|---|---|
| bank/CWE-22 | 3/3 | 3/3 |
| bank/CWE-639 | 3/3 | 3/3 |
| bank/CWE-840 | 0/3 | 0/3 |
| bank/CWE-89 | 3/3 | 3/3 |
| shop/CWE-22 | 3/3 | 3/3 |
| shop/CWE-639 | 1/3 | 3/3 |
| shop/CWE-89 | 3/3 | 3/3 |

Cost: 61 LLM calls, 81650 prompt / 7380 generated tokens, 1747 s model time, 0 error(s).

## Notes (LOCAL, hand-written)
- 52 of the 61 LLM calls ran live on 2026-10-07; 9 were replayed from `.cache/llm` (an interrupted run of 2026-10-01, same model digest `6114515d63c1`, same prompts and options). Their stored model time is the original one.
- Machine: AC power, no heavy apps in the process list at the start, but memory was tight (free about 11%, swap up to 9.9 GB), so model seconds are pessimistic. Prompt hash of detect + verify: 495704089c57 (commit 74fbead).
- Function recall is 18/21 at every stage. The only missed case is bank/CWE-840 (negative transfer amount, a business-logic check) in 3 of 3 seeds, although the detect prompt names negative amounts. Grounding lifted strict recall from 12/21 to 16/21 by snapping the line to the quoted code; it removed no hit.
- The verifier rejected 0 of 18 true hits, 3 of 12 extras and 2 of 4 findings on clean apps. Two of six clean runs keep a false signal: bank/clean CWE-89 at line 73 (a parameterized LIKE query) in 2 seeds. shop/clean ended clean in all 3 seeds.
- No invalid JSON, no truncated context (prompts of about 1.1-1.6k tokens against 8192). 28.6 s per call, 64.7 model seconds per run.
- Dev split only (shop, bank); blog (test) was not run. Bandit on the same seven injected cases: 2/7, no false signal.
