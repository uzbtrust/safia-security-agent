# Blue gym evaluation: gemma4:12b

9 cases (2 clean, 7 injected), seeds [1, 2, 3], verify on, bandit on, examples on. n is small: a direction, not proof.

| stage | strict recall | function recall | CWE-only | located (any CWE) | clean runs with a false signal | findings per clean run | extras per injected run |
|---|---|---|---|---|---|---|---|
| raw | 18/21 (0.65-0.95) | 21/21 (0.85-1.00) | 21/21 (0.85-1.00) | 21/21 | 3/6 | 0.83 | 0.24 |
| grounded | 18/21 (0.65-0.95) | 21/21 (0.85-1.00) | 21/21 (0.85-1.00) | 21/21 | 3/6 | 0.83 | 0.14 |
| verified | 18/21 (0.65-0.95) | 21/21 (0.85-1.00) | 21/21 (0.85-1.00) | 21/21 | 0/6 | 0.00 | 0.00 |
| final | 18/21 (0.65-0.95) | 21/21 (0.85-1.00) | 21/21 (0.85-1.00) | 21/21 | 0/6 | 0.00 | 0.00 |

Final stage per case (strict / function, of seeds):

| case | strict | function |
|---|---|---|
| bank/CWE-22 | 3/3 | 3/3 |
| bank/CWE-639 | 0/3 | 3/3 |
| bank/CWE-840 | 3/3 | 3/3 |
| bank/CWE-89 | 3/3 | 3/3 |
| shop/CWE-22 | 3/3 | 3/3 |
| shop/CWE-639 | 3/3 | 3/3 |
| shop/CWE-89 | 3/3 | 3/3 |

Cost: 56 LLM calls, 119484 prompt / 5841 generated tokens, 1853 s model time, 0 error(s).

## Notes (LOCAL, hand-written)
- Same dev cases, seeds and settings as `20261007-blue-gym-gemma4_12b` (baseline: function 18/21, strict 16/21, clean runs with a false signal 2/6), but with the step-4 prompts: `detect.md` rewritten and few-shot examples on (cloud commits e8882d1 and b493c0c; `meta.prompt_sha` 2d3a760131b8). All 56 LLM calls ran live: the old cache does not apply.
- Function recall rose from 18/21 to 21/21; bank/CWE-840 (negative transfer) went from 0/3 to 3/3 at every stage. Strict recall is 18/21 because bank/CWE-639 is reported on the `def` line, outside the +-5 window (function level 3/3).
- The verifier kept 21 of 21 true hits and rejected all 5 findings on clean apps and all 3 extras: no finding survives on a clean app (baseline 2/6) and no extra on an injected app (baseline 0.43 per run). The raw output still has a false signal in 3 of 6 clean runs.
- The step-4 prompts were written after the baseline run and aim at the gaps it showed (bank/CWE-840 above all), so this is a dev-set gain, not evidence of generalisation. The rewrite and the few-shot examples are not separated here; a `--no-examples` run would isolate the examples.
- 0 errors, no truncated context. Prompts are longer (2134 tokens per call against 1339 in the baseline): 33.1 s per call, 68.7 model seconds per run (baseline 64.7). Swap reached about 12.8 GB; free disk fell from 41.7 to 29.9 GB and came back to 39.6 GB after `ollama stop`.
- Dev split only; blog (test) was not run.
