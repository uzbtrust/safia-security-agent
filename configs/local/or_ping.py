#!/usr/bin/env python3
"""Latency and cost probe for one OpenRouter model. The key comes from OPENROUTER_API_KEY and is never printed.

  zsh -ic 'cd <repo> && .venv/bin/python configs/local/or_ping.py <model> [--red] [--max-tokens N] [--reasoning off|low|medium|high] [--timeout S]'

Without --red it sends a tiny prompt; with --red it sends the real Red prompt for CWE-89 (gym shop code only).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
URL = "https://openrouter.ai/api/v1/chat/completions"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--red", action="store_true")
    ap.add_argument("--max-tokens", type=int, default=200)
    ap.add_argument("--reasoning", choices=["off", "low", "medium", "high"])
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--schema", action="store_true", help="with --red: strict json_schema instead of json_object")
    ap.add_argument("--require-params", action="store_true", help="route only to providers that support every parameter")
    ap.add_argument("--sort", choices=["price", "throughput", "latency"], help="OpenRouter provider ordering")
    ap.add_argument("--only", help="route only to this upstream provider slug (no fallbacks)")
    a = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set here (run through: zsh -ic '...')")
    assert urlparse(URL).hostname == "openrouter.ai"

    prompt = "Reply with exactly: OK"
    if a.red:
        sys.path.insert(0, str(ROOT / "scripts"))
        import red_generate as rg
        t = rg.TEMPLATES["CWE-89"]
        prompt = rg.PROMPT.format(cwe=t.cwe, title=t.title, hint=t.hint, marker=t.marker,
                                  source=(rg.APP_DIR / "app.py").read_text(), example=rg.EXAMPLE.strip())
    body = {"model": a.model, "temperature": 0.8, "max_tokens": a.max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    if a.red:
        body["response_format"] = ({"type": "json_schema", "json_schema": {"name": "red_sample", "strict": True,
                                                                           "schema": rg.SCHEMA}}
                                   if a.schema else {"type": "json_object"})
    if a.require_params or a.sort:
        body["provider"] = {**({"require_parameters": True} if a.require_params else {}),
                            **({"sort": a.sort} if a.sort else {})}
    if a.only:
        body["provider"] = {**body.get("provider", {}), "order": [a.only], "allow_fallbacks": False}
    if a.reasoning:
        body["reasoning"] = {"enabled": False} if a.reasoning == "off" else {"effort": a.reasoning}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {
        "Content-Type": "application/json", "Authorization": "Bearer " + key, "User-Agent": "safia-sec"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=a.timeout) as resp:
            data = json.load(resp)
        ch = data["choices"][0]
        print(json.dumps({"ok": True, "seconds": round(time.time() - t0, 1), "provider": data.get("provider"),
                          "model": data.get("model"), "finish_reason": ch.get("finish_reason"),
                          "usage": data.get("usage"), "content_head": (ch["message"].get("content") or "")[:90]}))
    except urllib.error.HTTPError as exc:
        print(json.dumps({"ok": False, "seconds": round(time.time() - t0, 1), "http": exc.code,
                          "body": exc.read().decode()[:300]}))
    except Exception as exc:  # timeout, network
        print(json.dumps({"ok": False, "seconds": round(time.time() - t0, 1), "error": repr(exc)[:200]}))


if __name__ == "__main__":
    main()
