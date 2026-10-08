#!/usr/bin/env bash
# Step-4 freeze decision (A) and the once-only final evaluation (B) on one rented NVIDIA machine.
#
# Run from the repo root on the instance (copied there with rsync; no credentials are needed or wanted there):
#   nohup bash scripts/vast_final.sh > vast_run.log 2>&1 &
# A: round 1 and round 2 on RealVuln dev, same machine (in parallel when it has 2 GPUs);
#    scripts/freeze_decide.py applies the pre-registered rule.
# B: in the winning tree only: gym test (blog) and RealVuln test, with and without --no-examples.
# Nothing scanned is executed. Ollama listens on 127.0.0.1 only. The last line is "ALL DONE" on success.
set -euo pipefail

ROOT=$(pwd)
MODEL=gemma4:12b
MAC_DIGEST=6114515d63c1          # digest of gemma4:12b in the Mac runs (docs/handoff/local.md)
R2_COMMIT=e0c88de                # "Round 2 of step 4"; reverted in the round-1 tree
DAY=$(date +%Y%m%d)
OUT=$ROOT/eval/results
DATA=$ROOT/.cache/realvuln
PY=$ROOT/.venv/bin/python
FREEZE=$OUT/$DAY-step4-freeze-gpu

say() { echo "[$(date +%H:%M:%S)] $*"; }

# ---------------------------------------------------------------- setup
say "setup"
command -v git >/dev/null && command -v curl >/dev/null && python3 -c "import venv" 2>/dev/null \
  || { apt-get update -qq && apt-get install -y -qq git curl python3-venv >/dev/null; }
git config --global --add safe.directory '*'   # the rsync'ed checkout is owned by another uid
[ -x "$PY" ] || python3 -m venv .venv
# dependencies only: every tree imports its own src/ via PYTHONPATH (an editable install would pin one tree)
"$PY" -m pip install -q "flask>=3" "pytest>=8" "bandit>=1.7"
PYTHONPATH=src "$PY" -m pytest -q -x 2>&1 | tail -2
command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh

NGPU=$(nvidia-smi -L | wc -l)
H0=http://127.0.0.1:11434
H1=http://127.0.0.1:11435
CUDA_VISIBLE_DEVICES=0 OLLAMA_HOST=127.0.0.1:11434 nohup ollama serve > "$ROOT/ollama_gpu0.log" 2>&1 &
if [ "$NGPU" -ge 2 ]; then
  CUDA_VISIBLE_DEVICES=1 OLLAMA_HOST=127.0.0.1:11435 nohup ollama serve > "$ROOT/ollama_gpu1.log" 2>&1 &
else
  H1=$H0
fi
for h in "$H0" "$H1"; do until curl -sf "$h/api/version" >/dev/null; do sleep 1; done; done
OLLAMA_HOST=127.0.0.1:11434 ollama pull "$MODEL"
DIGEST=$(OLLAMA_HOST=127.0.0.1:11434 ollama list | awk -v m="$MODEL" '$1==m {print $2}')

mkdir -p "$FREEZE"
{
  echo "model $MODEL digest $DIGEST (Mac runs: $MAC_DIGEST)"
  echo "gpus $NGPU"; nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
  echo "ollama $(ollama --version 2>&1 | tail -1)"
  echo "repo $(git rev-parse HEAD)"
} | tee "$FREEZE/machine.txt"
[ "${DIGEST:0:12}" = "$MAC_DIGEST" ] || say "WARNING: model digest differs from the Mac runs (recorded; r1 and r2 still share this one)"

# two code trees: r2 = HEAD, r1 = HEAD without the round-2 commit (working tree only, nothing committed here)
rm -rf "$ROOT/../wt_r1" "$ROOT/../wt_r2"; git worktree prune
git worktree add -q --detach "$ROOT/../wt_r2" HEAD
git worktree add -q --detach "$ROOT/../wt_r1" HEAD
(cd "$ROOT/../wt_r1" && git revert --no-commit "$R2_COMMIT")

run() {  # run <tree> <ollama url> <cache name> <safia-sec args...>
  local tree=$1 host=$2 cache=$3; shift 3
  (cd "$tree" && PYTHONPATH=src "$PY" -c "import safia_sec, os, sys; sys.exit(not os.path.realpath(safia_sec.__file__).startswith(os.path.realpath('src')))" \
     && PYTHONPATH=src "$PY" -m safia_sec.cli "$@" --model "$MODEL" --host "$host" --cache "$ROOT/.cache/$cache")
}
pair() {  # pair "<cmd for gpu0>" "<cmd for gpu1>": parallel on 2 GPUs, sequential on 1
  if [ "$NGPU" -ge 2 ]; then
    bash -c "$1" & local p0=$!; bash -c "$2" & local p1=$!
    wait $p0; wait $p1
  else
    bash -c "$1"; bash -c "$2"
  fi
}
export -f run say; export ROOT PY MODEL

# ---------------------------------------------------------------- A: freeze decision on dev
say "A: fetch dev, run r1 and r2 on RealVuln dev"
PYTHONPATH=src "$PY" scripts/realvuln_fetch.py --split dev --dest "$DATA"
pair "run '$ROOT/../wt_r1' $H0 llm_gpu0 eval-realvuln --split dev --data '$DATA' --out '$OUT/$DAY-step4-realvuln-dev-r1-gpu'" \
     "run '$ROOT/../wt_r2' $H1 llm_gpu1 eval-realvuln --split dev --data '$DATA' --out '$OUT/$DAY-step4-realvuln-dev-r2-gpu'"
WINNER=$("$PY" scripts/freeze_decide.py "$OUT/$DAY-step4-realvuln-dev-r1-gpu" "$OUT/$DAY-step4-realvuln-dev-r2-gpu" "$FREEZE" | tail -1)
say "A: frozen round = $WINNER"
if [ "$WINNER" = "tie" ]; then say "exact tie: stopping before B (the tie-break needs a gym-dev run)"; exit 3; fi
TREE=$ROOT/../wt_$WINNER

# ---------------------------------------------------------------- B: once-only final evaluation
say "B: fetch test (final), run blog and RealVuln test with and without examples in the $WINNER tree"
PYTHONPATH=src "$PY" scripts/realvuln_fetch.py --split test --dest "$DATA" --final
pair "run '$TREE' $H0 llm_gpu0 eval-gym --apps blog --seeds 1 2 3 --out '$OUT/$DAY-final-gym-blog-gemma4_12b' && \
      run '$TREE' $H0 llm_gpu0 eval-realvuln --split test --final --data '$DATA' --out '$OUT/$DAY-final-realvuln-test-gemma4_12b'" \
     "run '$TREE' $H1 llm_gpu1 eval-gym --apps blog --seeds 1 2 3 --no-examples --out '$OUT/$DAY-final-gym-blog-gemma4_12b-noex' && \
      run '$TREE' $H1 llm_gpu1 eval-realvuln --split test --final --no-examples --data '$DATA' --out '$OUT/$DAY-final-realvuln-test-gemma4_12b-noex'"

tar czf "$ROOT/vast_results.tgz" -C "$ROOT" "eval/results/$DAY-step4-freeze-gpu" "eval/results/$DAY-step4-realvuln-dev-r1-gpu" \
  "eval/results/$DAY-step4-realvuln-dev-r2-gpu" eval/results/$DAY-final-*
say "results: vast_results.tgz (frozen round: $WINNER)"
echo "ALL DONE"
