#!/usr/bin/env python3
"""Print what an OpenRouter key has spent. Cost accounting for API runs: run it before and after.

The key comes from OPENROUTER_API_KEY in the environment (run through `zsh -ic '...'`). Only a
whitelist of numeric fields is printed: the response's `label` holds a key preview, so it is never shown.
"""
import json
import os
import sys
import urllib.request
from urllib.parse import urlparse

URL = "https://openrouter.ai/api/v1/key"
SHOW = ("usage", "usage_daily", "limit", "limit_remaining", "is_free_tier")


def main() -> None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set here (run through: zsh -ic '...')")
    assert urlparse(URL).hostname == "openrouter.ai"
    req = urllib.request.Request(URL, headers={"Authorization": "Bearer " + key, "User-Agent": "safia-sec"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp).get("data", {})
    print(json.dumps({k: data.get(k) for k in SHOW}))


if __name__ == "__main__":
    main()
