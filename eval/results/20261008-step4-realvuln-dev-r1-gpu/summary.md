# RealVuln dev: gemma4:12b

6 repos, benchmark 7a710251f55c, seed 1, verify on, bandit on, examples on. RealVuln matcher semantics (file + acceptable CWE + line +-10).

| stage | TP | FP | FN | traps hit (FP) | precision | recall (95% CI) | F3 |
|---|---|---|---|---|---|---|---|
| raw | 39 | 18 | 52 | - | 0.68 | 0.43 (0.33-0.53) | 0.45 |
| grounded | 37 | 14 | 54 | - | 0.73 | 0.41 (0.31-0.51) | 0.43 |
| verified | 37 | 9 | 54 | - | 0.80 | 0.41 (0.31-0.51) | 0.43 |
| final | 37 | 9 | 54 | 0 | 0.80 | 0.41 (0.31-0.51) | 0.43 |

Final stage per stratum and repo:

| repo | authorship | LOC | TP | FP | FN | FN in .py | precision | recall | F3 |
|---|---|---|---|---|---|---|---|---|---|
| realvuln-insecure-web | human_authored | 46 | 5 | 1 | 4 | 3 | 0.83 | 0.56 | 0.57 |
| realvuln-intentionally-vulnerable-python-application | human_authored | 46 | 2 | 1 | 5 | 5 | 0.67 | 0.29 | 0.30 |
| realvuln-python-insecure-app | human_authored | 79 | 2 | 0 | 6 | 5 | 1.00 | 0.25 | 0.27 |
| realvuln-vulnerable-api | human_authored | 122 | 7 | 1 | 7 | 7 | 0.88 | 0.50 | 0.52 |
| realvuln-vulnerable-tornado-app | human_authored | 130 | 6 | 0 | 8 | 8 | 1.00 | 0.43 | 0.45 |
| **all human_authored** | | 423 | 22 | 3 | 30 | 28 | 0.88 | 0.42 | 0.45 |
| vc-codex-seeded-v2-hr-payroll-django | llm_generated | 1336 | 15 | 6 | 24 | 24 | 0.71 | 0.38 | 0.40 |
| **all llm_generated** | | 1336 | 15 | 6 | 24 | 24 | 0.71 | 0.38 | 0.40 |

Recall over labels in .py files only (the scanner's scope): 0.42.
Cost: 92 LLM calls, 557 s model time, 1 error(s).
