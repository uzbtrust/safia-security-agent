# Blue gym evaluation: gemma4:12b

5 cases (1 clean, 4 injected), seeds [1, 2, 3], verify on, bandit on, examples off. n is small: a direction, not proof.

| stage | strict recall | function recall | CWE-only | located (any CWE) | clean runs with a false signal | findings per clean run | extras per injected run |
|---|---|---|---|---|---|---|---|
| raw | 10/12 (0.55-0.95) | 8/12 (0.39-0.86) | 11/12 (0.65-0.99) | 8/12 | 3/3 | 2.00 | 1.00 |
| grounded | 11/12 (0.65-0.99) | 11/12 (0.65-0.99) | 11/12 (0.65-0.99) | 11/12 | 3/3 | 2.00 | 0.92 |
| verified | 11/12 (0.65-0.99) | 11/12 (0.65-0.99) | 11/12 (0.65-0.99) | 11/12 | 3/3 | 2.00 | 0.42 |
| final | 11/12 (0.65-0.99) | 11/12 (0.65-0.99) | 11/12 (0.65-0.99) | 11/12 | 3/3 | 2.00 | 0.42 |

Final stage per case (strict / function, of seeds):

| case | strict | function |
|---|---|---|
| blog/CWE-330 | 2/3 | 2/3 |
| blog/CWE-601 | 3/3 | 3/3 |
| blog/CWE-79 | 3/3 | 3/3 |
| blog/CWE-915 | 3/3 | 3/3 |

Cost: 44 LLM calls, 72265 prompt / 4696 generated tokens, 180 s model time, 0 error(s).
