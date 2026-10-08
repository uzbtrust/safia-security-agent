#!/usr/bin/env bash
# LoRA experiment (docs/EXPERIMENTS.md, "LoRA experiment") on one rented NVIDIA GPU with 48 GB.
#
# Run from the repo root on the instance; the HF token is passed in the environment and never written to disk:
#   HF_TOKEN=<read-only token> BASE_HF=<official repo id> nohup bash scripts/vast_lora.sh > lora_run.log 2>&1 &
# Order: setup -> GATE (a base weights, b 4-step QLoRA, c merged model imports into Ollama and scans) ->
# training data (hash must match the pre-registered one) -> training -> merge -> import base and LoRA through
# the same path -> RealVuln dev for official / base-converted / LoRA -> conversion check -> test half once.
# Exit codes: 4 gate failed, 5 data hash differs, 6 conversion check failed. Last line "ALL DONE" on success.
set -euo pipefail

ROOT=$(pwd)
MODEL=gemma4:12b
DATA_SHA=3055e51df8973c1b12d6c920f39e03d923b79d954f1c79d3e7172315f34a9161   # pre-registered training set
DAY=$(date +%Y%m%d)
OUT=$ROOT/eval/results/$DAY-lora
W=$ROOT/.cache/lora
PY=$ROOT/.venv/bin/python
RV=$ROOT/.cache/realvuln
: "${BASE_HF:?set BASE_HF to the official Hugging Face repo id of the base model}"
: "${HF_TOKEN:?set HF_TOKEN (read-only) in the environment}"

say() { echo "[$(date +%H:%M:%S)] $*"; }
check() {  # check <name> <command...>: records pass/fail, stops the run on failure
  local name=$1; shift
  if "$@"; then echo "{\"check\": \"$name\", \"pass\": true}" >> "$OUT/gate.jsonl"; say "PASS $name"
  else echo "{\"check\": \"$name\", \"pass\": false}" >> "$OUT/gate.jsonl"; say "GATE FAILED: $name"; exit 4; fi
}
cli() { PYTHONPATH=src "$PY" -m safia_sec.cli "$@"; }
import_model() {  # import_model <ollama name> <hf dir>: same path for every arm
  local name=$1 dir=$2
  { echo "FROM $dir"; printf 'TEMPLATE """%s"""\n' "$(ollama show "$MODEL" --template)"
    ollama show "$MODEL" --parameters | sed -n 's/^\([a-z_]*\)  *\(.*\)$/PARAMETER \1 \2/p'; } > "$W/Modelfile.$name"
  ollama create "$name" --quantize q4_K_M -f "$W/Modelfile.$name"
}
f3_of() { "$PY" -c "import sys; sys.path.insert(0, 'scripts'); from freeze_decide import totals; print(totals('$1')['f3'])"; }

mkdir -p "$OUT" "$W"
: > "$OUT/gate.jsonl"

# ---------------------------------------------------------------- setup
say "setup"
git config --global --add safe.directory '*'
command -v git >/dev/null && command -v curl >/dev/null && python3 -c "import venv" 2>/dev/null \
  || { apt-get update -qq && apt-get install -y -qq git curl python3-venv >/dev/null; }
[ -x "$PY" ] || python3 -m venv --system-site-packages .venv   # reuse the image's CUDA build of torch
"$PY" -m pip install -q "flask>=3" "pytest>=8" "bandit>=1.7" transformers peft bitsandbytes accelerate \
  huggingface_hub safetensors sentencepiece
"$PY" -c "import torch; assert torch.cuda.is_available(), 'no CUDA'"
PYTHONPATH=src "$PY" -m pytest -q -x 2>&1 | tail -2
command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh
OLLAMA_HOST=127.0.0.1:11434 nohup ollama serve > "$ROOT/ollama.log" 2>&1 &
until curl -sf http://127.0.0.1:11434/api/version >/dev/null; do sleep 1; done
ollama pull "$MODEL"
{ echo "model $MODEL $(ollama list | awk -v m="$MODEL" '$1==m {print $2}')"; echo "base $BASE_HF"
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
  echo "ollama $(ollama --version 2>&1 | tail -1)"; echo "repo $(git rev-parse HEAD)"
  "$PY" -c "import torch, transformers, peft, bitsandbytes as b; print('torch', torch.__version__, 'transformers', transformers.__version__, 'peft', peft.__version__, 'bitsandbytes', b.__version__)"
} | tee "$OUT/machine.txt"

