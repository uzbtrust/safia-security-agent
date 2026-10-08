# Blue gym evaluation: gemma4:12b

5 cases (1 clean, 4 injected), seeds [1, 2, 3], verify on, bandit on, examples on. n is small: a direction, not proof.

| stage | strict recall | function recall | CWE-only | located (any CWE) | clean runs with a false signal | findings per clean run | extras per injected run |
|---|---|---|---|---|---|---|---|
| raw | 7/12 (0.32-0.81) | 4/12 (0.14-0.61) | 9/12 (0.47-0.91) | 4/12 | 3/3 | 2.33 | 1.50 |
| grounded | 9/12 (0.47-0.91) | 6/12 (0.25-0.75) | 9/12 (0.47-0.91) | 6/12 | 3/3 | 2.33 | 1.33 |
| verified | 9/12 (0.47-0.91) | 6/12 (0.25-0.75) | 9/12 (0.47-0.91) | 6/12 | 3/3 | 1.33 | 0.67 |
| final | 9/12 (0.47-0.91) | 6/12 (0.25-0.75) | 9/12 (0.47-0.91) | 6/12 | 3/3 | 1.33 | 0.67 |

Final stage per case (strict / function, of seeds):

| case | strict | function |
|---|---|---|
| blog/CWE-330 | 0/3 | 0/3 |
| blog/CWE-601 | 3/3 | 0/3 |
| blog/CWE-79 | 3/3 | 3/3 |
| blog/CWE-915 | 3/3 | 3/3 |

Cost: 47 LLM calls, 113195 prompt / 5097 generated tokens, 227 s model time, 0 error(s).
