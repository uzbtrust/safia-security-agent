# Hardware and local serving (LOCAL machine)

Measured on 2026-10-01 unless a line says *estimate* or *pending*. There are no performance numbers here yet: no model has been loaded (see "Not measured yet").

## Machine

| | |
|---|---|
| Model | MacBook Air (Mac16,13), Apple M4, fanless |
| CPU / GPU | 10 CPU cores (4 performance + 6 efficiency), 10 GPU cores, Metal 4 |
| Memory | 16 GB unified |
| OS | macOS 27.0 (build 26A428), arm64 |
| Present | Python 3.13.15, uv 0.9.21, git 2.52.0, Ollama 0.35.0 (Homebrew; 0.24.0 until 2026-10-01, see "Serving configuration") |
| Not installed | Docker (needed from T3.2); Semgrep and Bandit (C0 runs on the cloud side) |

## Memory budget

- Ollama reports **11.8 GiB** of Metal memory available (server log, `inference compute`). Weights, KV cache and compute buffers have to fit in it, otherwise layers spill to the CPU and decoding slows down.
- `ollama ps` can under-report: for `gemma4:12b` it shows 1.1-1.4 GB while `vm_stat` ("Pages wired down") rises by 10.8 GB. Measure the wired pages before and after loading a model.
- Memory pressure swings with what is open. At the first reading (about 02:40) swap was 3.3 of 4.0 GB used and 54% of memory was free; at 03:04 swap was empty and 66% was free. Check `memory_pressure` and `sysctl vm.swapusage` before a timed run and close heavy apps.

## Disk budget

- Volume: 228 GiB. Free space moved from **15.3 GB** (about 02:40) to **23.7 GB** (03:04), both `diskutil` container free space. The swap files (about 4 GB) went away once memory pressure dropped, and the used space of the data volume also fell by 5 GiB (cause unknown). The number is not stable: plan with the lower one and re-check right before every pull. Later readings: 38.7 GB at 13:09, and 34.0 GB after `qwen2.5-coder:7b` (4.68 GB) was pulled.
- Swap files live on this volume, so free disk is also runtime headroom. Keep at least 5 GB free.

## Serving configuration

`configs/local/ollama.env`, started with `configs/local/serve-ollama.sh`. Every setting is part of the experiment config. The effective values were read back from the server log.

| Setting | Value | Why |
|---|---|---|
| `OLLAMA_HOST` | `127.0.0.1:11434` | loopback only (checked with `lsof`) |
| `OLLAMA_NO_CLOUD` | `1` | the product path stays fully local; the log says `Ollama cloud disabled: true` |
| `OLLAMA_MAX_LOADED_MODELS`, `OLLAMA_NUM_PARALLEL` | `1`, `1` | one resident model; the KV cache is allocated per slot |
| `OLLAMA_FLASH_ATTENTION` | `1` | smaller KV cache, faster long-context prefill |
| `OLLAMA_CONTEXT_LENGTH` | `8192` | Ollama's own default here is 4096 (derived from the Metal memory size; server log) |
| `OLLAMA_KEEP_ALIVE` | `10m` | stay loaded during a run, release memory afterwards |

**Ollama version.** 0.24.0 until 2026-10-01 (the smoke test and the baseline `qwen2.5-coder:7b` probe ran on it), 0.35.0 afterwards (the `qwen3.5:9b` and `gemma4:12b` probes; each result records the version). The upgrade was needed because the registry refuses `gemma4:12b` to older clients (HTTP 412) and Ollama's release notes say 12B support arrived in v0.30.3. `brew upgrade ollama` also moved `mlx` 0.31.2 to 0.32.1, `mlx-c` 0.6.0_2 to 0.6.0_4, `openssl@3` 3.6.4 to 3.6.5, `readline`, `xz` and `ca-certificates`, and added `python@3.14`. The old versions were kept on disk (cleanup was switched off), so the previous Ollama can still be run from its Cellar directory.

## Which models fit

Download sizes come from the Ollama registry manifests (sum of layers). The verdict is an *estimate* from file size against the 11.8 GiB Metal budget and the disk budget. It becomes a fact only after a real load (`ollama ps`).

| Tag | Download | Verdict |
|---|---|---|
| `qwen2.5-coder:7b` | 4.68 GB | fits: 5.34 GB resident, all on the GPU at 8192 context (measured, see below) |
| `qwen3:8b` | 5.23 GB | fits comfortably; not probed |
| `qwen3.5:9b` | 6.59 GB | fits: +6.8 GB wired, 28% of RAM free with it loaded (measured) |
| `gemma4:12b` | 8.02 GB | fits only with other apps closed: +10.8 GB wired, 8% of RAM free (measured) |
| `gemma4:latest` | 6.58 GB | fits; not evaluated yet |
| `qwen2.5-coder:14b` | 8.99 GB | marginal: weights plus KV cache at 8192 tokens take most of the Metal budget; test before relying on it |
| `qwen3:14b`, `phi4:14b`, `deepseek-coder-v2:16b` | 9.28, 9.05, 8.91 GB | marginal, same as above |
| `gpt-oss:20b` | 13.79 GB | does not fit: the weights alone exceed the Metal budget |
| `devstral:latest` | 14.33 GB | does not fit |
| `qwen3-coder:30b` | 18.56 GB | does not fit |
| `qwen3-coder-next:latest` | 51.74 GB | does not fit |

