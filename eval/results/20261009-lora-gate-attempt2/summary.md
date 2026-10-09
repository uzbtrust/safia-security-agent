# LoRA gate, second attempt (2026-10-09): base weights passed, stopped at check (b) by a chat-template assumption in scripts/lora_train.py

Phase: `bash scripts/vast_lora.sh gate` again, with the one environment fix the user approved and no change to any script: the venv was created beforehand and `brotli>=1.2` installed into it (attempt 1 stopped at check (a) on Brotli 1.1.0, see `../20261009-lora-gate/summary.md`). Base `google/gemma-4-12B-it`. No retry after this GATE FAILED.
Machine: Vast.ai instance 55028737, 1x NVIDIA A40 (46068 MiB usable, driver 595.91.07; the cheaper A6000 offer was no longer available), image `pytorch/pytorch:2.8.0-cuda12.6-cudnn9-runtime`, torch 2.8.0+cu126, transformers 5.19.0, peft 0.21.2, bitsandbytes 0.50.2, Ollama 0.40.2, repo commit a92ab44. Rented 18:28:59, destroyed 18:43:53 (Tashkent time, 15 min) at $0.508/h; credit used $0.177 (both attempts $0.301; limit for the phase $1.5).

## Result
| check | result |
|---|---|
| (a) base weights download | passed (23.9 GB in 49 s with the Brotli fix) |
| (b) 8 QLoRA steps on the longest examples | **FAILED** (`GATE FAILED: smoke_training`, exit 4): AssertionError at `scripts/lora_train.py` line 53 in `encode`, before the first training step |
| (c) merge, Ollama import, scan | not run |
| (d) conversion check on RealVuln dev | not run |
`gate_report.json` does not exist. Not measured: peak GPU memory, tokens/s, estimated training hours, conversion F3 of official against converted.

## Why check (b) failed (a code assumption, not infrastructure)
`encode` renders the prompt with `add_generation_prompt=True` and the whole conversation without it, then asserts that the prompt tokens are a prefix of the full tokens. The Gemma 4 chat template breaks this: the generation prompt ends with an empty thinking channel, `<|turn>model\n<|channel>thought\n<channel|>`, while a finished assistant turn is rendered as `<|turn>model\n{"findings": []}<turn|>\n` with no channel. On the first record of `train.jsonl` both renderings are identical up to token 1856 (`model\n`); then the prompt continues with `<|channel>`, `thought`, `\n`, `<channel|>` and the full conversation with the answer (`template_probe.py`). The training text should therefore be built as generation prompt + answer + `<turn|>\n` (1867 tokens on that record, same ending as the full rendering), which is also what the model sees at inference with thinking off; this still has to be confirmed against Ollama's own prompt for gemma4 before any training. The script was not changed and the gate was not repeated (instruction: no retry after GATE FAILED).

## Side measurements (not gate results; tokenizer only, no GPU; `len_stats.py`)
Sequence = generation prompt + answer + `<turn|>`: 402 records, 1,341,793 tokens in total (mean 3338, median 3068, min 1845, max 8937); 1 record is longer than the 8192 limit (401 kept, 1,332,856 tokens). The 8 longest kept records are 7002, 6656, 6400, 6240, 5995, 5921, 5793 and 5767 tokens, so the smoke test would not reach the full 8192 tokens. Loss targets (answer tokens) are 42,788, about 3% of all tokens. The pre-registered estimate was about 1.16M tokens.
