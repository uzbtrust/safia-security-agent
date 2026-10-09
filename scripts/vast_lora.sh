#!/usr/bin/env bash
# LoRA experiment (docs/EXPERIMENTS.md, "LoRA experiment") on one rented NVIDIA GPU with 48 GB, in two phases.
#
#   HF_TOKEN=<read-only token> BASE_HF=<official repo id> nohup bash scripts/vast_lora.sh gate  > lora_gate.log  2>&1 &
#   HF_TOKEN=<read-only token> BASE_HF=<official repo id> nohup bash scripts/vast_lora.sh train > lora_train.log 2>&1 &
# The token lives only in the environment; it is never printed or written to disk.
#
# both  : template alignment: the training prompt has Ollama's token count for the same message (see the script).
# gate  (feasibility, no training): (a) base weights download, (b) 8 QLoRA steps on the 8 longest examples at the
#       full length (peak memory, tokens/s, estimated training time), (c) a merged smoke adapter imports into Ollama
#       and the scanner gets valid JSON from it, (d) conversion check: the base model taken through the same import
#       path scores within 0.05 F3 of the official Ollama model on RealVuln dev. Report: gate_report.json.
# train (only after a passed gate and a written plan): full training, merge, import base and LoRA the same way,
#       RealVuln dev for both, then the test half once (RealVuln test + gym blog) for both.
# Exit codes: 2 bad usage, 4 a gate check failed, 5 training-set hash differs. Last line "GATE DONE" / "ALL DONE".
set -euo pipefail

PHASE=${1:-}
[ "$PHASE" = gate ] || [ "$PHASE" = train ] || { echo "usage: bash scripts/vast_lora.sh gate|train"; exit 2; }
ROOT=$(pwd)
MODEL=gemma4:12b
DATA_SHA=3055e51df8973c1b12d6c920f39e03d923b79d954f1c79d3e7172315f34a9161   # pre-registered training set
RUN=$(date +%Y%m%d-%H%M)-lora-$PHASE   # unique per run: never writes into an earlier attempt's folder
OUT=$ROOT/eval/results/$RUN
W=$ROOT/.cache/lora
PY=$ROOT/.venv/bin/python
RV=$ROOT/.cache/realvuln
: "${BASE_HF:?set BASE_HF to the official Hugging Face repo id of the base model}"
: "${HF_TOKEN:?set HF_TOKEN (read-only) in the environment}"

say() { echo "[$(date +%H:%M:%S)] $*"; }
check() {  # check <name> <command...>: records pass/fail; stops the run on failure
  local name=$1; shift
  if "$@"; then echo "{\"check\": \"$name\", \"pass\": true}" >> "$OUT/gate.jsonl"; say "PASS $name"
  else echo "{\"check\": \"$name\", \"pass\": false}" >> "$OUT/gate.jsonl"; say "GATE FAILED: $name"; finish 4; fi
}
finish() {  # pack whatever exists, then exit with the given code
  tar czf "$ROOT/lora_$PHASE.tgz" -C "$ROOT" "eval/results/$RUN" 2>/dev/null || true
  exit "$1"
}
cli() { PYTHONPATH=src "$PY" -m safia_sec.cli "$@"; }
import_model() {  # import_model <ollama name> <hf dir>: the same import path for every arm
  local name=$1 dir=$2
  { echo "FROM $dir"; printf 'TEMPLATE """%s"""\n' "$(ollama show "$MODEL" --template)"
    ollama show "$MODEL" --parameters | sed -n 's/^\([a-z_]*\)  *\(.*\)$/PARAMETER \1 \2/p'; } > "$W/Modelfile.$name"
  ollama create "$name" --quantize q4_K_M -f "$W/Modelfile.$name"
}
f3_of() { "$PY" -c "import sys; sys.path.insert(0, 'scripts'); from freeze_decide import totals; print(totals('$1')['f3'])"; }

mkdir -p "$OUT" "$W"
: > "$OUT/gate.jsonl"

# ---------------------------------------------------------------- setup (both phases)
say "setup ($PHASE)"
git config --global --add safe.directory '*'
command -v git >/dev/null && command -v curl >/dev/null && python3 -c "import venv" 2>/dev/null \
  || { apt-get update -qq && apt-get install -y -qq git curl python3-venv >/dev/null; }
[ -x "$PY" ] || python3 -m venv --system-site-packages .venv   # reuse the image's CUDA build of torch
# brotli>=1.2: huggingface_hub's HTTP client passes a keyword that Brotli 1.1 rejects (gate attempt 1, 2026-10-09)
"$PY" -m pip install -q "flask>=3" "pytest>=8" "bandit>=1.7" transformers peft bitsandbytes accelerate \
  huggingface_hub safetensors sentencepiece "brotli>=1.2"
"$PY" -c "import torch; assert torch.cuda.is_available(), 'no CUDA'"
PYTHONPATH=src "$PY" -m pytest -q -x 2>&1 | tail -2
command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh
OLLAMA_HOST=127.0.0.1:11434 nohup ollama serve > "$ROOT/ollama_$PHASE.log" 2>&1 &
until curl -sf http://127.0.0.1:11434/api/version >/dev/null; do sleep 1; done
ollama pull "$MODEL"
{ echo "phase $PHASE"; echo "model $MODEL $(ollama list | awk -v m="$MODEL" '$1==m {print $2}')"; echo "base $BASE_HF"
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
  echo "ollama $(ollama --version 2>&1 | tail -1)"; echo "repo $(git rev-parse HEAD)"
  "$PY" -c "import torch, transformers, peft, bitsandbytes as b; print('torch', torch.__version__, 'transformers', transformers.__version__, 'peft', peft.__version__, 'bitsandbytes', b.__version__)"
} | tee "$OUT/machine.txt"

