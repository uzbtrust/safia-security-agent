# RealVuln dev: gemma4:12b

6 repos, benchmark 7a710251f55c, seed 1, verify on, bandit on, examples on. RealVuln matcher semantics (file + acceptable CWE + line +-10).

| stage | TP | FP | FN | traps hit (FP) | precision | recall (95% CI) | F3 |
|---|---|---|---|---|---|---|---|
| raw | 44 | 21 | 47 | - | 0.68 | 0.48 (0.38-0.58) | 0.50 |
| grounded | 41 | 18 | 50 | - | 0.69 | 0.45 (0.35-0.55) | 0.47 |
| verified | 40 | 12 | 51 | - | 0.77 | 0.44 (0.34-0.54) | 0.46 |
| final | 40 | 12 | 51 | 0 | 0.77 | 0.44 (0.34-0.54) | 0.46 |

Final stage per stratum and repo:

| repo | authorship | LOC | TP | FP | FN | FN in .py | precision | recall | F3 |
|---|---|---|---|---|---|---|---|---|---|
| realvuln-insecure-web | human_authored | 46 | 5 | 1 | 4 | 3 | 0.83 | 0.56 | 0.57 |
| realvuln-intentionally-vulnerable-python-application | human_authored | 46 | 5 | 0 | 2 | 2 | 1.00 | 0.71 | 0.74 |
| realvuln-python-insecure-app | human_authored | 79 | 2 | 0 | 6 | 5 | 1.00 | 0.25 | 0.27 |
| realvuln-vulnerable-api | human_authored | 122 | 7 | 1 | 7 | 7 | 0.88 | 0.50 | 0.52 |
| realvuln-vulnerable-tornado-app | human_authored | 130 | 6 | 0 | 8 | 8 | 1.00 | 0.43 | 0.45 |
| **all human_authored** | | 423 | 25 | 2 | 27 | 25 | 0.93 | 0.48 | 0.51 |
| vc-codex-seeded-v2-hr-payroll-django | llm_generated | 1336 | 15 | 10 | 24 | 24 | 0.60 | 0.38 | 0.40 |
| **all llm_generated** | | 1336 | 15 | 10 | 24 | 24 | 0.60 | 0.38 | 0.40 |

Recall over labels in .py files only (the scanner's scope): 0.45.
Cost: 98 LLM calls, 4393 s model time, 1 error(s).

## Notes (LOCAL, hand-written)
- One seed (1), dev split only, step-4 prompts with few-shot examples on, verifier and Bandit on. All 98 LLM calls ran live (13:40-14:53, 73 min, 44.8 s per call, 2052 prompt and 123 generated tokens per call). The test half and a `--no-examples` run were not done, so there is no before/after for the examples on this benchmark yet.
- Final stage: 40 TP, 12 FP, 51 FN, precision 0.77, recall 0.44, F3 0.46 (primary metric); none of the 16 traps was flagged. Human-authored repos: recall 0.48 at precision 0.93 (25 TP, 2 FP). The LLM-generated Django repo: recall 0.38 at precision 0.60 (15 TP, 10 FP, 24 FN).
- The filtering stages trade recall for precision: grounding lost 3 TP and 3 FP, the verifier 1 TP and 6 FP, so precision rose from 0.68 to 0.77 while F3 fell from 0.50 (raw) to 0.46. Most false positives sit in the Django repo (19 raw, 10 final).
- Most frequent missed labels: CWE-307 (5), CWE-798 (4), then CWE-79, CWE-200, CWE-434, CWE-312 and CWE-862 (3 each). 49 of the 51 FN are in .py files.
- 1 error: the verifier reply at vc-codex-seeded-v2-hr-payroll-django `config/payroll_operations.py:187` was invalid JSON (`Extra data`). The candidate was kept unverified (fail-open) and happens to be a TP (CWE-943).
- Machine: free memory about 72% before the run, swap peaked near 13.3 GB, free disk stayed above 28.9 GB.
