#!/usr/bin/env python3
"""Small open-weight candidates from Artificial Analysis (https://artificialanalysis.ai).

AA_TOKEN is read from the environment only; never print or commit it. The raw API response is
cached in .cache/aa_models.json (gitignored, so AA's data stays out of the repo); only the derived
table is committed, with attribution to Artificial Analysis.

  zsh -ic 'cd <repo> && .venv/bin/python configs/local/aa_small_models.py --keys --match jev'
  zsh -ic 'cd <repo> && .venv/bin/python configs/local/aa_small_models.py --max-b 14'
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "aa_models.json"
URL = "https://artificialanalysis.ai/api/v2/data/llms/models"

TOTAL = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*[bB](?![a-zA-Z])")  # "8B", "3.8B"
EFFECTIVE = re.compile(r"\bE(\d+(?:\.\d+)?)B\b")                      # Gemma "E4B" (effective size)
ACTIVE = re.compile(r"(?<![A-Za-z])A(\d+(?:\.\d+)?)B\b")              # MoE "A3B" (active parameters)


def fetch(refresh: bool) -> dict | list:
    if CACHE.exists() and not refresh:
        return json.loads(CACHE.read_text())
    key = os.environ.get("AA_TOKEN")
    if not key:
        sys.exit("AA_TOKEN is not set here (run through: zsh -ic '...')")
    assert urlparse(URL).hostname == "artificialanalysis.ai"
    req = urllib.request.Request(URL, headers={"x-api-key": key, "User-Agent": "safia-sec"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(payload))
    return payload


def size_info(name: str) -> tuple[float | None, float | None]:
    """(total params in B, active params in B) parsed from the model name; None when absent."""
    total = [float(x) for x in TOTAL.findall(name)]
    eff = [float(x) for x in EFFECTIVE.findall(name)]
    act = [float(x) for x in ACTIVE.findall(name)]
    t = max(total) if total else (max(eff) if eff else None)
    return t, (max(act) if act else None)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-b", type=float, default=14.0, help="max total parameters in billions")
    ap.add_argument("--top", type=int, default=45)
    ap.add_argument("--keys", action="store_true", help="print the response shape")
    ap.add_argument("--match", help="regex: print matching models in full")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache and call the API")
    a = ap.parse_args()

    payload = fetch(a.refresh)
    models = payload.get("data", payload) if isinstance(payload, dict) else payload
    print(f"{len(models)} models in the data set")
    if a.keys:
        print("model keys:", sorted(models[0]))
        ev = sorted({k for m in models for k in (m.get("evaluations") or {})})
        print("evaluation keys:", ev)
    if a.match:
        rx = re.compile(a.match, re.I)
        hits = [m for m in models if rx.search(m.get("name", "") + " " + m.get("slug", ""))]
        print(f"--match {a.match!r}: {len(hits)} hit(s)")
        for m in hits[:5]:
            print(json.dumps(m)[:900])
        return

    rows = []
    for m in models:
        total, active = size_info(m.get("name", ""))
        if total is None or total > a.max_b:
            continue
        ev = m.get("evaluations") or {}
        rows.append((m.get("name"), (m.get("model_creator") or {}).get("name", "?"), total, active,
                     ev.get("artificial_analysis_intelligence_index"), ev.get("artificial_analysis_coding_index"),
                     ev.get("ifbench"), ev.get("tau2"), ev.get("livecodebench"),
                     m.get("median_output_tokens_per_second")))
    rows.sort(key=lambda r: (r[5] is None, -(r[5] or 0), -(r[4] or 0)))
    print(f"\n{len(rows)} models with a parsed size <= {a.max_b:g}B (source: Artificial Analysis)")
    print(f"{'name':44s} {'creator':14s} {'B':>5s} {'act':>4s} {'intel':>6s} {'code':>6s} {'ifbench':>8s} {'tau2':>6s} {'lcb':>6s} {'tok/s':>6s}")
    fmt = lambda v, w, p=1: f"{v:{w}.{p}f}" if isinstance(v, (int, float)) else f"{'-':>{w}s}"
    for n, c, t, act, i, cd, ifb, tau, lcb, tps in rows[: a.top]:
        print(f"{n[:44]:44s} {str(c)[:14]:14s} {fmt(t, 5)} {fmt(act, 4)} {fmt(i, 6)} {fmt(cd, 6)} {fmt(ifb, 8, 2)} {fmt(tau, 6, 2)} {fmt(lcb, 6, 2)} {fmt(tps, 6, 0)}")


if __name__ == "__main__":
    main()
