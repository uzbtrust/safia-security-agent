# Blue probe comparison (3 local models)

Same prompts and scoring for every model: T=0.7, seeds [1, 2, 3], num_ctx 8192, +-5 lines, 4 cases (clean + 3 injected), nothing executed. Bandit is the static baseline (strict recall = CWE found at the region).
Rows for runs made before load/prefill timing was added show '-' there. Quality columns are comparable.

| Model | strict recall (95% CI) | location only | CWE only | strict per CWE 89/639/22 | false signal on clean | JSON valid | evidence in source |
|---|---|---|---|---|---|---|---|
| gemma4:12b | 6/9 (0.35-0.88) | 7/9 | 9/9 | 3/0/3 of 3 each | 3/3 runs (1 findings) | 12/12 | 14/14 |
| qwen2.5-coder:7b | 3/9 (0.12-0.65) | 8/9 | 3/9 | 2/0/1 of 3 each | 3/3 runs (1.33 findings) | 12/12 | 12/19 |
| qwen3.5:9b | 5/9 (0.27-0.81) | 6/9 | 5/9 | 3/0/2 of 3 each | 3/3 runs (2.33 findings) | 12/12 | 21/22 |
| Bandit (baseline) | 1/3 | - | - | - | 0/3 | - | - |

| Model | Ollama | decode tok/s | prefill tok/s | first load s | s per generation | resident | power | thinking |
|---|---|---|---|---|---|---|---|---|
| gemma4:12b | 0.35.0 | 8.4 | 79.8 | 7.4 | 21.1 | 1.39 GB | AC Power | False |
| qwen2.5-coder:7b | - | 20.5 | - | - | 10.2 | 5.34 GB | Battery Power | None |
| qwen3.5:9b | 0.35.0 | 16.7 | 154.2 | 5.1 | 16.4 | 5.77 GB | AC Power | False |

- gemma4:12b: protocol v2, schema guard <= 8 findings and 300 chars per text field
- qwen2.5-coder:7b: protocol v1, no length guard
- qwen3.5:9b: protocol v2, schema guard <= 8 findings and 300 chars per text field

- Highest strict recall: gemma4:12b (6/9).
- Fewest false signals on the clean app: gemma4:12b (3/3 runs).
- Samples are tiny (9 injected runs per model): a direction, not proof. The injected region is the only ground truth, so extra findings are not necessarily wrong.

## Memory measured with vm_stat (model loaded, num_ctx 8192, apps closed; memory.json)
| | wired | system free | `ollama ps` says |
|---|---|---|---|
| no model | 2.27 GB | 81% | - |
| qwen3.5:9b | 9.08 GB (+6.8) | 28% | 5.8 GB |
| gemma4:12b | 13.03 GB (+10.8) | 8% | 1.1 GB (not the real footprint) |

## Post-hoc, outside the scored protocol
IDOR is a missing check, and the pre-set region (the removed lines +-5) misses a finding on the function's `def` line (41) by one line. gemma4:12b reported (41, CWE-285) in 3/3 runs. Counting the whole function (lines 41-48) with the same CWE family: gemma4:12b 3/3 on IDOR (9/9 in total), qwen3.5:9b 0/3 (5/9), qwen2.5-coder:7b 0/3 (3/9). The tables keep the pre-set scoring; the pre-set CWE-only column already shows the same gap.

## Reading (n=9 per model: a direction, not proof)
- gemma4:12b is the better detector: right CWE in 9/9 runs (qwen3.5:9b 5/9), the only model that finds the IDOR class, 1 finding per clean run (2.3 and 1.3), every evidence quote exists in the source (14/14). Price: 8.4 tok/s (qwen3.5:9b 16.7), +10.8 GB wired (8% of RAM free, so no other apps), 8.0 GB on disk.
- qwen3.5:9b is the practical model: twice as fast, +6.8 GB wired. Strict recall 5/9 against 6/9 has overlapping intervals, but it never names the IDOR class and raises a SQL injection alarm on the clean app in 3/3 runs.
- All three raise a false signal on the clean app in 3/3 runs (Bandit 0/3). None can be trusted without the verifier: the model investigates, it does not detect alone.
- Not tested: thinking on, more seeds, other prompts. qwen2.5-coder:7b ran under protocol v1, on battery, with Ollama 0.24.0.
- First attempt: qwen3.5:9b gave invalid JSON in 2 of 2 generations (it reasons inside `explanation` until the 1500-token cap). The schema guard was added for every model before any result was kept.

Pick: gemma4:12b for the evaluation runs (other apps closed); keep qwen3.5:9b as the fast model for prompt and agent iteration while disk allows.