# ---------------------------------------------------------------- data (must equal the pre-registered set)
say "training data"
PYTHONPATH=src "$PY" scripts/lora_build_data.py --dest "$W"
SHA=$("$PY" -c "import json; print(json.load(open('$W/summary.json'))['sha256'])")
cp "$W/summary.json" "$OUT/data_summary.json"
[ "$SHA" = "$DATA_SHA" ] || { say "training set hash $SHA differs from the pre-registered one"; exit 5; }

# ---------------------------------------------------------------- GATE
say "gate a: base weights"
check base_weights "$PY" -c "
import os; from huggingface_hub import snapshot_download
snapshot_download('$BASE_HF', local_dir='$W/base', token=os.environ['HF_TOKEN'])"
say "gate b: 4-step QLoRA"
check smoke_training env PYTHONPATH=src "$PY" scripts/lora_train.py train --base "$W/base" --data "$W/train.jsonl" \
  --out "$W/smoke_adapter" --smoke
say "gate c: merge, import into Ollama, scan"
smoke_export() {
  PYTHONPATH=src "$PY" scripts/lora_train.py merge --base "$W/base" --adapter "$W/smoke_adapter" --out "$W/smoke_merged" &&
  import_model safia-smoke "$W/smoke_merged" &&
  { cli scan gym_apps/shop --model safia-smoke --no-bandit --out "$W/smoke_scan" || true; } &&
  "$PY" -c "import json; m = json.load(open('$W/smoke_scan/report.json'))['meta']; assert m['llm_calls'] > 0 and not m['errors'], m['errors']"
}
check export_and_scan smoke_export
ollama rm safia-smoke; rm -rf "$W/smoke_merged" "$W/smoke_adapter"
say "gate passed"

# ---------------------------------------------------------------- training
say "training"
PYTHONPATH=src "$PY" scripts/lora_train.py train --base "$W/base" --data "$W/train.jsonl" --out "$W/adapter"
cp "$W/adapter/train_meta.json" "$W/adapter/loss.jsonl" "$W/adapter/adapter_config.json" "$OUT/"
PYTHONPATH=src "$PY" scripts/lora_train.py merge --base "$W/base" --adapter "$W/adapter" --out "$W/merged"
import_model safia-lora "$W/merged"
import_model safia-base-conv "$W/base"
rm -rf "$W/merged"

# ---------------------------------------------------------------- validation on dev + conversion check
say "RealVuln dev: official, base-converted, LoRA"
PYTHONPATH=src "$PY" scripts/realvuln_fetch.py --split dev --dest "$RV"
for m in "$MODEL" safia-base-conv safia-lora; do
  cli eval-realvuln --split dev --data "$RV" --model "$m" --out "$OUT/realvuln-dev-${m//[:\/]/_}"
done
OFF=$(f3_of "$OUT/realvuln-dev-${MODEL//[:\/]/_}"); CONV=$(f3_of "$OUT/realvuln-dev-safia-base-conv")
echo "conversion check: official $OFF, base-converted $CONV (allowed gap 0.05)" | tee "$OUT/conversion_check.txt"
"$PY" -c "import sys; sys.exit(abs($OFF - $CONV) > 0.05)" || { say "conversion check failed: stop before the test half"; exit 6; }

# ---------------------------------------------------------------- test half, once
say "test half (final): base-converted and LoRA"
PYTHONPATH=src "$PY" scripts/realvuln_fetch.py --split test --dest "$RV" --final
for m in safia-base-conv safia-lora; do
  cli eval-realvuln --split test --final --data "$RV" --model "$m" --out "$OUT/realvuln-test-$m"
  cli eval-gym --apps blog --seeds 1 2 3 --model "$m" --out "$OUT/gym-blog-$m"
done

tar czf "$ROOT/lora_results.tgz" -C "$ROOT" "eval/results/$DAY-lora"
say "results: lora_results.tgz"
echo "ALL DONE"
