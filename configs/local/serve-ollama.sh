#!/usr/bin/env bash
# Start the local Ollama server with the project's settings (runs in the foreground).
#   mkdir -p .cache/logs && configs/local/serve-ollama.sh > .cache/logs/ollama-serve.log 2>&1 &
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
set -a
# shellcheck source=ollama.env
source "$here/ollama.env"
set +a
exec ollama serve
