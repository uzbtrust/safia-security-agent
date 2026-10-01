# Blue probe: qwen2.5-coder:7b

- git `f562f8d`, digest `dae161e27b0e`, 7.6B Q4_K_M; T=0.7, seeds 1-3, num_ctx 8192, thinking=None
- Now drawing from 'Battery Power'; at the end: System-wide memory free percentage: 28%
- Bandit baseline (eval/baselines/bandit.json): 1 of 3 found (CWE-89 only), no false signal on the clean app.

| Case | strict hit | location only | CWE only | findings (mean) | JSON valid |
|---|---|---|---|---|---|
| clean (false signal in an injected region) | 3/3 | - | - | 1.3 | 3/3 |
| CWE-89 | 2/3 | 3/3 | 2/3 | 1 | 3/3 |
| CWE-639 | 0/3 | 2/3 | 0/3 | 2 | 3/3 |
| CWE-22 | 1/3 | 3/3 | 1/3 | 2 | 3/3 |

- Recall strict 3/9 (Wilson 95% 0.12-0.65); location only 8/9; CWE only 3/9
- False signal on the clean app: 3/3 runs; 1.33 findings per clean run
- JSON valid 12/12; evidence found in the source 12/19 findings
- Speed 20.5 tok/s decode (median), 10.25 s per generation (median); resident {'size_gb': 5.34, 'vram_gb': 5.34}

Examples to look at (case, run in result.json):
- miss CWE-89#0
- miss CWE-639#0
- miss CWE-639#1
- false signal clean#0 ['CWE-89']
- false signal clean#1 ['CWE-89']

Small sample (3 runs x 4 cases): a direction, not proof. The injected region is the only ground truth,
so extra findings are not necessarily wrong. Generated text only; nothing was executed.
