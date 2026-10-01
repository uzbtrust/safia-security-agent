# Smoke test: qwen2.5-coder:7b on Ollama 0.24.0

- git `cf0495d`, num_ctx 8192, digest `dae161e27b0e`, 7.6B Q4_K_M, file 4.68 GB
- power: Now drawing from 'AC Power'; at start: System-wide memory free percentage: 53%; swap total = 2048.00M  used = 1170.81M  free = 877.19M  (encrypted); free disk 34.0 GB

| Check | Result |
|---|---|
| Cold load | 23.45 s |
| Decode speed (red samples) | 20.2 tok/s median, 18.5-20.8 |
| Prefill speed | 199.0 tok/s at 2040 tokens; 167.6 tok/s at 8192 tokens |
| Resident | 5.34 GB, 5.34 GB on GPU, ctx 8192 |
| Native `format` (red schema), n=3 | valid JSON 3, schema ok 3, `old` found once 1, marker present 3 |
| `/v1` `response_format` json_schema, n=3 | conforms 3; usage present: yes |
| Prompt longer than context (~10649 tokens, ctx 8192) | native prompt_eval_count 8192, found A/B: no/no; `/v1` usage {'prompt_tokens': 8192, 'completion_tokens': 15, 'total_tokens': 8207}, found A/B: no/no |
| Determinism T=0 | identical across seeds 1-3: yes |
| Determinism T=0.8 | 3 distinct outputs of 3 seeds; seed 1 repeated identical: yes |

Prefill is only meaningful for calls with a cold prompt prefix; repeated red prompts reuse the cache.
Red samples are stored in result.json for inspection. They were never executed.
