# Hardware and local serving (LOCAL machine)

Measured on 2026-10-01 unless a line says *estimate* or *pending*. There are no performance numbers here yet: no model has been loaded (see "Not measured yet").

## Machine

| | |
|---|---|
| Model | MacBook Air (Mac16,13), Apple M4, fanless |
| CPU / GPU | 10 CPU cores (4 performance + 6 efficiency), 10 GPU cores, Metal 4 |
| Memory | 16 GB unified |
| OS | macOS 27.0 (build 26A428), arm64 |
| Present | Python 3.13.15, uv 0.9.21, git 2.52.0, Ollama 0.24.0 (Homebrew) |
| Not installed | Docker (needed from T3.2); Semgrep and Bandit (C0 runs on the cloud side) |

## Memory budget

- Ollama reports **11.8 GiB** of Metal memory available (server log, `inference compute`). Weights, KV cache and compute buffers have to fit in it, otherwise layers spill to the CPU and decoding slows down.
- Memory pressure swings with what is open. At the first reading (about 02:40) swap was 3.3 of 4.0 GB used and 54% of memory was free; at 03:04 swap was empty and 66% was free. Check `memory_pressure` and `sysctl vm.swapusage` before a timed run and close heavy apps.

## Disk budget

- Volume: 228 GiB. Free space moved from **15.3 GB** (about 02:40) to **23.7 GB** (03:04), both `diskutil` container free space. The swap files (about 4 GB) went away once memory pressure dropped, and the used space of the data volume also fell by 5 GiB (cause unknown). The number is not stable: plan with the lower one and re-check right before every pull.
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

## Which models fit

Download sizes come from the Ollama registry manifests (sum of layers). The verdict is an *estimate* from file size against the 11.8 GiB Metal budget and the disk budget. It becomes a fact only after a real load (`ollama ps`).

| Tag | Download | Verdict |
|---|---|---|
| `qwen2.5-coder:7b` | 4.68 GB | fits comfortably |
| `qwen3:8b` | 5.23 GB | fits comfortably |
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

## Not measured yet

Prefill and decode tok/s, cold-load time, resident memory per model (`ollama ps`), JSON-schema behavior through `/v1`, determinism, and what happens to prompts longer than the context window. These need a model on disk (T0.3 smoke test, pending).