say "training data (must equal the pre-registered set)"
PYTHONPATH=src "$PY" scripts/lora_build_data.py --dest "$W"
cp "$W/summary.json" "$OUT/data_summary.json"
SHA=$("$PY" -c "import json; print(json.load(open('$W/summary.json'))['sha256'])")
[ "$SHA" = "$DATA_SHA" ] || { say "training set hash $SHA differs from the pre-registered one"; finish 5; }

say "base weights"
check base_weights "$PY" -c "
import os; from huggingface_hub import snapshot_download
snapshot_download('$BASE_HF', local_dir='$W/base', token=os.environ['HF_TOKEN'])"
PYTHONPATH=src "$PY" scripts/realvuln_fetch.py --split dev --dest "$RV"
say "template alignment: training prompt vs the prompt Ollama renders (first query of the model)"
check template_alignment env PYTHONPATH=src "$PY" scripts/lora_template_check.py --base "$W/base" \
  --data "$W/train.jsonl" --out "$OUT/template_check.json"

# ---------------------------------------------------------------- gate
if [ "$PHASE" = gate ]; then
  say "gate b: 8 QLoRA steps on the longest examples"
  check smoke_training env PYTHONPATH=src "$PY" scripts/lora_train.py train --base "$W/base" --data "$W/train.jsonl" \
    --out "$W/smoke_adapter" --smoke
  cp "$W/smoke_adapter/train_meta.json" "$OUT/smoke_train_meta.json"

  say "gate c: merge, import into Ollama, scan"
  smoke_export() {
    PYTHONPATH=src "$PY" scripts/lora_train.py merge --base "$W/base" --adapter "$W/smoke_adapter" --out "$W/smoke_merged" &&
    import_model safia-smoke "$W/smoke_merged" &&
    { cli scan gym_apps/shop --model safia-smoke --no-bandit --out "$W/smoke_scan" || true; } &&
    "$PY" -c "import json; m = json.load(open('$W/smoke_scan/report.json'))['meta']; assert m['llm_calls'] > 0 and not m['errors'], m['errors']"
  }
  check export_and_scan smoke_export
  ollama rm safia-smoke; rm -rf "$W/smoke_merged" "$W/smoke_adapter"

  say "gate d: conversion check on RealVuln dev (official vs base through our import path)"
  import_model safia-base-conv "$W/base"
  cli eval-realvuln --split dev --data "$RV" --model "$MODEL" --out "$OUT/realvuln-dev-official"
  cli eval-realvuln --split dev --data "$RV" --model safia-base-conv --out "$OUT/realvuln-dev-base-conv"
  OFF=$(f3_of "$OUT/realvuln-dev-official"); CONV=$(f3_of "$OUT/realvuln-dev-base-conv")
  echo "official $OFF, base-converted $CONV (allowed gap 0.05)" | tee "$OUT/conversion_check.txt"
  check conversion "$PY" -c "import sys; sys.exit(abs($OFF - $CONV) > 0.05)"

  "$PY" - "$OUT" <<'EOF'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
meta = json.loads((out / "smoke_train_meta.json").read_text())
report = {"checks": [json.loads(l) for l in (out / "gate.jsonl").read_text().splitlines()],
          "peak_gpu_memory_gb": meta["peak_gpu_memory_gb"], "tokens_per_second": meta["tokens_per_second"],
          "full_set_tokens": meta["full_set_tokens"], "dropped_too_long": meta["dropped_too_long"],
          "estimated_full_training_hours": meta["estimated_full_training_hours"],
          "conversion_check": (out / "conversion_check.txt").read_text().strip(),
          "machine": (out / "machine.txt").read_text()}
(out / "gate_report.json").write_text(json.dumps(report, indent=1) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "machine"}, indent=1))
EOF
  say "gate passed: write the training plan before running 'train'"
  tar czf "$ROOT/lora_gate.tgz" -C "$ROOT" "eval/results/$RUN"
  echo "GATE DONE"
  exit 0
fi

# ---------------------------------------------------------------- train (after a passed gate)
say "training"
PYTHONPATH=src "$PY" scripts/lora_train.py train --base "$W/base" --data "$W/train.jsonl" --out "$W/adapter"
cp "$W/adapter/train_meta.json" "$W/adapter/loss.jsonl" "$W/adapter/adapter_config.json" "$OUT/"
PYTHONPATH=src "$PY" scripts/lora_train.py merge --base "$W/base" --adapter "$W/adapter" --out "$W/merged"
import_model safia-lora "$W/merged"
import_model safia-base-conv "$W/base"
rm -rf "$W/merged"

say "RealVuln dev: base-converted and LoRA (same machine)"
for m in safia-base-conv safia-lora; do
  cli eval-realvuln --split dev --data "$RV" --model "$m" --out "$OUT/realvuln-dev-$m"
done

say "test half (final, once): base-converted and LoRA"
PYTHONPATH=src "$PY" scripts/realvuln_fetch.py --split test --dest "$RV" --final
for m in safia-base-conv safia-lora; do
  cli eval-realvuln --split test --final --data "$RV" --model "$m" --out "$OUT/realvuln-test-$m"
  cli eval-gym --apps blog --seeds 1 2 3 --model "$m" --out "$OUT/gym-blog-$m"
done
tar czf "$ROOT/lora_train.tgz" -C "$ROOT" "eval/results/$RUN"
echo "ALL DONE"
