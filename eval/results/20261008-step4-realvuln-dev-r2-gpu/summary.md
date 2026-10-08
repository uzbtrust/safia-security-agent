# RealVuln dev: gemma4:12b

6 repos, benchmark 7a710251f55c, seed 1, verify on, bandit on, examples on. RealVuln matcher semantics (file + acceptable CWE + line +-10).

| stage | TP | FP | FN | traps hit (FP) | precision | recall (95% CI) | F3 |
|---|---|---|---|---|---|---|---|
| raw | 55 | 18 | 36 | - | 0.75 | 0.60 (0.50-0.70) | 0.62 |
| grounded | 55 | 18 | 36 | - | 0.75 | 0.60 (0.50-0.70) | 0.62 |
| verified | 53 | 11 | 38 | - | 0.83 | 0.58 (0.48-0.68) | 0.60 |
| final | 53 | 11 | 38 | 0 | 0.83 | 0.58 (0.48-0.68) | 0.60 |

Final stage per stratum and repo:

| repo | authorship | LOC | TP | FP | FN | FN in .py | precision | recall | F3 |
|---|---|---|---|---|---|---|---|---|---|
| realvuln-insecure-web | human_authored | 46 | 7 | 1 | 2 | 1 | 0.88 | 0.78 | 0.79 |
| realvuln-intentionally-vulnerable-python-application | human_authored | 46 | 6 | 0 | 1 | 1 | 1.00 | 0.86 | 0.87 |
| realvuln-python-insecure-app | human_authored | 79 | 4 | 0 | 4 | 3 | 1.00 | 0.50 | 0.53 |
| realvuln-vulnerable-api | human_authored | 122 | 9 | 0 | 5 | 5 | 1.00 | 0.64 | 0.67 |
| realvuln-vulnerable-tornado-app | human_authored | 130 | 7 | 2 | 7 | 7 | 0.78 | 0.50 | 0.52 |
| **all human_authored** | | 423 | 33 | 3 | 19 | 17 | 0.92 | 0.63 | 0.65 |
| vc-codex-seeded-v2-hr-payroll-django | llm_generated | 1336 | 20 | 8 | 19 | 19 | 0.71 | 0.51 | 0.53 |
| **all llm_generated** | | 1336 | 20 | 8 | 19 | 19 | 0.71 | 0.51 | 0.53 |

Recall over labels in .py files only (the scanner's scope): 0.60.
Cost: 110 LLM calls, 619 s model time, 0 error(s).
