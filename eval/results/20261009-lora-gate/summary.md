# LoRA gate on a rented GPU (2026-10-09): stopped at check (a) by an environment fault

Phase: `bash scripts/vast_lora.sh gate` only. No training, no test half. Base checkpoint, confirmed by the user: `google/gemma-4-12B-it` (official Google repo, Apache 2.0, not gated; 11.96B BF16 parameters, architecture Gemma4UnifiedForConditionalGeneration, context 262144). The Ollama page of `gemma4:12b` shows the same architecture, 11.9B parameters, Apache 2.0 and digest 6114515d63c1. Not chosen: `google/gemma-4-12B` (pretrained), and the QAT, assistant, GGUF and w4a16 variants.
Machine: Vast.ai instance 55024411, 1x NVIDIA RTX A6000 (49140 MiB, driver 570.133.20), image `pytorch/pytorch:2.8.0-cuda12.6-cudnn9-runtime`, torch 2.8.0+cu126, transformers 5.19.0, peft 0.21.2, bitsandbytes 0.50.2, Ollama 0.40.2, repo commit 5e23891. Rented 18:00:27, destroyed 18:17:42 (Tashkent time, 17 min) at $0.442/h; credit used $0.124 (limit for this phase $1.5).

## Result
| check | result |
|---|---|
| (a) base weights download | **FAILED** (`GATE FAILED: base_weights`, exit 4) |
| (b) 8 QLoRA steps at 8192 tokens | not run |
| (c) merge, Ollama import, scan | not run |
| (d) conversion check on RealVuln dev | not run |
`gate_report.json` does not exist. None of the numbers the gate exists to measure (peak GPU memory, tokens/s, estimated training hours, examples dropped for length, conversion F3 of official against converted) were measured.

## What did run
- Tests on the instance: 84 passed, 1 skipped (66 s). `gemma4:12b` pulled into Ollama at about 119 MB/s.
- The training set rebuilt on the instance equals the pre-registered one: 402 examples (201 positive, 50 trap, 151 negative), 442 target findings, 1041 candidate chunks, sha256 3055e51df897... (3 labels of realvuln-vulnpy could not be quoted).
- `model.safetensors` downloaded completely: 23,919,549,408 bytes in about 3 minutes (about 131 MB/s through hf-xet), plus `tokenizer.json` and `generation_config.json`.

## Why check (a) failed
The remaining small files (`config.json`, `tokenizer_config.json`, ...) are fetched over plain HTTP by `huggingface_hub` 2.2.0 (client `httpx2` 2.13.1). With the image's system `Brotli 1.1.0` the response decoder raises `TypeError: process() takes no keyword arguments` (`httpx2` passes `output_buffer_limit`, which Brotli 1.2 accepts). This is an install-environment fault, not a feasibility result for LoRA.
Reproduced on the instance after the gate had stopped (`brotli_probe.py`, the 7 small files of the repo): with HF_TOKEN set and Brotli 1.1.0, 6 of 7 failed with the same error (`generation_config.json`, the one small file the gate had fetched, was fine); after `pip install "brotli>=1.2"` inside the venv all 7 succeeded. Requests without a token did not fail (the reason was not investigated), so the fault only shows with a token.
The gate script was not changed and the gate was not repeated (instruction: no retry after GATE FAILED). A second attempt would need `brotli>=1.2` installed before the download (for example in the setup `pip install` line of `scripts/vast_lora.sh`), which is the cloud's file.
