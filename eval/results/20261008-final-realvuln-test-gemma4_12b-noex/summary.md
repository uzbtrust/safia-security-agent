# RealVuln test: gemma4:12b

4 repos, benchmark 7a710251f55c, seed 1, verify on, bandit on, examples off. RealVuln matcher semantics (file + acceptable CWE + line +-10).

| stage | TP | FP | FN | traps hit (FP) | precision | recall (95% CI) | F3 |
|---|---|---|---|---|---|---|---|
| raw | 31 | 16 | 49 | - | 0.66 | 0.39 (0.29-0.50) | 0.40 |
| grounded | 30 | 15 | 50 | - | 0.67 | 0.38 (0.28-0.48) | 0.39 |
| verified | 30 | 13 | 50 | - | 0.70 | 0.38 (0.28-0.48) | 0.39 |
| final | 30 | 13 | 50 | 2 | 0.70 | 0.38 (0.28-0.48) | 0.39 |

Final stage per stratum and repo:

| repo | authorship | LOC | TP | FP | FN | FN in .py | precision | recall | F3 |
|---|---|---|---|---|---|---|---|---|---|
| realvuln-pythonssti | human_authored | 13 | 1 | 0 | 1 | 1 | 1.00 | 0.50 | 0.53 |
| realvuln-dsvw | human_authored | 93 | 7 | 0 | 20 | 20 | 1.00 | 0.26 | 0.28 |
| realvuln-damn-vulnerable-flask-application | human_authored | 224 | 5 | 3 | 9 | 9 | 0.62 | 0.36 | 0.37 |
| **all human_authored** | | 330 | 13 | 3 | 30 | 30 | 0.81 | 0.30 | 0.32 |
| vc-codex-seeded-v2-fintech-lending-fastapi | llm_generated | 928 | 17 | 10 | 20 | 20 | 0.63 | 0.46 | 0.47 |
| **all llm_generated** | | 928 | 17 | 10 | 20 | 20 | 0.63 | 0.46 | 0.47 |

Recall over labels in .py files only (the scanner's scope): 0.38.
Cost: 60 LLM calls, 293 s model time, 0 error(s).
