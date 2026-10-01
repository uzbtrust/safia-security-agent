"""Compare candidate Red models using Artificial Analysis data.

Reads the key from the AA_TOKEN environment variable (never print or commit it).
Run on your own machine:  python scripts/aa_pick.py
Endpoint/field names are from memory: if the shape differs, the script prints the
raw keys so we can adjust.
"""
import json
import os
import sys
import urllib.request

URL = "https://artificialanalysis.ai/api/v2/data/llms/models"
WANT = ["deepseek v4.1", "muse spark", "gemini 3.8", "space bunny", "mimo",
        "glm-5.3", "solar pro 4", "laguna s 2.1"]


def main() -> None:
    key = os.environ.get("AA_TOKEN")
    if not key:
        sys.exit("AA_TOKEN is not set in this shell (try: source ~/.zshrc)")
    req = urllib.request.Request(URL, headers={"x-api-key": key, "User-Agent": "safia-sec"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    models = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not models:
        sys.exit(f"unexpected response keys: {list(payload)[:10]}")
    hits = [m for m in models if any(w in (m.get("name", "") + m.get("slug", "")).lower().replace("-", " ")
                                     or w.replace("-", " ") in m.get("name", "").lower() for w in WANT)]
    print(f"{len(models)} models in API, {len(hits)} match the shortlist\n")
    for m in sorted(hits, key=lambda x: x.get("name", "")):
        creator = (m.get("model_creator") or {}).get("name", "?")
        print(f"== {m.get('name')} ({creator})")
        print("   evaluations:", json.dumps(m.get("evaluations", {}))[:300])
        print("   pricing:", json.dumps(m.get("pricing", {}))[:200])
        print("   speed tok/s:", m.get("median_output_tokens_per_second"))


if __name__ == "__main__":
    main()
