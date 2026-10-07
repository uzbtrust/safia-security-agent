# Blue gym evaluation: qwen3.5:9b

9 cases (2 clean, 7 injected), seeds [1, 2, 3], verify on, bandit on. n is small: a direction, not proof.

| stage | strict recall | function recall | CWE-only | clean runs with a false signal | findings per clean run | extras per injected run |
|---|---|---|---|---|---|---|
| raw | 11/21 (0.32-0.72) | 11/21 (0.32-0.72) | 11/21 (0.32-0.72) | 6/6 | 1.50 | 1.14 |
| grounded | 9/21 (0.24-0.63) | 9/21 (0.24-0.63) | 9/21 (0.24-0.63) | 6/6 | 1.50 | 1.05 |
| verified | 1/21 (0.01-0.23) | 1/21 (0.01-0.23) | 1/21 (0.01-0.23) | 1/6 | 0.17 | 0.05 |
| final | 1/21 (0.01-0.23) | 1/21 (0.01-0.23) | 1/21 (0.01-0.23) | 1/6 | 0.17 | 0.05 |

Final stage per case (strict / function, of seeds):

| case | strict | function |
|---|---|---|
| bank/CWE-22 | 0/3 | 0/3 |
| bank/CWE-639 | 0/3 | 0/3 |
| bank/CWE-840 | 0/3 | 0/3 |
| bank/CWE-89 | 0/3 | 0/3 |
| shop/CWE-22 | 0/3 | 0/3 |
| shop/CWE-639 | 0/3 | 0/3 |
| shop/CWE-89 | 1/3 | 1/3 |

Cost: 68 LLM calls, 85130 prompt / 9064 generated tokens, 1244 s model time, 0 error(s).

## Notes (LOCAL, hand-written)
- All 68 LLM calls ran live on 2026-10-07 (no cache replay). Model digest `56671c2ab938...` is the registry's re-packaged revision seen on 2026-10-06 (weights 5.63 GB + vision projector 0.92 GB); the 2026-10-01 probe used the earlier packaging `6488c96fa5fa`. Same prompts and options as the gemma4:12b run (prompt hash 495704089c57), same day.
- Raw function recall is 11/21 (gemma4:12b 18/21): the IDOR cases (shop and bank CWE-639) and bank/CWE-840 are missed in 3 of 3 seeds, and the raw output has a false signal in 6 of 6 clean runs.
- The verifier is the same model and collapses recall: it rejected 9 of 10 true hits (90%), 21 of 22 extras and 8 of 9 findings on clean apps, so function recall falls from 9/21 (grounded) to 1/21. Several reasons are factually wrong, e.g. a SQL injection is called parameterized and `os.path.join` is said to prevent directory traversal.
- Grounding lowered function recall from 11/21 to 9/21 (two hits lost: dropped for evidence not found in the source, or moved by the line snap) and removed no false-signal run.
- The one surviving false signal is bank/clean CWE-532 at line 20 (seed data containing `VIP-SECRET-MEMO`).
- No invalid JSON, no truncated context. 18.3 s per call, 46.1 model seconds per run (gemma4:12b 64.7); memory was less tight than during the Gemma run (swap 2-7 GB).
- Dev split only. The rule in docs/EXPERIMENTS.md picks gemma4:12b (step 1, recall gap 17 of 21 runs); the raw and grounded stages give gaps of 7 and 9, so the choice does not depend on the verifier.
