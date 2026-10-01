# Blue probe: gemma4:12b

- git `89a10c7`, Ollama 0.35.0, digest `6114515d63c1`, 11.9B Q4_K_M; T=0.7, seeds 1-3, num_ctx 8192, thinking=False, schema guard <= 8 findings and 300 chars per text field
- Now drawing from 'AC Power'; at the end: System-wide memory free percentage: 14%
- Bandit baseline (eval/baselines/bandit.json): 1 of 3 found (CWE-89 only), no false signal on the clean app.

| Case | strict hit | location only | CWE only | findings (mean) | JSON valid |
|---|---|---|---|---|---|
| clean (false signal in an injected region) | 3/3 | - | - | 1 | 3/3 |
| CWE-89 | 3/3 | 3/3 | 3/3 | 1 | 3/3 |
| CWE-639 | 0/3 | 1/3 | 3/3 | 1.3 | 3/3 |
| CWE-22 | 3/3 | 3/3 | 3/3 | 1.3 | 3/3 |

- Recall strict 6/9 (Wilson 95% 0.35-0.88); location only 7/9; CWE only 9/9
- False signal on the clean app: 3/3 runs; 1 findings per clean run
- JSON valid 12/12; evidence found in the source 14/14 findings
- Speed 8.4 tok/s decode and 79.8 tok/s prefill (first run of each case; medians), 21.05 s per generation (median); first load 7.37 s; resident {'size_gb': 1.39, 'vram_gb': 1.39}

Examples to look at (case, run in result.json):
- miss CWE-639#0
- miss CWE-639#1
- miss CWE-639#2
- false signal clean#0 ['CWE-22']
- false signal clean#1 ['CWE-22']

Small sample (3 runs x 4 cases): a direction, not proof. The injected region is the only ground truth,
so extra findings are not necessarily wrong. Generated text only; nothing was executed.