`gpt-oss-20b`, Devstral and Qwen3-Coder-Next were the stretch candidates in `docs/PLAN.md` section 6. They could only serve as references on other hardware.

KV cache, calculated from the published architecture and not measured: about 57 KB per token for Qwen2.5-Coder-7B (0.47 GB at 8192 tokens) and about 197 KB per token for the 14B (1.6 GB at 8192 tokens).

## Storage policy

- At most two models on disk at a time. Bake-offs are sequential: pull, measure, `ollama rm`. Tag, digest, size and quantization go into `configs/local/models.yaml` and each `result.json`, so a run stays reproducible after the weights are deleted.
- Models never live on iCloud or Google Drive. Inference needs local random access to the weights, and Drive's streaming mode caches the whole file locally anyway. Re-pulling from the Ollama registry is faster than restoring from Drive, so registry models are not backed up.
- Cloud drives are for artifacts that cannot be re-downloaded: LoRA adapters and merged GGUFs, compressed LLM response caches and replays, the demo video. Tier-3 training runs on Colab with Drive as the dataset and checkpoint store, so full-precision weights never touch this disk.
- Drive for desktop must be in "Stream files" mode. In "Mirror" mode, archived files would also occupy local disk.
- Docker (T3.2): none installed. A full Docker Desktop install plus images takes a large share of the free space, so the runtime choice (lighter runtime or external disk) is decided at T3.2 after measuring.

## Operational notes

- Use AC power for timing and eval runs. The Air has no fan, so sustained load throttles and tok/s depends on the thermal state. Note the power source in each `summary.md`.
- Long runs: lid open, AC power, `caffeinate -i <command>`.

## Measured: qwen2.5-coder:7b (Q4_K_M, 7.6B)

From `configs/local/smoke_test.py`. Raw data and the three red samples are in `eval/results/20261001-smoke-ollama-qwen2.5-coder_7b/`. AC power, num_ctx 8192, git `cf0495d`. At the start 53% of memory was free and swap was 1.2 of 2.0 GB used.

| | |
|---|---|
| Cold load | 23.5 s (first load after the pull) |
| Decode | 20.2 tok/s median (18.5 to 20.8, n=3) |
| Prefill | 199 tok/s at 2040 tokens, 168 tok/s at 8192 tokens |
| Resident | 5.34 GB, all of it on the GPU |
| Disk | 4.68 GB; free space went from 38.7 to 34.0 GB |
| Structured output | native `format` and `/v1` `response_format` (json_schema) both followed the schema (3 of 3 each) |
| Longer than the context | Ollama truncates silently: the client gets no error, the server log has a WARN (`truncating input prompt limit=8192 prompt=10865`), and `/v1` `usage.prompt_tokens` comes back as exactly 8192 |
| Determinism | at T=0 seeds 1 to 3 gave identical output; at T=0.8 they differ and a repeated seed reproduces |

Small samples: n=3 per structured-output check, one prompt for determinism. Direction, not proof. Still not measured: other models, sustained load under thermal throttling, and the 14B.

## Measured: the Blue probe models (Ollama 0.35.0, AC power, apps closed)

From `configs/local/blue_probe.py`; the table and the reading are in `eval/results/20261001-blue-probe-comparison/summary.md`. Thinking off, num_ctx 8192.

| | qwen3.5:9b | gemma4:12b |
|---|---|---|
| Decode | 16.7 tok/s (16.4 to 17.0, steady) | 8.4 tok/s (7.4 to 10.0) |
| Prefill (first run of each case) | 154 tok/s | 80 tok/s |
| First load | 5.1 s | 7.4 s (the files were in the page cache, so a colder load will be slower) |
| Per generation (median) | 16.4 s | 21.1 s |
| Wired memory added | 6.8 GB | 10.8 GB |
| System free memory with it loaded | 28% | 8% |

The prefill figure of a repeated prompt is not a speed: the prompt cache answers it in a fraction of a second and the run then reports thousands of tok/s. Only the first run of each case is used.

## Measured: Blue v0 on the dev gym (Ollama 0.35.0, AC power, 2026-10-07)
`safia-sec eval-gym --apps shop bank --seeds 1 2 3`: 27 runs per model, detector and verifier on the same model, prompts of about 1.1-1.6k tokens.

| Model | LLM calls | model s per call | model s per run | prompt / generated tokens per call |
|---|---|---|---|---|
| gemma4:12b | 61 (9 replayed from the cache) | 28.6 | 64.7 | 1339 / 121 |
| qwen3.5:9b | 68 | 18.3 | 46.1 | 1252 / 133 |

End to end qwen3.5:9b is 1.4x faster per run (1.56x per call), not the 2x of the decode speed. The Gemma run pushed swap from 0.6 GB to 9.9 GB and free disk from 35.7 GB to 26.0 GB (free memory about 11%); the Qwen run reached 6.8 GB of swap and 30.3 GB of free disk. After `ollama stop` swap fell to 2.1 GB and free disk went back to 34.6 GB. The first Gemma attempt on 2026-10-01 took the disk from 19.3 GB to 15.0 GB in two minutes, so a Gemma run needs about 30 GB free; with 35.7 GB it finished without trouble.
