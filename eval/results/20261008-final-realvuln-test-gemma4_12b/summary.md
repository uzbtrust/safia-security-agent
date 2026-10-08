# RealVuln test: gemma4:12b

4 repos, benchmark 7a710251f55c, seed 1, verify on, bandit on, examples on. RealVuln matcher semantics (file + acceptable CWE + line +-10).

| stage | TP | FP | FN | traps hit (FP) | precision | recall (95% CI) | F3 |
|---|---|---|---|---|---|---|---|
| raw | 34 | 8 | 46 | - | 0.81 | 0.42 (0.32-0.53) | 0.45 |
| grounded | 33 | 7 | 47 | - | 0.82 | 0.41 (0.31-0.52) | 0.43 |
| verified | 31 | 9 | 49 | - | 0.78 | 0.39 (0.29-0.50) | 0.41 |
| final | 31 | 9 | 49 | 1 | 0.78 | 0.39 (0.29-0.50) | 0.41 |

Final stage per stratum and repo:

| repo | authorship | LOC | TP | FP | FN | FN in .py | precision | recall | F3 |
|---|---|---|---|---|---|---|---|---|---|
| realvuln-pythonssti | human_authored | 13 | 1 | 0 | 1 | 1 | 1.00 | 0.50 | 0.53 |
| realvuln-dsvw | human_authored | 93 | 5 | 2 | 22 | 22 | 0.71 | 0.19 | 0.20 |
| realvuln-damn-vulnerable-flask-application | human_authored | 224 | 5 | 2 | 9 | 9 | 0.71 | 0.36 | 0.38 |
| **all human_authored** | | 330 | 11 | 4 | 32 | 32 | 0.73 | 0.26 | 0.27 |
| vc-codex-seeded-v2-fintech-lending-fastapi | llm_generated | 928 | 20 | 5 | 17 | 17 | 0.80 | 0.54 | 0.56 |
| **all llm_generated** | | 928 | 20 | 5 | 17 | 17 | 0.80 | 0.54 | 0.56 |

Recall over labels in .py files only (the scanner's scope): 0.39.
Cost: 55 LLM calls, 300 s model time, 0 error(s).
