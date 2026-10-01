#!/usr/bin/env bash
# Pull an Ollama model, but abort if the free space on / drops below a floor (default 15 GB).
#   configs/local/guarded_pull.sh qwen3.5:9b [floor_gb]
# Progress and the outcome go to .cache/logs/pull-<tag>.log (gitignored). Run it from the repo root.
set -u
tag="$1"
floor=$(( ${2:-15} * 1000000000 ))
log=".cache/logs/pull-${tag//[:\/]/_}.log"
mkdir -p .cache/logs
: > "$log"
free() { diskutil info / | sed -nE 's/.*Container Free Space:.*\(([0-9]+) Bytes\).*/\1/p'; }
echo "free before: $(free)" >> "$log"
ollama pull "$tag" >> "$log" 2>&1 &
pid=$!
while kill -0 "$pid" 2>/dev/null; do
  f=$(free)
  if [ -n "$f" ] && [ "$f" -lt "$floor" ]; then
    kill "$pid"
    echo "ABORTED: free space $f is below the floor $floor" >> "$log"
    break
  fi
  sleep 10
done
wait "$pid"
echo "pull exit=$?" >> "$log"
echo "free after: $(free)" >> "$log"
